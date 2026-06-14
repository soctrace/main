from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ask.llm.gemini_provider import GeminiProvider
from app.core.config import get_settings


async def main() -> int:
    settings = get_settings()
    print(f"LLM_PROVIDER={settings.llm_provider}")
    print(f"GEMINI_API_KEY={'loaded' if settings.gemini_api_key else 'missing'}")
    if settings.llm_provider.strip().lower() != "gemini":
        print("Provider check failed: LLM_PROVIDER is not gemini")
        return 1
    if not settings.gemini_api_key:
        print("Provider check failed: GEMINI_API_KEY is missing")
        return 1

    provider = GeminiProvider(settings=settings)
    print("Provider OK")
    model = settings.gemini_default_model
    try:
        if provider.client is None:
            provider.client = provider._build_client()
        response = await asyncio.to_thread(
            provider.client.models.generate_content,
            model=model,
            contents="Hola",
        )
        print("Model OK")
        if getattr(response, "text", None):
            print("Response OK")
            return 0
        print("Response failed: empty model response")
        return 1
    except Exception as exc:
        print(f"Gemini connection failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
