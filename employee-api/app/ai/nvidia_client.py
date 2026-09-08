from openai import OpenAI
from app.config import settings

nvclient = OpenAI(
    api_key=settings.nvidia_api_key,
    base_url=settings.nvidia_base_url,
)