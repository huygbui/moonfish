from string import Template

from google import genai
from google.genai import types

from app.ai import helpers, prompts
from app.core.config import settings


class LLM:
    def __init__(self, gemini_client):
        self.gemini_client = gemini_client

    async def generate_topic(self) -> str:
        category = helpers.get_random_category()
        angle = helpers.get_random_angle()
        response = await gemini_client.aio.models.generate_content(
            model=settings.gemini_lite_model,
            contents=[
                Template(prompts.topic_system).substitute(
                    angle=angle,
                    category=category,
                )
            ],
            config=types.GenerateContentConfig(
                temperature=2.0,
                top_p=0.90,
            ),
        )
        return response.text


gemini_client = genai.Client(api_key=settings.gemini_api_key)
gemini_model = settings.gemini_model
llm = LLM(gemini_client)
