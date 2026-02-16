from __future__ import annotations

from .event_stream import AssistantMessageEventStream
from .registry import get_api_provider
from .types import AssistantMessage, Context, Model, SimpleStreamOptions, StreamOptions


def _resolve_api_provider(api: str):
    provider = get_api_provider(api)
    if provider is None:
        raise ValueError(f"No API provider registered for api: {api}")
    return provider


def stream(
    model: Model,
    context: Context,
    options: StreamOptions | None = None,
) -> AssistantMessageEventStream:
    provider = _resolve_api_provider(model.api)
    return provider.stream(model, context, options)


async def complete(
    model: Model,
    context: Context,
    options: StreamOptions | None = None,
) -> AssistantMessage:
    s = stream(model, context, options)
    return await s.result()


def stream_simple(
    model: Model,
    context: Context,
    options: SimpleStreamOptions | None = None,
) -> AssistantMessageEventStream:
    provider = _resolve_api_provider(model.api)
    return provider.stream_simple(model, context, options)


async def complete_simple(
    model: Model,
    context: Context,
    options: SimpleStreamOptions | None = None,
) -> AssistantMessage:
    s = stream_simple(model, context, options)
    return await s.result()
