"""Round-trip tests for session-service Session SQL mapper.

Split from the former cross-BC suite so each BC owns its mapper tests
(``shell/tests/<bc>/`` may import only that BC plus ``shell.platform``).
"""

from __future__ import annotations

from datetime import UTC, datetime

from shell.platform.domain.value_objects.changed_at import ChangedAt
from shell.platform.domain.value_objects.created_at import CreatedAt
from shell.platform.domain.value_objects.timestamp import Timestamp
from shell.session_service.domain.session.aggregates.session import Session
from shell.session_service.domain.session.aggregates.session.value_objects.session_id import (
    SessionId,
)
from shell.session_service.domain.session.value_objects.session_status import SessionStatus
from shell.session_service.domain.session.value_objects.user_id_ref import UserIdRef
from shell.session_service.infrastructure.session.session.persistence.sql.mappers import (
    session_entity_to_model,
    session_model_to_entity,
)

_NOW = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)


def _raw(dt: datetime | Timestamp | None) -> datetime | None:
    """Extract raw datetime from a datetime or Timestamp."""
    if dt is None:
        return None
    return dt.value if isinstance(dt, Timestamp) else dt


class TestSessionMapper:
    def test_entity_to_model(self) -> None:
        original = Session.restore(
            id=SessionId("sess-1"),
            created_at=CreatedAt.from_datetime(_NOW),
            user_id=UserIdRef("user-1"),
            status=SessionStatus.OPEN,
            opened_at=CreatedAt.from_datetime(_NOW),
        )
        model = session_entity_to_model(original)

        assert model.id == "sess-1"
        assert model.closed_at is None

    def test_entity_to_model_closed(self) -> None:
        original = Session.restore(
            id=SessionId("sess-2"),
            created_at=CreatedAt.from_datetime(_NOW),
            user_id=UserIdRef("user-2"),
            status=SessionStatus.CLOSED,
            opened_at=CreatedAt.from_datetime(_NOW),
            closed_at=ChangedAt.from_datetime(_NOW),
        )
        model = session_entity_to_model(original)

        assert model.id == "sess-2"
        assert model.closed_at is not None

    def test_round_trip(self) -> None:
        original = Session.restore(
            id=SessionId("sess-3"),
            created_at=CreatedAt.from_datetime(_NOW),
            user_id=UserIdRef("user-3"),
            status=SessionStatus.OPEN,
            opened_at=CreatedAt.from_datetime(_NOW),
        )
        model = session_entity_to_model(original)
        model.opened_at = _raw(model.opened_at)  # type: ignore[assignment]

        restored = session_model_to_entity(model)

        assert restored.id.value == "sess-3"
        assert restored.session_status == SessionStatus.OPEN
