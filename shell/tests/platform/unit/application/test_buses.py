"""Unit tests for the application buses (dispatch, registration, isolation)."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from shell.platform.application.bus.command_bus import CommandBus
from shell.platform.application.bus.event_bus import EventBus
from shell.platform.application.bus.query_bus import QueryBus
from shell.platform.application.commands.command import Command
from shell.platform.application.exceptions.application_contract_error import (
    CommandHandlerNotFoundError,
    CommandHandlerRegistrationError,
    QueryHandlerNotFoundError,
    QueryHandlerRegistrationError,
)


@dataclass(frozen=True)
class _SampleCommand(Command):
    pass


@dataclass(frozen=True)
class _OtherCommand(Command):
    pass


@dataclass(frozen=True)
class _SampleQuery:
    text: str = ""


class _RecordingHandler:
    def __init__(self, calls: list[object], *, result: object = None) -> None:
        self._calls = calls
        self._result = result

    async def handle(self, message: object) -> object:
        self._calls.append(message)
        return self._result


class _FailingHandler:
    def __init__(self, calls: list[object], error: Exception) -> None:
        self._calls = calls
        self._error = error

    async def handle(self, message: object) -> None:
        self._calls.append(message)
        raise self._error


class TestCommandBus:
    async def test_dispatch_to_registered_handler(self) -> None:
        bus = CommandBus()
        calls: list[object] = []
        bus.register(_SampleCommand, lambda: _RecordingHandler(calls, result="done"))

        assert await bus.dispatch(_SampleCommand()) == "done"
        assert len(calls) == 1

    async def test_dispatch_without_handler_raises_not_found(self) -> None:
        bus = CommandBus()

        with pytest.raises(CommandHandlerNotFoundError, match="_OtherCommand"):
            await bus.dispatch(_OtherCommand())

    def test_duplicate_registration_raises(self) -> None:
        bus = CommandBus()
        bus.register(_SampleCommand, lambda: _RecordingHandler([]))

        with pytest.raises(CommandHandlerRegistrationError, match="_SampleCommand"):
            bus.register(_SampleCommand, lambda: _RecordingHandler([]))


class TestQueryBus:
    async def test_dispatch_to_registered_handler(self) -> None:
        bus = QueryBus()
        calls: list[object] = []
        bus.register(_SampleQuery, lambda: _RecordingHandler(calls, result="answer"))

        assert await bus.dispatch(_SampleQuery()) == "answer"
        assert len(calls) == 1

    async def test_dispatch_without_handler_raises_not_found(self) -> None:
        bus = QueryBus()

        with pytest.raises(QueryHandlerNotFoundError, match="_SampleQuery"):
            await bus.dispatch(_SampleQuery())

    def test_duplicate_registration_raises(self) -> None:
        bus = QueryBus()
        bus.register(_SampleQuery, lambda: _RecordingHandler([]))

        with pytest.raises(QueryHandlerRegistrationError, match="_SampleQuery"):
            bus.register(_SampleQuery, lambda: _RecordingHandler([]))


class TestEventBus:
    async def test_publish_without_handlers_is_noop(self) -> None:
        await EventBus().publish([object()])

    async def test_failing_handler_does_not_block_siblings(self) -> None:
        bus = EventBus()
        first_calls: list[object] = []
        second_calls: list[object] = []
        bus.subscribe(str, lambda: _FailingHandler(first_calls, RuntimeError("boom")))
        bus.subscribe(str, lambda: _RecordingHandler(second_calls))

        with pytest.raises(RuntimeError, match="boom"):
            await bus.publish(["event"])

        assert len(first_calls) == 1
        assert len(second_calls) == 1

    async def test_unhandled_event_type_is_noop(self) -> None:
        bus = EventBus()
        calls: list[object] = []
        bus.subscribe(str, lambda: _RecordingHandler(calls))

        await bus.publish([42])

        assert calls == []
