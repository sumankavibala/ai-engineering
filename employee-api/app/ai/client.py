from openai import OpenAI
from app.config import settings
from app.ai.retry import call_with_retry

client = OpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_base_url,
    timeout=30.0,
)

nvclient = OpenAI(
    api_key=settings.nvidia_api_key,
    base_url=settings.nvidia_base_url,
    timeout=30.0,
)

def create_embedding(text: str) -> list[float]:

    response = call_with_retry(
        lambda: nvclient.embeddings.create(
            model="nvidia/nemotron-3-embed-1b",
            input=text
        )
    )
    return response.data[0].embedding
