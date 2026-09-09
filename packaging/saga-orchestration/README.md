# saga-orchestration — podpinanie do serwisu

> Biblioteka wprocesowa (NIE mikroserwis). Nie ma portu, `DATABASE_URL`, kolejki ani API.
> Po podpięciu jej komponenty żyją WEWNĄTRZ serwisu-gospodarza: tabele
> `saga_instance / saga_timeout` w JEGO bazie (`MetaData` serwisu), handlery w JEGO
> busach, worker w JEGO procesie. Komendy między serwisami idą jak dotąd:
> `command_outbox -> relay -> RabbitMQ -> inbox`.
> Pełne uzasadnienie architektury: `SAGA.MD` w root repo.

## 0. Co dostajesz, a czego nie

Dostajesz mechanizm: agregat `Saga` (maszyna stanów), porty
(`SagaRepository`, `SagaUnitOfWork`, `CommandOutboxWriter`, `Clock`, `IdGenerator`),
implementacje SQL/InMemory, handlery `Start / Advance / Timeout`, worker timeoutów,
łańcuch migracji `saga_0001 / saga_0002`, funkcję `install_saga()`.

NIE dostajesz: konkretnej sagi (definicja kroków + polityka zostaje w serwisie,
np. `shell/project_service/process/project/project_provision/`),
modeli serwisu, routerów, brokera. Libka nie importuje `shell.*` (nawet w `TYPE_CHECKING`)
i nie zna `DATABASE_URL` żadnego serwisu.

Serwis bez sagi nie robi NIC z tej listy (zero tabel, zero providerów, zero importów).

## 1. Instalacja pakietu

```text
pip install -e packaging/saga-orchestration
```

Zależności to tylko `sqlalchemy + alembic`. Nie ma extra `shell` — libka nie zależy
od `shell-platform`. To serwis adaptuje się do portów libki (Krok 4), nie odwrotnie.

Weryfikacja:

```powershell
python -c "import saga_orchestration.domain.saga, saga_orchestration.bootstrap.install; print('OK')"
Select-String -Path "packaging/saga-orchestration/saga_orchestration/**/*.py" -Pattern "shell\.platform|shell-platform"
# oczekiwane: 0 trafień
```

## 2. Tabele: jeden wiersz w `base.py` serwisu

```python
# shell/<bc>_service/infrastructure/<bc>/persistence/sql/models/base.py
from saga_orchestration.infrastructure.sqlalchemy.saga_models import build_saga_models

SAGA_MODELS = build_saga_models(TwojaBase)  # TwojaBase = Base TEGO serwisu, jego MetaData
```

To jedyne miejsce gdzie modele sagi spotykają serwis. Nic globalnie, nic w platformie.
Serwis bez sagi pomija ten wiersz i nie ma tabel.

## 3. Migracje: łańcuch libki na bazie serwisu

Uruchom na bazie serwisu (serwis jest właścicielem bazy, libka tylko dostarcza skrypty):

- `saga_0001_instance` → tworzy `saga_instance`,
- `saga_0002_timeout` → tworzy `saga_timeout`.

```powershell
alembic -c shell/<bc>_service/migrations/alembic.ini upgrade head
# świeża baza serwisu Z sagą ma saga_instance + saga_timeout; bez sagi — nie ma
```

Zasady: `downgrade()` usuwa tabele. Brak gałęzi kompatybilnościowych
(stare `platform_0008/0009` są skasowane — patrz `SAGA.MD` Krok 1).
Nigdy nie edytuj tych dwóch migracji w serwisie; jeśli potrzebujesz kolumny,
dopisz `saga_0003_*` w łańcuchu libki.

## 4. Adaptery: ~25 linii po stronie serwisu (jedyny kod do napisania ręcznie)

Libka potrzebuje 4 rzeczy z serwisu. Każdą dajesz jako cienki adapter
(zero logiki biznesowej):

```python
# shell/<bc>_service/infrastructure/<bc>/saga/saga_wiring.py
from __future__ import annotations

from shell.platform.infrastructure.context import get_session_scope


class ServiceSessionScope:
    """Bieżąca sesja UoW serwisu -> port libki."""

    def current(self) -> object | None:
        scope = get_session_scope()
        return None if scope is None else scope.session


class ServiceCommandOutboxWriter:
    """Wiersz libki -> wiersz command_outbox TEGO serwisu (ta sama sesja!)."""

    def __init__(self, models: object) -> None:
        self._models = models

    def append(self, row: object) -> None:
        scope = get_session_scope()
        assert scope is not None, "poza UoW nie wolno pisać do outbox"
        scope.session.add(
            self._models.commands(
                id=row.command_id,
                target_service=row.target_service,
                contract_type=row.contract_type,
                payload=row.payload,
                correlation_id=row.correlation_id,
                causation_id=row.causation_id,
            )
        )
```

Zegar i generator id bierzesz z platformy bez adaptera:
`SystemClock()`, `UuidIdGenerator()` — spełniają porty `Clock` / `IdGenerator`
strukturalnie. Fabrykę nowej sesji dla workerów dajesz jako
`lambda: TwojaSessionFactory()`.

## 5. Wiring: jedno wywołanie w composition root

