"""Wyjątki warstwy mapowania zdarzeń domenowych na integracyjne."""

from __future__ import annotations


class IntegrationMappingError(ValueError):
    """Zdarzenie domenowe nie ma odpowiedniego kontraktu zdarzenia integracyjnego.

    Rzucony, gdy agregat emituje zdarzenie domenowe, które bounded context
    zamierza opublikować między BC, ale nie istnieje odpowiadający typ
    ``*IntegrationEvent``.

    To błąd programistyczny/konfiguracyjny, nie błąd biznesowy w runtime:
    rozwiązanie to zadeklarowanie brakującego zdarzenia integracyjnego (lub
    jawne oznaczenie zdarzenia domenowego jako wewnętrznego i poza zakresem
    publikacji outbox).

    Dziedziczy po :class:`ValueError`, by istniejące ``except ValueError``
    nadal działało.
    """