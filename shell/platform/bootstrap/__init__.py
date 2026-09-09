"""Platform bootstrap package — shared composition-root helpers."""

from __future__ import annotations

from shell.platform.bootstrap.delivery import DeliveryConfig, build_delivery_config

__all__ = [
    "DeliveryConfig",
    "build_delivery_config",
]
