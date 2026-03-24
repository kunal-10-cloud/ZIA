from openai import AsyncOpenAI
from backend.config.settings import settings

# One shared client for the whole app
# OpenRouter is OpenAI-compatible — same SDK, different base URL + key
sonnet_client = AsyncOpenAI(
    api_key=settings.OPENROUTER_API_KEY,
    base_url=settings.OPENROUTER_BASE_URL,
)

haiku_client = AsyncOpenAI(
    api_key=settings.OPENROUTER_API_KEY,
    base_url=settings.OPENROUTER_BASE_URL,
)


async def call_sonnet(system_prompt: str, messages: list, tools: list = None) -> str:
    """
    Main conversation call — uses Claude Sonnet via OpenRouter.
    This is what the orchestrator calls on every turn.
    """
    kwargs = {
        "model": settings.CLAUDE_SONNET_MODEL,
        "messages": [{"role": "system", "content": system_prompt}] + messages,
        "max_tokens": 1024,
        "extra_headers": {
            "HTTP-Referer": "https://employlabs.com",  # OpenRouter asks for this
            "X-Title": "Zia Career Companion",
        },
    }
    if tools:
        kwargs["tools"] = tools

    response = await sonnet_client.chat.completions.create(**kwargs)
    return response.choices[0].message.content


async def call_haiku(system_prompt: str, messages: list) -> str:
    """
    Classification/profiling call — uses Claude Haiku via OpenRouter.
    Used by: skill router fallback, cultural profiler background task.
    """
    response = await haiku_client.chat.completions.create(
        model=settings.CLAUDE_HAIKU_MODEL,
        messages=[{"role": "system", "content": system_prompt}] + messages,
        "max_tokens": 512,
        extra_headers={
            "HTTP-Referer": "https://employlabs.com",
            "X-Title": "Zia Career Companion",
        },
    )
    return response.choices[0].message.content