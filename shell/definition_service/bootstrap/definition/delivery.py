"""Delivery configuration for the definition bounded context.

Thin re-export of the platform-owned delivery configuration (pkt 25).
"""

from __future__ import annotations

from shell.platform.bootstrap.delivery import DeliveryConfig, build_delivery_config

__all__ = [
    "DeliveryConfig",
    "build_delivery_config",
]
