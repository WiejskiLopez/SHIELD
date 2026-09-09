from __future__ import annotations

from datetime import UTC, datetime

from shell.platform.domain.value_objects.created_at import CreatedAt
from shell.user_service.domain.user.aggregates.user_skill.events.user_skill_created_event import (
    UserSkillCreatedEvent,
)
from shell.user_service.domain.user.aggregates.user_skill.user_skill import UserSkill
from shell.user_service.domain.user.value_objects.user_id import UserId


def test_user_skill_creation_event_contains_user_skill_id_only() -> None:
    skill = UserSkill.create(
        now=CreatedAt.from_datetime(datetime(2026, 1, 1, tzinfo=UTC)),
        user_id=UserId("user-1"),
        skill_data="{}",
    )

    events = skill.pull_events()

    assert len(events) == 1
    event = events[0]
    assert isinstance(event, UserSkillCreatedEvent)
    assert event.user_skill_id == skill.id
    assert not hasattr(event, "aggregate_id")
    assert not hasattr(event, "user_id")


