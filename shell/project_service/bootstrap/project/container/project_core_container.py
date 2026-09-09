from __future__ import annotations

from typing import TYPE_CHECKING

from dependency_injector import containers, providers
from saga_orchestration.bootstrap.install import install_saga

from shell.platform.application.bus.command_bus import CommandBus
from shell.platform.application.bus.command_bus_publisher import CommandBusPublisher
from shell.platform.application.bus.event_bus import EventBus
from shell.platform.application.bus.query_bus import QueryBus
from shell.platform.infrastructure.identity.uuid_id_generator import UuidIdGenerator
from shell.platform.infrastructure.mapping.integration_event_mapper import (
    IntegrationEventMapper,
)
from shell.platform.infrastructure.messaging.command import CommandInboxConsumer, CommandOutboxRelay
from shell.platform.infrastructure.messaging.command.command_inbox_processor import (
    CommandInboxProcessor,
)
from shell.platform.infrastructure.messaging.command_transport.rabbit import (
    RabbitCommandDeliveryTransport,
)
from shell.platform.infrastructure.messaging.event import EventInboxConsumer, EventOutboxRelay
from shell.platform.infrastructure.messaging.event.event_inbox_processor import (
    EventInboxProcessor,
)
from shell.platform.infrastructure.messaging.event_transport.rabbit import (
    RabbitEventDeliveryTransport,
)
from shell.platform.infrastructure.messaging.inbox.envelope_validator import (
    envelope_policy_from_catalog,
)
from shell.platform.infrastructure.messaging.inbox.inbox_metrics_service import (
    InboxMetricsService,
)
from shell.platform.infrastructure.messaging.outbox.outbox_metrics_service import (
    OutboxMetricsService,
)
from shell.platform.infrastructure.persistence.sql import build_session_factory
from shell.platform.infrastructure.serialization.registries.event_registry import (
    build_domain_event_mapper_registry,
)
from shell.platform.infrastructure.serialization.upcaster import PayloadUpcaster
from shell.platform.infrastructure.time.system_clock import SystemClock
from shell.platform.observability.infrastructure.health.composite_readiness_probe import (
    CompositeReadinessProbe,
)
from shell.platform.observability.infrastructure.health.rabbit_readiness_probe import (
    RabbitReadinessProbe,
)
from shell.platform.observability.infrastructure.health.saga_timeout_readiness_probe import (
    SagaTimeoutReadinessProbe,
)
from shell.platform.observability.infrastructure.health.sql_readiness_probe import SqlReadinessProbe
from shell.platform.observability.infrastructure.metrics.prometheus_metrics_backend import (
    PrometheusMetricsBackend,
)
from shell.platform.observability.infrastructure.metrics.registry import MetricsRegistry
from shell.project_service.application.project.project.command_handlers.change_project_handler import (
    ChangeProjectHandler,
)
from shell.project_service.application.project.project.command_handlers.create_project_handler import (
    CreateProjectHandler,
)
from shell.project_service.application.project.project.command_handlers.delete_project_handler import (
    DeleteProjectHandler,
)
from shell.project_service.application.project.project.commands.change_project_command import (
    ChangeProjectCommand,
)
from shell.project_service.application.project.project.commands.create_project_command import (
    CreateProjectCommand,
)
from shell.project_service.application.project.project.commands.delete_project_command import (
    DeleteProjectCommand,
)
from shell.project_service.application.project.project.queries.get_project_by_id_query import (
    GetProjectByIdQuery,
)
from shell.project_service.application.project.project.queries.list_projects_query import (
    ListProjectsQuery,
)
from shell.project_service.application.project.project.query_handlers.get_project_by_id_handler import (
    GetProjectByIdHandler,
)
from shell.project_service.application.project.project.query_handlers.list_projects_handler import (
    ListProjectsHandler,
)
from shell.project_service.application.project.project_provision.command_handlers.provision_workspace_handler import (
    ProvisionWorkspaceHandler,
)
from shell.project_service.application.project.project_provision.command_handlers.release_workspace_handler import (
    ReleaseWorkspaceHandler,
)
from shell.project_service.application.project.project_provision.commands.provision_workspace_command import (
    ProvisionWorkspaceCommand,
)
from shell.project_service.application.project.project_provision.commands.release_workspace_command import (
    ReleaseWorkspaceCommand,
)
from shell.project_service.application.project.project_provision.commands.start_project_provision_command import (
    StartProjectProvisionCommand,
)
from shell.project_service.application.project.project_provision.integration_events.workspace_provision_failed_integration_event import (
    WorkspaceProvisionFailedIntegrationEvent,
)
from shell.project_service.application.project.project_provision.integration_events.workspace_provisioned_integration_event import (
    WorkspaceProvisionedIntegrationEvent,
)
from shell.project_service.application.project.project_provision.integration_events.workspace_released_integration_event import (
    WorkspaceReleasedIntegrationEvent,
)
from shell.project_service.application.project.project_skill.queries.get_project_skill_by_id_query import (
    GetProjectSkillByIdQuery,
)
from shell.project_service.application.project.project_skill.query_handlers.get_project_skill_by_id_handler import (
    GetProjectSkillByIdHandler,
)
from shell.project_service.bootstrap.project.command_contracts import (
    PROJECT_COMMAND_CONTRACTS,
    build_project_command_registry,
)
from shell.project_service.bootstrap.project.contract_catalog import PROJECT_CONTRACT_CATALOG
from shell.project_service.bootstrap.project.delivery import build_delivery_config
from shell.project_service.bootstrap.project.event_registry import build_project_event_registry
from shell.project_service.infrastructure.project.persistence.sql.models.base import (
    PERSISTENCE_DELIVERY_MODELS,
    SAGA_MODELS,
)
from shell.project_service.infrastructure.project.project.persistence.sql.services.project_query_service import (
    ProjectQueryService,
)
from shell.project_service.infrastructure.project.project.persistence.sql.unit_of_work import (
    SqlAlchemyProjectUnitOfWork,
)
from shell.project_service.infrastructure.project.project_skill.persistence.sql.services.project_skill_query_service import (
    ProjectSkillQueryService,
)
from shell.project_service.infrastructure.project.saga.saga_result_writer import (
    SqlProvisionResultWriter,
)
from shell.project_service.infrastructure.project.saga.saga_wiring import (
    build_project_saga_unit_of_work_factory,
)
from shell.project_service.process.project.project_provision.handlers.provision_result_bridge_handler import (
    ProvisionResultBridgeHandler,
)
from shell.project_service.process.project.project_provision.handlers.release_result_bridge_handler import (
    ReleaseResultBridgeHandler,
)
from shell.project_service.process.project.project_provision.handlers.start_saga_bridge_handler import (
    StartProjectProvisionBridgeHandler,
)
from shell.project_service.process.project.project_provision.saga_definition import (
    PROJECT_PROVISION_STEPS_V2,
    SAGA_TYPE,
)
from shell.project_service.process.project.project_provision.saga_dispatch import (
    ProjectProvisionDispatchResolver,
)

