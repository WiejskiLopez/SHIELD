from __future__ import annotations

import pytest

from shell.platform.application.contracts.command_contract import CommandContract
from shell.platform.infrastructure.persistence.repository_configuration_error import (
    RepositoryConfigurationError,
)
from shell.platform.infrastructure.persistence.sql_alchemy_uow_base import (
    SqlAlchemyUnitOfWorkBase,
    _command_source_service,
)
from shell.session_service.application.session.session.commands.close_session_command import (
    CloseSessionCommand,
)


def test_staged_command_source_is_derived_from_command_class() -> None:
    contract = CommandContract(
        command_name="CloseSessionCommand",
        command_class=CloseSessionCommand,
        target_service="session_service",
    )

    assert _command_source_service([(contract, object())]) == "session_service"


def test_base_uow_requires_concrete_repository_map() -> None:
    assert SqlAlchemyUnitOfWorkBase.__abstractmethods__ == {"_build_repo_map"}


def test_source_service_is_required_explicitly() -> None:
    class DefinitionUnitOfWork(SqlAlchemyUnitOfWorkBase):
        def _build_repo_map(self) -> dict[type, type]:
            return {}

    with pytest.raises(TypeError, match="source_service"):
        DefinitionUnitOfWork(None, mapper=None, models=None)  # type: ignore[call-arg]


def test_empty_source_service_is_rejected() -> None:
    with pytest.raises(RepositoryConfigurationError, match="non-empty source service"):
        class InvalidUnitOfWork(SqlAlchemyUnitOfWorkBase):
            def _build_repo_map(self) -> dict[type, type]:
                return {}

        InvalidUnitOfWork(None, mapper=None, source_service="", models=None)  # type: ignore[arg-type]


def test_missing_mapper_is_rejected() -> None:
    class InvalidUnitOfWork(SqlAlchemyUnitOfWorkBase):
        def _build_repo_map(self) -> dict[type, type]:
            return {}

    with pytest.raises(RepositoryConfigurationError, match="integration mapper"):
        InvalidUnitOfWork(None, mapper=None, source_service="test", models=object())  # type: ignore[arg-type]


def test_missing_models_are_rejected() -> None:
    class InvalidUnitOfWork(SqlAlchemyUnitOfWorkBase):
        def _build_repo_map(self) -> dict[type, type]:
            return {}

    with pytest.raises(RepositoryConfigurationError, match="persistence delivery"):
        InvalidUnitOfWork(None, mapper=object(), source_service="test", models=None)  # type: ignore[arg-type]


def test_command_contracts_cannot_mix_source_services() -> None:
    contract = CommandContract(
        command_name="CloseSessionCommand",
        command_class=CloseSessionCommand,
        target_service="session_service",
    )

    class ExecutionCommand(CloseSessionCommand):
        __module__ = "shell.execution_service.application.execution.commands.fake"

    mixed_contract = CommandContract(
        command_name="ExecutionCommand",
        command_class=ExecutionCommand,
        target_service="execution_service",
    )

    with pytest.raises(RepositoryConfigurationError, match="same source service"):
        _command_source_service(
            [(contract, object()), (mixed_contract, object())]
        )
