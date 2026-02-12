from __future__ import annotations

from typing import Any, Callable

from pi_ai.event_stream import AssistantMessageEventStream
from pi_ai.types import Api, Context, Model, SimpleStreamOptions, StreamOptions

StreamFunction = Callable[
    [Model, Context, StreamOptions | None],
    AssistantMessageEventStream,
]

ApiProvider = None
_registry: dict[str, tuple[Any, str | None]] = {}


def register_api_provider(
    provider: Any,
    source_id: str | None = None,
) -> None:
    global ApiProvider

    ApiProvider = provider
    _registry[provider.api] = (provider, source_id)


def get_api_provider(api: str) -> Any | None:
    entry = _registry.get(api)
    return entry[0] if entry else None


def get_api_providers() -> list[Any]:
    return [entry[0] for entry in _registry.values()]


def unregister_api_providers(source_id: str) -> None:
    global ApiProvider
    to_remove = [api for api, (_, sid) in _registry.items() if sid == source_id]
    for api in to_remove:
        del _registry[api]


def clear_api_providers() -> None:
    global ApiProvider
    _registry.clear()