if TYPE_CHECKING:
    from saga_orchestration.bootstrap.install import SagaWiring
    from saga_orchestration.infrastructure.saga_timeout_worker import SagaTimeoutWorker


def _saga_timeout_worker(*, wiring: SagaWiring) -> SagaTimeoutWorker:
    """Worker timeoutów z wiringu install_saga (extra_processor w main --worker)."""
    return wiring.timeout_worker


class ProjectCoreContainer(containers.DeclarativeContainer):
    config = providers.Configuration()
    session_factory = providers.Singleton(build_session_factory, url=config.db_url)
    command_bus = providers.Singleton(CommandBus)
    command_bus_publisher = providers.Singleton(CommandBusPublisher, command_bus=command_bus)
    persistence_delivery_models = providers.Object(PERSISTENCE_DELIVERY_MODELS)
    event_bus = providers.Singleton(EventBus)
    event_registry = providers.Singleton(build_project_event_registry)
    event_inbox_processor_factory = providers.Factory(
        EventInboxProcessor,
        session_factory=session_factory,
        event_bus=event_bus,
        models=persistence_delivery_models.provided.events,
        registry=event_registry,
        worker_id=config.worker_id,
        heartbeat_interval_seconds=config.worker_heartbeat_interval_seconds,
        max_batch_time_seconds=config.worker_max_batch_time_seconds,
        envelope_policy=envelope_policy_from_catalog(PROJECT_CONTRACT_CATALOG),
        upcaster=providers.Singleton(PayloadUpcaster),
    )
    event_delivery_transport = providers.Factory(
        RabbitEventDeliveryTransport, url=config.broker_url
    )
    outbox_to_transport_relay_factory = providers.Factory(
        EventOutboxRelay,
        session_factory=session_factory,
        models=persistence_delivery_models.provided.events,
        transport=event_delivery_transport,
    )
    command_delivery_transport = providers.Factory(
        RabbitCommandDeliveryTransport, url=config.broker_url
    )
    command_outbox_to_transport_relay_factory = providers.Factory(
        CommandOutboxRelay,
        session_factory=session_factory,
        models=persistence_delivery_models.provided.commands,
        transport=command_delivery_transport,
    )
    saga_models = providers.Object(SAGA_MODELS)
    saga_result_writer = providers.Singleton(
        SqlProvisionResultWriter,
        event_models=persistence_delivery_models.provided.events,
    )
    provision_workspace_handler_factory = providers.Factory(
        ProvisionWorkspaceHandler,
        result_writer=saga_result_writer,
    )
    release_workspace_handler_factory = providers.Factory(
        ReleaseWorkspaceHandler,
        result_writer=saga_result_writer,
    )
    command_registry = providers.Object(build_project_command_registry())
    delivery_config = providers.Singleton(
        build_delivery_config,
        models=persistence_delivery_models,
        event_registry=event_registry,
        command_registry=command_registry,
        event_bus=event_bus,
        command_bus=command_bus,
        event_transport=event_delivery_transport,
        command_transport=command_delivery_transport,
        session_factory=session_factory,
    )
    command_inbox_processor_factory = providers.Factory(
        CommandInboxProcessor,
        session_factory=session_factory,
        dispatcher=command_bus_publisher,
        models=persistence_delivery_models.provided.commands,
        registry=command_registry,
        worker_id=config.command_worker_id,
        heartbeat_interval_seconds=config.worker_heartbeat_interval_seconds,
        max_batch_time_seconds=config.worker_max_batch_time_seconds,
        upcaster=providers.Singleton(PayloadUpcaster),
    )
    rabbit_command_inbox_consumer_factory = providers.Factory(
        CommandInboxConsumer,
        url=config.broker_url,
        session_factory=session_factory,
        models=persistence_delivery_models.provided.commands,
        service_name="project",
    )
    rabbit_inbox_consumer_factory = providers.Factory(
        EventInboxConsumer,
        url=config.broker_url,
        session_factory=session_factory,
        models=persistence_delivery_models.provided.events,
        queue_name="shell-project-event-inbox",
        routing_keys=["event.#"],
    )
    metrics_exporter = providers.Singleton(MetricsRegistry)
    metrics_backend = providers.Singleton(PrometheusMetricsBackend, registry=metrics_exporter)
    inbox_metrics_service = providers.Singleton(
        InboxMetricsService,
        session_factory=session_factory,
        inbox_model=persistence_delivery_models.provided.events.inbox,
        backend=metrics_backend,
    )
    outbox_metrics_service = providers.Singleton(
        OutboxMetricsService,
        session_factory=session_factory,
        outbox_model=persistence_delivery_models.provided.events.outbox,
        backend=metrics_backend,
    )
    readiness_probe = providers.Singleton(
        CompositeReadinessProbe,
        probes=providers.List(
            providers.Singleton(
                SqlReadinessProbe,
                session_factory=session_factory,
                inbox_model=persistence_delivery_models.provided.events.inbox,
                max_backlog=1000,
                worker_heartbeat_model=persistence_delivery_models.provided.worker_heartbeat,
            ),
            providers.Singleton(
                RabbitReadinessProbe,
                url_provider=providers.Object(config.broker_url),
            ),
            providers.Singleton(
                SagaTimeoutReadinessProbe,
                session_factory=session_factory,
                timeout_model=saga_models.provided.timeout,
                max_backlog=100,
            ),
        ),
    )
    integration_mapper = providers.Singleton(
        IntegrationEventMapper,
        integration_events=build_domain_event_mapper_registry(
            build_project_event_registry()
        ),
    )
    unit_of_work_factory = providers.Factory(
        SqlAlchemyProjectUnitOfWork,
        session_factory=session_factory,
        mapper=integration_mapper,
        source_service="project_service",
        models=persistence_delivery_models,
    )
    clock_factory = providers.Factory(SystemClock)
    id_generator_factory = providers.Factory(UuidIdGenerator)
    saga_uow_factory = providers.Singleton(
        build_project_saga_unit_of_work_factory,
        session_factory=session_factory,
        models=saga_models,
        commands_models=persistence_delivery_models.provided.commands,
        contracts=providers.Object(PROJECT_COMMAND_CONTRACTS),
        registries=providers.Object({SAGA_TYPE: PROJECT_PROVISION_STEPS_V2}),
    )
    saga_dispatch_resolver = providers.Singleton(ProjectProvisionDispatchResolver)
    saga_wiring = providers.Singleton(
        install_saga,
        uow_factory=saga_uow_factory,
        dispatch_resolver=saga_dispatch_resolver,
        clock=clock_factory,
        ids=id_generator_factory,
        source_service="project",
        owner="project-saga-timeout",
    )
    start_saga_bridge_handler_factory = providers.Factory(
        StartProjectProvisionBridgeHandler,
        start_handler=saga_wiring.provided.start_handler,
    )
    provision_result_bridge_handler_factory = providers.Factory(
        ProvisionResultBridgeHandler,
        advance_handler=saga_wiring.provided.advance_handler,
    )
    release_result_bridge_handler_factory = providers.Factory(
        ReleaseResultBridgeHandler,
        advance_handler=saga_wiring.provided.advance_handler,
    )
    saga_timeout_worker_factory = providers.Factory(
        _saga_timeout_worker,
        wiring=saga_wiring,
    )
    query_bus = providers.Singleton(QueryBus)
    project_query_service = providers.Singleton(
        ProjectQueryService, session_factory=session_factory
    )
    project_skill_query_service = providers.Singleton(
        ProjectSkillQueryService, session_factory=session_factory
    )
    get_project_skill_by_id_handler_factory = providers.Factory(
        GetProjectSkillByIdHandler, queries=project_skill_query_service
    )
    create_project_handler_factory = providers.Factory(
        CreateProjectHandler,
        unit_of_work=unit_of_work_factory,
        clock=clock_factory,
        id_generator=id_generator_factory,
    )
    change_project_handler_factory = providers.Factory(
        ChangeProjectHandler, unit_of_work=unit_of_work_factory, clock=clock_factory
    )
    delete_project_handler_factory = providers.Factory(
        DeleteProjectHandler, unit_of_work=unit_of_work_factory, clock=clock_factory
    )
    get_project_by_id_handler_factory = providers.Factory(
        GetProjectByIdHandler, queries=project_query_service
    )
    list_projects_handler_factory = providers.Factory(
        ListProjectsHandler, queries=project_query_service
    )


