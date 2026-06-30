from langchain_openai import ChatOpenAI
from langsmith.wrappers import wrap_openai
from openai import AsyncOpenAI
from pydantic import BaseModel

from src.common.config import settings


def create_chat_client() -> AsyncOpenAI:
    """Deepseek (OpenAI-compatible) client wrapped for LangSmith tracing."""
    client = AsyncOpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)
    return wrap_openai(client)


def create_structured_llm(schema: type[BaseModel]):
    """ChatOpenAI bound to a pydantic schema, so malformed output raises instead of passing through."""
    return ChatOpenAI(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=0,
    ).with_structured_output(schema, method="function_calling")
