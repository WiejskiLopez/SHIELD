"""Unit tests for ApiVersionRegistry natural version ordering."""

from __future__ import annotations

import pytest

from shell.platform.framework.api.version import ApiVersionInfo, ApiVersionRegistry


def _registry(*versions: str) -> ApiVersionRegistry:
    return ApiVersionRegistry([ApiVersionInfo(version=version) for version in versions])


def test_latest_orders_v10_after_v2() -> None:
    registry = _registry("v1", "v2", "v10")

    assert registry.latest == "v10"


def test_list_versions_sorts_naturally_descending() -> None:
    registry = _registry("v2", "v10", "v1")

    assert [entry["version"] for entry in registry.list_versions()] == ["v10", "v2", "v1"]


def test_single_version_registry() -> None:
    registry = _registry("v1")

    assert registry.latest == "v1"
    assert [entry["version"] for entry in registry.list_versions()] == ["v1"]


def test_empty_registry_rejected() -> None:
    with pytest.raises(ValueError, match="At least one API version"):
        ApiVersionRegistry([])
