import asyncio
from datetime import timedelta
from io import BytesIO
from string import Template
from typing import Tuple

from google import genai
from google.genai import types
from hatchet_sdk import Context
from pydub import AudioSegment

from app.core.config import settings
from app.core.database import async_session
from app.core.storage import Minio, minio_bucket, minio_client
from app.models import (
    Episode,
    EpisodeComposeOutput,
    EpisodeComposeResponse,
    EpisodeComposeResult,
    EpisodeContent,
    EpisodeResearchOutput,
    EpisodeTaskFailure,
    EpisodeTaskInput,
    EpisodeVoiceOutput,
    EpisodeVoiceResult,
)
from app.worker import prompts, tools
from app.worker.hatchet_client import hatchet

podcast_generation = hatchet.workflow(name="PodcastGeneration")


gemini_client = genai.Client(api_key=settings.gemini_api_key)
gemini_model = settings.gemini_model
gemini_pro_model = settings.gemini_pro_model
gemini_tts_model = settings.gemini_tts_model


@podcast_generation.task()
async def research(input: EpisodeTaskInput, ctx: Context) -> EpisodeResearchOutput:
    # Update db status
    async with async_session() as session:
        episode = await session.get(Episode, input.id)
        if not episode:
            raise Exception("Episode not found")
        episode.hatchet_run_id = ctx.workflow_run_id
        episode.status = "active"
        episode.step = "research"
        session.add(episode)
        await session.commit()

        # Generate
        response = await gemini_client.aio.models.generate_content(
            model=gemini_model,
            contents=[
                prompts.research_system,
                Template(prompts.research_user).substitute(input.model_dump()),
            ],
            config=types.GenerateContentConfig(
                tools=[tools.web_search],
            ),
        )

    return EpisodeResearchOutput(result=response.text, usage=response.usage_metadata.model_dump())


@podcast_generation.task(parents=[research])
async def compose(input: EpisodeTaskInput, ctx: Context) -> EpisodeComposeOutput:
    # Get output
    research_output = EpisodeResearchOutput.model_validate(ctx.task_output(research))

    # Update db status
    async with async_session() as session:
        episode = await session.get(Episode, input.id)
        if not episode:
            raise Exception("Episode not found")
        episode.step = "compose"
        session.add(episode)
        await session.commit()
        await session.refresh(episode)

    # Generate transcript
    response = await gemini_client.aio.models.generate_content(
        model=gemini_model,
        contents=[
            prompts.compose_system,
            Template(prompts.compose_user).substitute(
                input.model_dump(), research_result=research_output.result
            ),
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=EpisodeComposeResponse,
        ),
    )

    result = EpisodeComposeResponse.model_validate_json(response.text)

    return EpisodeComposeOutput(
        result=EpisodeComposeResult(
            title=result.title, summary=result.summary, transcript=result.script
        ),
        usage=response.usage_metadata.model_dump(),
    )


@podcast_generation.task(parents=[compose], execution_timeout=timedelta(minutes=5))
async def voice(input: EpisodeTaskInput, ctx: Context):
    # Get output
    compose_output = EpisodeComposeOutput.model_validate(ctx.task_output(compose))

    # Update db status
    async with async_session() as session:
        episode = await session.get(Episode, input.id)
        if not episode:
            raise Exception("Episode not found")
        episode.content = EpisodeContent(
            title=compose_output.result.title,
            summary=compose_output.result.summary,
            transcript=compose_output.result.transcript,
        )
        episode.step = "voice"
        session.add(episode)
        await session.commit()

    # Generate audio
    response = await gemini_client.aio.models.generate_content(
        model=gemini_tts_model,
        contents=compose_output.result.transcript,
        config=types.GenerateContentConfig(
            temperature=1,
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                    speaker_voice_configs=[
                        types.SpeakerVoiceConfig(
                            speaker="Speaker 1",
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Zephyr")
                            ),
                        ),
                        types.SpeakerVoiceConfig(
                            speaker="Speaker 2",
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Puck")
                            ),
                        ),
                    ]
                ),
            ),
        ),
    )
    data = response.candidates[0].content.parts[0].inline_data.data
    name = f"{input.podcast_id}/{input.id}.mp3"

    # Process and upload to minio
    buffer, buffer_size, duration = await asyncio.to_thread(process_audio, data)
    try:
        await asyncio.to_thread(
            upload_audio,
            data=buffer,
            length=buffer_size,
            client=minio_client,
            bucket_name=minio_bucket,
            object_name=name,
        )
    finally:
        buffer.close()
        buffer = None

    return EpisodeVoiceOutput(
        result=EpisodeVoiceResult(file_name=name, duration=duration),
        usage=response.usage_metadata.model_dump(),
    )


@podcast_generation.on_success_task()
async def handle_success(input: EpisodeTaskInput, ctx: Context):
    voice_output = EpisodeVoiceOutput.model_validate(ctx.task_output(voice))
    # Update db status
    async with async_session() as session:
        episode = await session.get(Episode, input.id)
        if not episode:
            raise Exception("Episode not found")

        episode.duration = voice_output.result.duration
        episode.step = None
        episode.status = "completed"
        session.add(episode)
        await session.commit()


@podcast_generation.on_failure_task()
async def handle_failure(input: EpisodeTaskInput, ctx: Context):
    async with async_session() as session:
        episode = await session.get(Episode, input.id)
        if not episode:
            raise Exception("Episode not found")
        episode.status = "failed"
        session.add(episode)
        await session.commit()

    return EpisodeTaskFailure(error=ctx.task_run_errors)


def process_audio(data: bytes) -> Tuple[BytesIO, int, int]:
    audio = AudioSegment(
        data=data,
        sample_width=2,
        frame_rate=24000,
        channels=1,
    )
    duration = int(audio.duration_seconds)

    buffer = BytesIO()
    audio.export(buffer, format="mp3", bitrate="128k")
    buffer_size = buffer.getbuffer().nbytes

    if buffer_size <= 0:
        raise ValueError("Empty audio buffer")

    return buffer, buffer_size, duration


def upload_audio(data: BytesIO, length: int, client: Minio, bucket_name: str, object_name: str):
    client.put_object(
        bucket_name=bucket_name,
        object_name=object_name,
        data=data,
        length=length,
        content_type="audio/mpeg",
    )
