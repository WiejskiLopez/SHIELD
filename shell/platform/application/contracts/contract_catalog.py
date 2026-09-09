"""Katalog kontraktów (ContractCatalog) — jawny rejestr publicznych kontraktów między BC na BC.

Katalog jest jedynym źródłem prawdy o tym, jakie typy zdarzeń/komend dany bounded context
publicznie wystawia lub konsumuje. Rejestruje właściciela, producentów i konsumentów
oraz wspierane wersje schematów, aby rejestr deserializacji nigdy nie był jedynym
autorytetem istnienia kontraktu.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from shell.platform.application.exceptions.application_contract_error import (
    ContractCatalogCoverageError,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping


@dataclass(frozen=True, slots=True)
class ContractEntry:
    type_name: str
    owner: str
    supported_schema_versions: frozenset[int] = frozenset({1})
    producers: tuple[str, ...] = ()
    consumers: tuple[str, ...] = ()
    retry_policy: str = "default"


@dataclass(frozen=True, slots=True)
class ContractCatalog:
    owner: str
    entries: tuple[ContractEntry, ...]

    def names(self) -> set[str]:
        return {entry.type_name for entry in self.entries}

    def by_name(self, type_name: str) -> ContractEntry | None:
        for entry in self.entries:
            if entry.type_name == type_name:
                return entry
        return None

    def assert_covers(self, registered: Iterable[str]) -> None:
        """Rzuć wyjątek, jeśli jakikolwiek zarejestrowany typ nie ma wpisu w katalogu."""
        registered_set = set(registered)
        missing = registered_set - self.names()
        if missing:
            raise ContractCatalogCoverageError(
                f"Kontrakt katalogu {self.owner} brakuje wpisów dla: "
                + ", ".join(sorted(missing))
            )


def build_contract_catalog(
    owner: str,
    entries: Iterable[ContractEntry],
) -> ContractCatalog:
    return ContractCatalog(owner=owner, entries=tuple(entries))


def build_contract_catalog_from_registry(
    owner: str,
    registry: Mapping[str, object],
    *,
    extra_consumed: Mapping[str, tuple[str, ...]] | None = None,
) -> ContractCatalog:
    """Zbuduj katalog z rejestru BC.

    Każdy zarejestrowany typ staje się ``ContractEntry`` własnym przez ``owner``
    (produkowanym przez właściciela BC). Typy, które BC dodatkowo konsumuje z innych BC,
    można wymienić w ``extra_consumed`` z kluczem będącym BC-konsumentem.

    Typy w ``extra_consumed`` muszą już być obecne w ``registry`` (są rejestrowane
    przez rejestr zdarzeń BC jako jawnie konsumowane kontrakty).
    """
    consumed = dict(extra_consumed or {})
    entries = [
        ContractEntry(
            type_name=type_name,
            owner=owner,
            producers=(owner,),
            consumers=consumed.get(type_name, ()),
        )
        for type_name in registry
    ]
    return ContractCatalog(owner=owner, entries=tuple(entries))