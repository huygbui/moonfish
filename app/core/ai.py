from google import genai

from .config import settings


class LLM:
    def __init__(self, client):
        self.client = client

    def generate_topic(self) -> str:
        return "Some topic from the llm"


gemini_client = genai.Client(api_key=settings.gemini_api_key)

llm = LLM(gemini_client)
