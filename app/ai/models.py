from string import Template

from google import genai

from app.ai import prompts
from app.core.config import settings


class LLM:
    def __init__(self, gemini_client):
        self.gemini_client = gemini_client

    async def generate_topic(self, format) -> str:
        response = await gemini_client.aio.models.generate_content(
            model=gemini_model,
            contents=[prompts.topic_user, Template(prompts.compose_user).substitute(format=format)],
        )
        return response.text


gemini_client = genai.Client(api_key=settings.gemini_api_key)
gemini_model = settings.gemini_model
llm = LLM(gemini_client)
