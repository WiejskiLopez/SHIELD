"""Konfiguracyjne kawałki (slices) z jawnymi granicami własności."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shell.platform.infrastructure.configuration.shell_config import EventsConfig


@dataclass(frozen=True, slots=True)
class DeploymentConfig:
    """Wartości własne wdrożenia i kompozycji root usługi."""

    profile: str
    database_url: str


@dataclass(frozen=True, slots=True)
class PlatformRuntimeConfig:
    """Neutralne ustawienia techniczne współdzielone przez adaptery i workery platformy."""

    log_level: str
    events: EventsConfig


@dataclass(frozen=True, slots=True)
class AuthConfig:
    """Dane wejściowe uwierzytelniania przekazywane do adapterów auth bez ujawniania sekretów."""

    api_key: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class ServiceConfig:
    """Ustawienia używane tylko przez usługę lub jej własnych workerów."""

    max_step: int
    max_parallel: int
    seed_dev_data: bool
    reset_db: bool