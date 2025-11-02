from __future__ import annotations

from abc import ABC, abstractmethod

import anthropic
import openai

from second_brain.core.config import get_settings


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, system: str, query: str, context: str) -> str: ...


class AnthropicProvider(LLMProvider):
    def __init__(self) -> None:
        settings = get_settings()
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.llm_model

    async def generate(self, system: str, query: str, context: str) -> str:
        prompt = f"{context}\n\nUser question: {query}"
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text  # type: ignore[union-attr]


class OpenAIProvider(LLMProvider):
    def __init__(self) -> None:
        settings = get_settings()
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.llm_model if "gpt" in settings.llm_model else "gpt-4o"

    async def generate(self, system: str, query: str, context: str) -> str:
        prompt = f"{context}\n\nUser question: {query}"
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            max_tokens=4096,
        )
        return response.choices[0].message.content or ""


def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    if settings.llm_provider == "openai":
        return OpenAIProvider()
    return AnthropicProvider()
