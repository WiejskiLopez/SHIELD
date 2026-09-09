from __future__ import annotations

from shell.platform.domain.base import Entity
from shell.tests.shared.sample_aggregate import _SampleEntity, _SampleId


class _OtherEntity(Entity[_SampleId]):
    __slots__ = ()

    def __init__(self, id: _SampleId) -> None:
        super().__init__(id)


class TestEntityIdentity:
    def test_id_is_exposed_via_property(self) -> None:
        e = _SampleEntity(_SampleId("a"), "x")
        assert e.id == _SampleId("a")

    def test_equality_is_identity_based(self) -> None:
        a1 = _SampleEntity(_SampleId("same"), "label-1")
        a2 = _SampleEntity(_SampleId("same"), "label-2-different")
        assert a1 == a2

    def test_inequality_for_different_ids(self) -> None:
        a = _SampleEntity(_SampleId("a"), "x")
        b = _SampleEntity(_SampleId("b"), "x")
        assert a != b

    def test_hash_matches_identity(self) -> None:
        a1 = _SampleEntity(_SampleId("same"), "label-1")
        a2 = _SampleEntity(_SampleId("same"), "label-2")
        assert hash(a1) == hash(a2)
        assert {a1, a2} == {a1}

    def test_compare_with_non_entity_returns_not_implemented(self) -> None:
        e = _SampleEntity(_SampleId("a"), "x")
        assert (e == "not-an-entity") is False
        assert (e != "not-an-entity") is True

    def test_equality_requires_same_entity_type(self) -> None:
        entity = _SampleEntity(_SampleId("same"), "x")
        other_type = _OtherEntity(_SampleId("same"))
        assert (entity == other_type) is False
        assert (entity != other_type) is True

    def test_equality_returns_plain_bool(self) -> None:
        entity = _SampleEntity(_SampleId("a"), "x")
        assert type(entity.__eq__("not-an-entity")) is bool
        assert type(entity.__eq__(_SampleEntity(_SampleId("a"), "y"))) is bool
