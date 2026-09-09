"""Porty domenowe platformy."""

from __future__ import annotations

from shell.platform.domain.ports.identity import IdGenerator
from shell.platform.domain.ports.repository_port import RepositoryPort
from shell.platform.domain.ports.time import Clock

__all__ = [
    "Clock",
    "IdGenerator",
    "RepositoryPort",
]