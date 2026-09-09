"""Sanityzacja komunikatów błędów do bezpiecznych odpowiedzi i logów."""

from __future__ import annotations

import re

_ERROR_MESSAGE_MAX_LENGTH = 2000
_CREDENTIAL_IN_URL = re.compile(r"(://[^/:\s]+:)[^/\s@]+@")
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)(password|passwd|pwd|secret|api[_-]?key)(\s*[:=]\s*)['\"]?[^\s'\";,]+['\"]?"
)
_AUTHORIZATION_HEADER = re.compile(
    r"(?i)(authorization)(\s*[:=]\s*)['\"]?[^\s'\";,]+(?:\s+[^\s'\";,]+)?['\"]?"
)
_BEARER_TOKEN = re.compile(r"(?i)(bearer\s+)[^\s'\";,]+")
_WINDOWS_ABSOLUTE_PATH = re.compile(r"[A-Za-z]:\\(?:[^\s'\";,\\]+\\)*([^\s'\";,\\]+)")


def sanitize_message(message: str) -> str:
    message = _CREDENTIAL_IN_URL.sub(r"\1***@", message)
    message = _SECRET_ASSIGNMENT.sub(r"\1\2***", message)
    message = _AUTHORIZATION_HEADER.sub(r"\1\2***", message)
    message = _BEARER_TOKEN.sub(r"\1***", message)
    message = _WINDOWS_ABSOLUTE_PATH.sub(r"\1", message)
    return message[:_ERROR_MESSAGE_MAX_LENGTH]


def sanitize_error_message(exc: BaseException) -> str:
    message = f"{type(exc).__name__}: {exc}"
    return sanitize_message(message)