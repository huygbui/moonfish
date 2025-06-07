from exa_py import AsyncExa
from google import genai

from app.core.config import settings

exa_client = AsyncExa(settings.exa_api_key)

gemini_client = genai.Client(api_key=settings.gemini_api_key)
gemini_model = settings.gemini_model
gemini_tts_model = settings.gemini_tts_model
