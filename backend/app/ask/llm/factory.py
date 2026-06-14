from app.ask.llm.errors import ProviderNotConfiguredError, ProviderNotImplementedError
from app.ask.llm.gemini_provider import GeminiProvider
from app.ask.llm.mock_provider import MockLLMProvider
from app.ask.llm.provider import LLMProvider
from app.core.config import get_settings


def get_llm_provider(provider_name: str | None = None, *, fallback_to_mock: bool = False) -> LLMProvider:
    settings = get_settings()
    selected = (provider_name or settings.llm_provider or "mock").strip().lower()

    if selected == "mock":
        return MockLLMProvider()
    if selected == "gemini":
        if fallback_to_mock and not settings.gemini_api_key:
            return MockLLMProvider()
        return GeminiProvider(settings=settings)
    if selected == "openai":
        raise ProviderNotImplementedError("OpenAI provider is reserved for a later phase and is not implemented yet.")

    raise ProviderNotConfiguredError(f"Unsupported LLM provider: {selected}")
