from __future__ import annotations

from datetime import UTC, datetime

from shell.platform.domain.value_objects.created_at import CreatedAt
from shell.project_service.domain.project.aggregates.project.value_objects.project_id import (
    ProjectId,
)
from shell.project_service.domain.project.aggregates.project_skill.events.project_skill_created_event import (
    ProjectSkillCreatedEvent,
)
from shell.project_service.domain.project.aggregates.project_skill.project_skill import (
    ProjectSkill,
)


def test_project_skill_creation_event_contains_project_skill_id_only() -> None:
    skill = ProjectSkill.create(
        now=CreatedAt.from_datetime(datetime(2026, 1, 1, tzinfo=UTC)),
        project_id=ProjectId("project-1"),
        skill_data="{}",
    )

    events = skill.pull_events()

    assert len(events) == 1
    event = events[0]
    assert isinstance(event, ProjectSkillCreatedEvent)
    assert event.project_skill_id == skill.id
    assert not hasattr(event, "aggregate_id")
    assert not hasattr(event, "project_id")


