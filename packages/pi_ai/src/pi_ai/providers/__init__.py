from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pi_ai.types import Api, ApiProvider, Context, Model, SimpleStreamOptions, StreamOptions
from pi_ai.event_stream import AssistantMessageEventStream
from pi_ai.providers.openai import stream_openai_completions
from pi_ai.providers.anthropic import stream_anthropic_messages
from pi_ai.providers.google import stream_google
from pi_ai.providers.transform import transform_messages

StreamFunction = Callable[
    [Model, Context, StreamOptions | None],
    AssistantMessageEventStream,
]

_registry: dict[str, tuple[Any, str | None]] = {}


def register_api_provider(
    provider: Any,
    source_id: str | None = None,
) -> None:
    global _registry
    _registry[provider.api] = (provider, source_id)


def get_api_provider(api: str) -> Any | None:
    entry = _registry.get(api)
    return entry[0] if entry else None


def get_api_providers() -> list[Any]:
    return [entry[0] for entry in _registry.values()]


def unregister_api_providers(source_id: str) -> None:
    global _registry
    to_remove = [api for api, (_, sid) in _registry.items() if sid == source_id]
    for api in to_remove:
        del _registry[api]


def clear_api_providers() -> None:
    global _registry
    _registry.clear()

register_api_provider(
    ApiProvider(
        api="openai-completions",
        stream=stream_openai_completions,
        stream_simple=stream_openai_completions,
    ),
    "openai",
)

register_api_provider(
    ApiProvider(
        api="anthropic-messages",
        stream=stream_anthropic_messages,
        stream_simple=stream_anthropic_messages,
    ),
    "anthropic",
)

register_api_provider(
    ApiProvider(
        api="google-generative-ai",
        stream=stream_google,
        stream_simple=stream_google,
    ),
    "google",
)

__all__ = [
    "stream_openai_completions",
    "stream_anthropic_messages",
    "stream_google",
    "transform_messages",
    "ApiProvider",
]
