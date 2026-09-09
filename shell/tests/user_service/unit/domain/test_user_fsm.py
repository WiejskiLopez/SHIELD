from __future__ import annotations

from datetime import UTC, datetime

import pytest

from shell.platform.domain.value_objects.created_at import CreatedAt
from shell.platform.domain.value_objects.occurred_at import OccurredAt
from shell.user_service.domain.user.aggregates.user.exceptions.user_state_transition_error import (
    UserStateTransitionError,
)
from shell.user_service.domain.user.aggregates.user.user import User
from shell.user_service.domain.user.value_objects.user_email import UserEmail
from shell.user_service.domain.user.value_objects.user_id import UserId
from shell.user_service.domain.user.value_objects.user_status import UserStatus

_NOW_DT = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
_NOW = CreatedAt.from_datetime(_NOW_DT)
_OCCURRED = OccurredAt.from_datetime(_NOW_DT)


def _user() -> User:
    return User.create(
        id=UserId.generate(),
        email=UserEmail("user@example.com"),
        now=_NOW,
    )


def _assert_transition_events(user: User, intent_event_name: str) -> None:
    events = user.pull_events()
    assert len(events) == 2
    assert type(events[0]).__name__ == "UserChangedEvent"
    assert type(events[1]).__name__ == intent_event_name


class TestUserFsm:
    def test_disable_emits_changed_event(self) -> None:
        user = _user()
        user.pull_events()
        user.disable(now=_OCCURRED)
        assert user.status == UserStatus.DISABLED
        _assert_transition_events(user, "UserDisabledEvent")

    def test_enable_emits_changed_event(self) -> None:
        user = _user()
        user.pull_events()
        user.disable(now=_OCCURRED)
        user.pull_events()
        user.enable(now=_OCCURRED)
        assert user.status == UserStatus.ACTIVE
        _assert_transition_events(user, "UserEnabledEvent")

    def test_enable_on_active_raises_and_emits_no_event(self) -> None:
        user = _user()
        user.pull_events()
        with pytest.raises(UserStateTransitionError):
            user.enable(now=_OCCURRED)
        assert user.pull_events() == []
