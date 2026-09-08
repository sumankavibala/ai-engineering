from openai import OpenAI
from app.config import settings

client = OpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_base_url,
)

nvclient = OpenAI(
    api_key=settings.nvidia_api_key,
    base_url=settings.nvidia_base_url,
)

def create_embedding(text: str) -> list[float]:

    response = nvclient.embeddings.create(
    model="nvidia/nemotron-3-embed-1b",
    input=text
    )
    return response.data[0].embedding
