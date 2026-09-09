"""Klasa bazowa dla encji domenowych (Entity).

Tożsamość jest nieprzezroczysta (``TId``) i niemutowalna po konstrukcji.
Równość i haszowanie opierają się wyłącznie na tożsamości, nigdy na zawartości pól.
Dwie encje o tej samej tożsamości SĄ tą samą encją, niezależnie od ich stanu.
"""

from __future__ import annotations

from abc import ABC
from typing import TypeVar

TId = TypeVar("TId")
"""Zmienna typu powiązana z identyfikatorami encji/agregatów."""


class Entity[TId](ABC):
    __slots__ = ("_id",)

    _id: TId

    def __init__(self, id: TId) -> None:
        self._id = id

    @property
    def id(self) -> TId:
        return self._id

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return False
        if type(self) is not type(other):
            return False
        return bool(self._id == other._id)

    def __hash__(self) -> int:
        return hash(self._id)