```python
# shell/<bc>_service/bootstrap/<bc>/container/<bc>_core_container.py
from saga_orchestration.bootstrap.install import install_saga
from shell.<bc>_service.infrastructure.<bc>.saga.saga_wiring import (
    ServiceCommandOutboxWriter, ServiceSessionScope,
)

saga = install_saga(
    models=SAGA_MODELS,                          # z Kroku 2
    sessions=ServiceSessionScope(),              # z Kroku 4
    new_session=lambda: session_factory(),
    outbox_writer=ServiceCommandOutboxWriter(SAGA_MODELS),
    clock=SystemClock(),
    ids=UuidIdGenerator(),
)
# saga.start_handler / saga.advance_handler / saga.timeout_handler -> rejestracja w busach
# saga.timeout_worker -> dopisz do run_delivery_workers(...) jako extra processor
```

To wszystko. Nie rejestrujesz ręcznie `SqlSagaRepository`, workerów ani dispatcherów
— robi to `install_saga`. Drugi serwis powtarza Kroki 2-5 identycznie (jego `base.py`,
jego `saga_wiring.py`, jego jedno wywołanie).

Weryfikacja:

```powershell
Select-String -Path "shell/*/bootstrap/*/container/*.py" -Pattern "SqlSagaRepository|SqlSagaTimeoutRepository|SagaTimeoutProcessor|build_command_delivery_dispatcher"
# oczekiwane: 0 trafień (wszystko za install_saga)
```

## 6. Konkretna saga zostaje w serwisie (deklaracja, nie framework)

```python
# shell/project_service/process/project/project_provision/saga_definition.py
from __future__ import annotations

from datetime import timedelta

from saga_orchestration.domain.step import StepDefinition, StepRegistry
from saga_orchestration.domain.step_name import StepName

PROJECT_PROVISION_STEPS = StepRegistry(
    steps=(
        StepDefinition(
            name=StepName("provision_workspace"),
            target_service="project",
            compensation_step=StepName("release_workspace"),
            timeout=timedelta(minutes=5),
            max_attempts=2,
            backoff=timedelta(seconds=30),
        ),
    )
)
SAGA_TYPE = "project_provision"
```

Start sagi to JEDEN handler z KROKU 4 `SAGA.MD` (create sagi + dispatch kroku 1
w JEDNEJ transakcji). Wyniki kroków wchodzą przez `advance_handler`
(idempotentnie po `event_id` — drugi dowóz to no-op).

## 7. Uczestnik kroku: zwykły agregat (nigdy stub na EventBus)

Efekt kroku + fakt rezultatu zapisujesz w agregacie serwisu przez jego własny UoW:

```python
class ProvisionWorkspaceHandler(CommandHandler[ProvisionWorkspaceCommand]):
    async def handle(self, command: ProvisionWorkspaceCommand) -> None:
        async with self._unit_of_work as uow:
            ws = await uow.repository(WorkspaceRepository).get_by_project(command.project_id)
            if ws is not None and ws.is_provisioned():
                return  # idempotencja uczestnika
            await uow.save(WorkspaceRepository, Workspace.provision(...))
        # fakt WorkspaceProvisioned/Failed wychodzi przez event_outbox serwisu:
        # relay -> RabbitMQ -> inbox sagi. Zero EventBusPublisher.
```

Weryfikacja:

```powershell
Select-String -Path "shell/<bc>_service/**/*.py" -Pattern "EventBusPublisher|event_bus\.publish"
# oczekiwane w ścieżce sagi: 0 trafień
```

## 8. Korelacja (obowiązkowa, bez defaultów)

- Saga korelowana parą `saga_type + saga_key` (`get_by_key`), gdzie `saga_key`
  to klucz BIZNESOWY (np. `project_id`).
- `saga_id` to wewnętrzne id instancji i rekordów timeoutów — nie doklejane
  do bazowych `Command` / `IntegrationEvent` ani kopert.
- Komendy kroków i eventy wyników NIE niosą `saga_id` — handlery odnajdują sagę
  po kluczach biznesowych.
- `correlation_id` wymagane, `causation_id` wymagane-lub-None. Bez `default=""`.

## 9. Minimalny przykład end-to-end (project)

1. `pip install -e packaging/saga-orchestration`
2. W `shell/project_service/.../models/base.py`: `SAGA_MODELS = build_saga_models(ProjectSqlAlchemyModelBase)`
3. `alembic upgrade head` → `saga_instance`, `saga_timeout` w bazie projektu
4. Nowy `shell/project_service/infrastructure/project/saga/saga_wiring.py` (Krok 4)
5. W containerze: jedno `install_saga(...)` + rejestracja 3 handlerów + worker
6. Nowa `saga_definition.py` (Krok 6) + uczestnik-agregat (Krok 7)
7. Testy: `pytest packaging/saga-orchestration/tests -q`
   (atomiczność, idempotencja, retry→kompensata) oraz restart-test serwisu
   (kill po COMMIT przed relay → po restarcie `COMPLETED`/`COMPENSATED`)

## 10. Serwis bez sagi: checklista „niczego”

- brak wiersza `build_saga_models(...)` w `base.py` → brak tabel na świeżej bazie,
- brak `saga_wiring.py`, brak `install_saga(...)` w containerze,
- brak importów `saga_orchestration` w całym serwisie,
- brak handlerów/workerów sagowych w busach.

```powershell
Select-String -Path "shell/<bc>_service/**/*.py" -Pattern "saga_orchestration|install_saga|SAGA_MODELS"
# oczekiwane dla serwisu BEZ sagi: 0 trafień
```
