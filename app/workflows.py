import asyncio
from datetime import timedelta
from io import BytesIO
from string import Template
from typing import Tuple

from google import genai
from google.genai import types
from hatchet_sdk import Context, Hatchet
from minio import Minio
from pydub import AudioSegment

from . import prompts, tools
from .config import settings
from .database import async_session
from .models import (
    Podcast,
    PodcastComposeResponse,
    PodcastComposeResult,
    PodcastContent,
    PodcastResearchResult,
    PodcastTaskFailure,
    PodcastTaskInput,
    PodcastVoiceResult,
)

hatchet = Hatchet(debug=True)

podcast_generation = hatchet.workflow(name="PodcastGeneration")

gemini_client = genai.Client(api_key=settings.gemini_api_key)
gemini_model = settings.gemini_model
gemini_tts_model = settings.gemini_tts_model

minio_client = Minio(
    f"{settings.minio_server}:{settings.minio_port}",
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=False,
)
minio_bucket = settings.minio_bucket


@podcast_generation.task()
async def research(input: PodcastTaskInput, ctx: Context) -> PodcastResearchResult:
    # Update db status
    async with async_session() as session:
        podcast = await session.get(Podcast, input.id)
        if not podcast:
            raise Exception("Podcast not found")
        podcast.status = "active"
        podcast.step = "research"
        session.add(podcast)
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

    return PodcastResearchResult(result=response.text, usage=response.usage_metadata.model_dump())


@podcast_generation.task(parents=[research])
async def compose(input: PodcastTaskInput, ctx: Context) -> PodcastComposeResult:
    # Get output
    research_output = PodcastResearchResult.model_validate(ctx.task_output(research))

    # Update db status
    async with async_session() as session:
        podcast = await session.get(Podcast, input.id)
        if not podcast:
            raise Exception("Podcast not found")
        podcast.step = "compose"
        session.add(podcast)
        await session.commit()
        await session.refresh(podcast)

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
                response_schema=PodcastComposeResponse,
            ),
        )

        result = PodcastComposeResponse.model_validate_json(response.text)

        # Update db transcript
        podcast.title = result.title
        podcast.content = PodcastContent(transcript=result.script)
        session.add(podcast)
        await session.commit()

    return PodcastComposeResult(result=result.script, usage=response.usage_metadata.model_dump())


@podcast_generation.task(parents=[compose], execution_timeout=timedelta(minutes=5))
async def voice(input: PodcastTaskInput, ctx: Context):
    # Get output
    compose_output = PodcastComposeResult.model_validate(ctx.task_output(compose))

    # Update db status
    async with async_session() as session:
        podcast = await session.get(Podcast, input.id)
        if not podcast:
            raise Exception("Podcast not found")
        podcast.step = "voice"
        session.add(podcast)
        await session.commit()
        await session.refresh(podcast)

        # Generate audio
        response = await gemini_client.aio.models.generate_content(
            model=gemini_tts_model,
            contents=compose_output.result,
            config=types.GenerateContentConfig(
                temperature=1,
                response_modalities=["audio"],
                speech_config=types.SpeechConfig(
                    multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                        speaker_voice_configs=[
                            types.SpeakerVoiceConfig(
                                speaker="Speaker 1",
                                voice_config=types.VoiceConfig(
                                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                        voice_name="Zephyr"
                                    )
                                ),
                            ),
                            types.SpeakerVoiceConfig(
                                speaker="Speaker 2",
                                voice_config=types.VoiceConfig(
                                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                        voice_name="Puck"
                                    )
                                ),
                            ),
                        ]
                    ),
                ),
            ),
        )
        data = response.candidates[0].content.parts[0].inline_data.data
        name = f"{input.id}.mp3"

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

        # Update db status
        podcast.step = None
        podcast.status = "completed"
        podcast.audio_url = name
        podcast.duration = duration
        session.add(podcast)
        await session.commit()

    return PodcastVoiceResult(result=name, usage=response.usage_metadata.model_dump())


@podcast_generation.on_failure_task()
async def on_failure(input: PodcastTaskInput, ctx: Context):
    async with async_session() as session:
        podcast = await session.get(Podcast, input.id)
        if not podcast:
            raise Exception("Podcast not found")
        podcast.status = "cancelled"
        session.add(podcast)
        await session.commit()

    return PodcastTaskFailure(error=ctx.task_run_errors)


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
