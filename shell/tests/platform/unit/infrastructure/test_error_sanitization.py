"""Unit tests for delivery error sanitization (no secrets, no absolute paths)."""

from __future__ import annotations

import pytest

from shell.platform.application.error_sanitization import (
    sanitize_error_message,
    sanitize_message,
)


def test_sanitize_message_truncates_to_2000_characters() -> None:
    assert len(sanitize_message("x" * 5000)) == 2000


def test_sanitize_error_message_truncates_to_2000_characters() -> None:
    assert len(sanitize_error_message(RuntimeError("x" * 5000))) == 2000


def test_sanitize_message_masks_credentials_in_url() -> None:
    sanitized = sanitize_message("connect failed: amqp://user:super-secret@broker:5672/vhost")

    assert "super-secret" not in sanitized
    assert "user:***@" in sanitized


@pytest.mark.parametrize(
    "raw",
    [
        "database password=super-secret failed",
        "login failed: PASSWORD: super-secret",
        "config passwd=topsecret missing",
        "auth pwd=topsecret expired",
        "request failed api_key=live-secret-key",
        "request failed api-key=live-secret-key",
        "request failed apikey=live-secret-key",
        "header API_KEY: live-secret-key rejected",
        "connection failed secret=topsecret",
        "call failed with Bearer live-secret-token-here",
        "Authorization: Bearer live-secret-token-here",
        "authorization=Basic dXNlcjpwYXNz denied",
    ],
)
def test_sanitize_message_masks_secrets_case_insensitive(raw: str) -> None:
    sanitized = sanitize_message(raw)

    assert "super-secret" not in sanitized
    assert "topsecret" not in sanitized
    assert "live-secret" not in sanitized
    assert "dXNlcjpwYXNz" not in sanitized
    assert "***" in sanitized


def test_sanitize_error_message_masks_secrets_from_exception() -> None:
    sanitized = sanitize_error_message(RuntimeError("connect with password=super-secret"))

    assert "RuntimeError" in sanitized
    assert "super-secret" not in sanitized
    assert "***" in sanitized


def test_sanitize_message_shortens_windows_absolute_path_to_basename() -> None:
    sanitized = sanitize_message(r"cannot read C:\Users\runner\config\default.yaml: broken")

    assert "C:\\" not in sanitized
    assert "Users" not in sanitized
    assert sanitized.endswith("default.yaml: broken") or "default.yaml" in sanitized


def test_sanitize_error_message_shortens_windows_absolute_path_to_basename() -> None:
    sanitized = sanitize_error_message(ValueError(r"bad file C:\Temp\data\prod.yaml"))

    assert "C:\\" not in sanitized
    assert "prod.yaml" in sanitized


def test_sanitize_message_keeps_benign_text_intact() -> None:
    assert sanitize_message("connection refused by broker") == "connection refused by broker"
