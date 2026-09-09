"""Błąd domenowy (DomainError).

Klasa bazowa dla błędów spowodowanych naruszeniem reguł lub invariantów
domeny. Używana do sygnalizowania naruszeń reguł biznesowych.
"""

from __future__ import annotations


class DomainError(Exception):
    pass