def configure_project_container(container: ProjectCoreContainer) -> None:
    container.command_bus().register(CreateProjectCommand, container.create_project_handler_factory)
    container.command_bus().register(ChangeProjectCommand, container.change_project_handler_factory)
    container.command_bus().register(DeleteProjectCommand, container.delete_project_handler_factory)
    container.command_bus().register(
        StartProjectProvisionCommand, container.start_saga_bridge_handler_factory
    )
    container.command_bus().register(
        ProvisionWorkspaceCommand, container.provision_workspace_handler_factory
    )
    container.command_bus().register(
        ReleaseWorkspaceCommand, container.release_workspace_handler_factory
    )
    container.event_bus().subscribe(
        WorkspaceProvisionedIntegrationEvent,
        container.provision_result_bridge_handler_factory,
    )
    container.event_bus().subscribe(
        WorkspaceProvisionFailedIntegrationEvent,
        container.provision_result_bridge_handler_factory,
    )
    container.event_bus().subscribe(
        WorkspaceReleasedIntegrationEvent,
        container.release_result_bridge_handler_factory,
    )
    container.query_bus().register(GetProjectByIdQuery, container.get_project_by_id_handler_factory)
    container.query_bus().register(ListProjectsQuery, container.list_projects_handler_factory)
    container.query_bus().register(
        GetProjectSkillByIdQuery, container.get_project_skill_by_id_handler_factory
    )
