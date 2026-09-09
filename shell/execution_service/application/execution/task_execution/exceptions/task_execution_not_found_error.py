from __future__ import annotations

from shell.platform.application.exceptions.application_error import ApplicationError


class TaskExecutionNotFoundError(ApplicationError):
    """Raised when a task execution command targets an unknown aggregate."""
