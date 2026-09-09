"""Błąd konfiguracji repozytoriów UoW (RepositoryConfigurationError)."""

from __future__ import annotations


class RepositoryConfigurationError(ValueError):
    """Nieprawidłowa konfiguracja mapy repozytoriów SqlAlchemyUnitOfWorkBase.

    Rzucany, gdy kod programistyczny/konfiguracyjny jest niekompletny:
    komendy z różnych source services w jednej partii, nieznany typ
    repozytorium dla danego BC, pusta mapa repozytoriów przy staged
    komendach albo brak wymaganego bundle/mappera w konstruktorze.

    To błąd programistyczny/konfiguracyjny, nie błąd biznesowy w runtime:
    rozwiązanie to poprawienie ``_build_repo_map()`` lub konstrukcji UoW.

    Dziedziczy po :class:`ValueError`, by istniejące ``except ValueError``
    nadal działało.
    """
