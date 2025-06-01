from fastapi import HTTPException
from google import genai
from google.genai import types
from hatchet_sdk import Context, EmptyModel, Hatchet

from . import prompts, tools
from .config import settings
from .database import async_session
from .models import (
    Podcast,
    PodcastComposeResult,
    PodcastResearchResult,
    PodcastTaskInput,
    PodcastVoiceResult,
)

hatchet = Hatchet(debug=True)

podcast_generation = hatchet.workflow(name="PodcastGeneration")

client = genai.Client(api_key=settings.gemini_api_key)
gemini_model = settings.gemini_model


@podcast_generation.task()
async def research(input: PodcastTaskInput, ctx: Context) -> PodcastResearchResult:
    # Update db status
    async with async_session() as session:
        podcast = await session.get(Podcast, input.id)
        if not podcast:
            raise HTTPException(status_code=404, detail="Podcast not found")
        # data = req.model_dump(exclude_unset=True, mode="json")
        # podcast.sqlmodel_update(data)
        podcast.status = "active"
        podcast.step = "research"
        session.add(podcast)
        await session.commit()
        await session.refresh(podcast)

    # Generate
    result = await client.aio.models.generate_content(
        model=gemini_model,
        contents=[prompts.research_system, prompts.research_user.format_map(input.model_dump())],
        config=types.GenerateContentConfig(
            tools=[tools.search],
        ),
    )

    return PodcastResearchResult(id=input.id, result=result.text, metadata=result.usage_metadata)


@podcast_generation.task(parents=[research])
async def compose(input: EmptyModel, ctx: Context) -> PodcastComposeResult:
    # Get result
    input = ctx.task_output(research)
    research_result = PodcastResearchResult.model_validate(input)

    # Update db status
    async with async_session() as session:
        podcast = await session.get(Podcast, input.id)
        if not podcast:
            raise HTTPException(status_code=404, detail="Podcast not found")
        # data = req.model_dump(exclude_unset=True, mode="json")
        # podcast.sqlmodel_update(data)
        podcast.step = "compose"
        session.add(podcast)
        await session.commit()
        await session.refresh(podcast)

    # Generate
    result = await client.aio.models.generate_content(
        model=gemini_model,
        contents=[prompts.compose_system, prompts.compose_user.format(research_result)],
    )

    return PodcastComposeResult(id=input.id, result=result.text, metadata=result.usage_metadata)


@podcast_generation.task(parents=[compose])
async def voice(input: EmptyModel, ctx: Context):
    # Get result
    input = ctx.task_output(compose)
    compose_result = PodcastComposeResult.model_validate(input)

    # Update db status
    async with async_session() as session:
        podcast = await session.get(Podcast, input.id)
        if not podcast:
            raise HTTPException(status_code=404, detail="Podcast not found")
        # data = req.model_dump(exclude_unset=True, mode="json")
        # podcast.sqlmodel_update(data)
        podcast.step = "voice"
        session.add(podcast)
        await session.commit()
        await session.refresh(podcast)

    return PodcastVoiceResult(id=compose_result.id, result="voice result")
