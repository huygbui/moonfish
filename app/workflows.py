from string import Template

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
        podcast.status = "active"
        podcast.step = "research"
        session.add(podcast)
        await session.commit()
        await session.refresh(podcast)

    # Generate
    result = await client.aio.models.generate_content(
        model=gemini_model,
        contents=[
            prompts.research_system,
            Template(prompts.research_user).substitute(input.model_dump()),
        ],
        config=types.GenerateContentConfig(
            tools=[tools.web_search],
        ),
    )

    return PodcastResearchResult(
        id=input.id, input=input, result=result.text, usage=str(result.usage_metadata.model_dump())
    )


@podcast_generation.task(parents=[research])
async def compose(_: EmptyModel, ctx: Context) -> PodcastComposeResult:
    # Get result
    input = PodcastResearchResult.model_validate(ctx.task_output(research))

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
        contents=[
            prompts.compose_system,
            Template(prompts.compose_user).substitute(
                input.input.model_dump(), research_result=input.result
            ),
        ],
    )

    return PodcastComposeResult(
        id=input.id,
        input=input.input,
        result=result.text,
        usage=str(result.usage_metadata.model_dump()),
    )


@podcast_generation.task(parents=[compose])
async def voice(_: EmptyModel, ctx: Context):
    # Get result
    input = PodcastComposeResult.model_validate(ctx.task_output(compose))

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

    return PodcastVoiceResult(
        id=input.id, input=input.input, result="some result", usage="some usage"
    )
