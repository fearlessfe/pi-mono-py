from __future__ import annotations

import asyncio
from typing import Any, Callable, Generic, TypeVar

from pi_ai.types import AssistantMessage, AssistantMessageEvent

T = TypeVar("T")
R = TypeVar("R")

_SENTINEL = object()


class EventStream(Generic[T, R]):
    def __init__(
        self,
        is_complete: Callable[[T], bool],
        extract_result: Callable[[T], R],
    ) -> None:
        self._is_complete = is_complete
        self._extract_result = extract_result
        self._queue: asyncio.Queue[T | object] = asyncio.Queue()
        self._done = False
        self._loop = asyncio.get_event_loop()
        self._final_result: asyncio.Future[R] = self._loop.create_future()

    def push(self, event: T) -> None:
        if self._done:
            return
        if self._is_complete(event):
            self._done = True
            if not self._final_result.done():
                self._final_result.set_result(self._extract_result(event))
            self._queue.put_nowait(event)
            self._queue.put_nowait(_SENTINEL)
        else:
            self._queue.put_nowait(event)

    def end(self, result: R | None = None) -> None:
        self._done = True
        if result is not None and not self._final_result.done():
            self._final_result.set_result(result)
        self._queue.put_nowait(_SENTINEL)

    def __aiter__(self) -> EventStream[T, R]:
        return self

    async def __anext__(self) -> T:
        while True:
            item = await self._queue.get()
            if item is _SENTINEL:
                raise StopAsyncIteration
            if self._done and self._queue.empty():
                return item  # type: ignore[return-value]
            return item  # type: ignore[return-value]

    async def result(self) -> R:
        return await self._final_result


class AssistantMessageEventStream(EventStream[AssistantMessageEvent, AssistantMessage]):
    def __init__(self) -> None:
        super().__init__(
            is_complete=lambda event: event.type in ("done", "error"),
            extract_result=lambda event: (
                event.message if event.type == "done" else event.error  # type: ignore[union-attr]
            ),
        )
