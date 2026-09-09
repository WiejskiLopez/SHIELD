from __future__ import annotations

import pytest
from pydantic import ValidationError

from shell.project_service.framework.project.project.api.change_project_request import (
    ChangeProjectRequest,
)
from shell.project_service.framework.project.project.api.create_project_request import (
    CreateProjectRequest,
)


def test_create_project_request_accepts_http_repository_url() -> None:
    request = CreateProjectRequest(name="demo", repo_url="https://github.com/acme/demo")

    assert str(request.repo_url) == "https://github.com/acme/demo"


@pytest.mark.parametrize("request_type", [CreateProjectRequest, ChangeProjectRequest])
def test_project_request_rejects_invalid_repository_url(request_type: type[object]) -> None:
    payload = {"repo_url": "not-a-url"}
    if request_type is CreateProjectRequest:
        payload["name"] = "demo"

    with pytest.raises(ValidationError):
        request_type.model_validate(payload)


@pytest.mark.parametrize("request_type", [CreateProjectRequest, ChangeProjectRequest])
def test_project_request_rejects_overlong_repository_url(request_type: type[object]) -> None:
    payload = {"repo_url": f"https://example.com/{'a' * 2040}"}
    if request_type is CreateProjectRequest:
        payload["name"] = "demo"

    with pytest.raises(ValidationError):
        request_type.model_validate(payload)