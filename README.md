# SHELL

SHELL to platforma uruchamiania i orkiestracji zadań oparta na Pythonie. Projekt jest podzielony na bounded contexty i korzysta z DDD, Clean Architecture, Hexagonal Architecture oraz CQRS.

## Co zawiera projekt

Repozytorium zawiera:

- siedem usług backendowych wystawiających API FastAPI;
- wspólną platformę techniczną w `shell/platform`;
- warstwy domeny, aplikacji, procesów, infrastruktury, frameworka i bootstrapu;
- komunikację asynchroniczną przez RabbitMQ oraz mechanizmy inbox/outbox;
- persystencję SQL przez SQLAlchemy 2 i migracje Alembic;
- adaptery SQLite i PostgreSQL;
- repozytoria SQL oraz in-memory używane w testach;
- sagę/process managery dla procesów wieloagregatowych;
- konfigurację mTLS i generator certyfikatów;
- testy jednostkowe, integracyjne, systemowe, kontraktowe i architektury;
- skrypty PowerShell do uruchamiania usług, testów i walidacji release.

### Bounded contexty

| Usługa | Odpowiedzialność | Domyślny port API |
|---|---|---:|
| `user_service` | użytkownicy, umiejętności i sesje autoryzacyjne | 8001 |
| `definition_service` | definicje grafów, node'ów i konfiguracji runnera | 8002 |
| `session_service` | sesje wykonania | 8003 |
| `ingestion_service` | przyjmowanie danych wejściowych | 8004 |
| `project_service` | projekty i ich konfiguracja | 8005 |
| `scheduling_service` | definicje zadań, harmonogramy i wykonania | 8006 |
| `execution_service` | workflow, grafy, node'y i wykonania | 8007 |
| `platform` | wspólne busy, persistence, messaging, auth, logging i observability | - |

Każdy bounded context ma własną bazę danych, migracje, kontener DI i bootstrap. Wspólne mechanizmy techniczne znajdują się w `shell/platform`, a nie w kopiach poszczególnych usług.

## Wymagania

- Windows z PowerShell 7 lub Windows PowerShell;
- Python `>=3.14,<3.15`;
- Docker Desktop z Docker Compose;
- Git;
- RabbitMQ, uruchamiany przez compose;
- SQLite dla lokalnego uruchomienia;
- PostgreSQL tylko wtedy, gdy uruchamiane są testy PostgreSQL lub środowisko produkcyjne.

Do pracy z Dockerem Docker Desktop musi być uruchomiony. Certyfikaty mTLS są potrzebne tylko dla konfiguracji TLS/mTLS.

## Biblioteki

### Runtime

Najważniejsze zależności z głównego `pyproject.toml`:

- `FastAPI` i `Uvicorn` - HTTP API i serwery usług;
- `SQLAlchemy` - modele ORM i dostęp asynchroniczny do SQL;
- `aiosqlite` i `asyncpg` - sterowniki SQLite/PostgreSQL;
- `Alembic` - migracje baz danych;
- `aio-pika` - komunikacja z RabbitMQ;
- `APScheduler` - harmonogramowanie zadań;
- `Pydantic` i `pydantic-settings` - modele danych i konfiguracja;
- `dependency-injector` - kontenery zależności;
- `httpx` - wywołania HTTP między usługami i testy;
- `PyJWT` - tokeny JWT;
- `PyYAML` - konfiguracja zadań;
- `motor` - adapter MongoDB.

### Development i jakość

- `pytest`, `pytest-asyncio`, `pytest-cov` - testy i coverage;
- `ruff` - lint i formatowanie;
- `mypy` - statyczne typowanie;
- `import-linter` - kontrola granic architektury;
- `bandit` - skan bezpieczeństwa kodu;
- `pip-audit` - audyt podatności zależności;
- `cryptography` - certyfikaty i TLS/mTLS.

Pełne wersje zależności są zdefiniowane w `pyproject.toml` oraz w plikach `packaging/*/pyproject.toml`.

## Instalacja lokalna

Z katalogu głównego repozytorium:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Środowisko używane przez repozytorium powinno mieć również narzędzia jakości uruchamiane przez `run_tests.ps1`:

```powershell
python -m pip install aiosqlite uvicorn pydantic-settings pytest-asyncio pytest-cov ruff mypy import-linter bandit pip-audit
```

Jeżeli PowerShell blokuje aktywację środowiska:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

## Konfiguracja

Dla lokalnego uruchomienia większość usług korzysta z SQLite i wartości zdefiniowanych w compose. Dla środowiska produkcyjnego:

```powershell
Copy-Item .env.prod.example .env.prod
```

Następnie ustaw realne wartości, przede wszystkim:

- `<SERVICE>_SERVICE_DATABASE_URL` (np. `DEFINITION_SERVICE_DATABASE_URL`) dla
	produkcyjnej bazy konkretnej usługi;
- `SHELL_DATABASE_URL` jako wspólny fallback i wartość używaną lokalnie, gdy
	nie potrzebujesz osobnych URL-i baz danych;
- `SHELL_API_KEY`;
- `SHELL_EVENTS_BROKER_URL`;
- `SHELL_LOG_LEVEL`;
- opcjonalne `*_SERVICE_TLS_*` dla TLS serwera;
- opcjonalne `*_SERVICE_MTLS_*` dla certyfikatu klienta.

Nie commituj `.env.prod` ani prawdziwych kluczy API, haseł i kluczy prywatnych. Plik `.env.prod.example` zawiera tylko wartości przykładowe.

### Zmienne lokalnego uruchomienia

Przed pierwszym uruchomieniem lokalnego backendu ustaw w PowerShell zmienne wymagane przez Docker Compose. Wartości poniżej są przykładowe i służą wyłącznie do pracy lokalnej:

```powershell
$env:RABBITMQ_DEFAULT_USER = "shell"
$env:RABBITMQ_DEFAULT_PASS = "shell"

$env:SHELL_API_KEY = "shell-dev-example-api-key"

$env:SHELL_EVENTS_BROKER_URL = "amqp://shell:shell@rabbitmq:5672/"
```

Następnie uruchom cały backend:

```powershell
.\shell\backend.ps1 up
```

Compose ustawia lokalnie automatycznie: `SHELL_ALLOWED_ORIGINS=http://localhost:8080`, `SHELL_COOKIE_SECURE=0` oraz bazy SQLite w katalogach `shell/*/docker/dev_db`. Dla komunikacji między kontenerami broker musi używać hosta `rabbitmq`; `localhost` wskazywałby na bieżący kontener.

Opcjonalne zmienne lokalne:

```powershell
$env:DEFINITION_SERVICE_URL = "https://shell-definition-api:8002"
$env:SESSION_SERVICE_URL = "https://shell-session-api:8003"
$env:SERVICE_HTTP_TIMEOUT = "5"

# Nadpisanie baz SQLite, jeśli jest potrzebne:
$env:SHELL_DATABASE_URL = "sqlite+aiosqlite:///shell_dev/dev_shell.db"
```

Zmienne środowiskowe ustawione w PowerShell obowiązują tylko w bieżącej sesji. Po otwarciu nowego terminala trzeba ustawić je ponownie albo zapisać w lokalnym pliku `.env` używanym przez Docker Compose. Nie commituj takiego pliku, jeśli zawiera prawdziwe sekrety.

## Uruchamianie przez Docker Compose

Najprościej uruchomić cały lokalny backend z katalogu głównego:

```powershell
.\shell\backend.ps1 up
```

Dostępne akcje agregatora:

```powershell
.\shell\backend.ps1 status
.\shell\backend.ps1 logs
.\shell\backend.ps1 restart
.\shell\backend.ps1 down
.\shell\backend.ps1 redeploy execution
.\shell\backend.ps1 test
```

Można uruchomić tylko jedną jednostkę:

```powershell
.\shell\backend.ps1 up user
.\shell\backend.ps1 logs scheduling
.\shell\backend.ps1 status rabbit
```

Dostępne jednostki to: `user`, `definition`, `session`, `ingestion`, `project`, `scheduling`, `execution` i `rabbit`.

Dla środowiska produkcyjnego użyj przygotowanego `.env.prod`:

```powershell
.\shell\backend.ps1 up -Environment prod
```

Każdy serwis ma również własny plik `shell/<service>/docker/docker-compose.yml` i skrypt `shell/<service>/docker/scripts/manage.ps1`.

## Uruchamianie pojedynczej usługi bez Dockera

Każda usługa ma własny moduł bootstrapu. Przykłady:

```powershell
python -m shell.user_service.bootstrap.user.main --host 127.0.0.1 --port 8001
python -m shell.definition_service.bootstrap.definition.main --host 127.0.0.1 --port 8002
python -m shell.session_service.bootstrap.session.main --host 127.0.0.1 --port 8003
python -m shell.ingestion_service.bootstrap.ingestion.main --host 127.0.0.1 --port 8004
python -m shell.project_service.bootstrap.project.main --host 127.0.0.1 --port 8005
python -m shell.scheduling_service.bootstrap.scheduling.main --host 127.0.0.1 --port 8006
python -m shell.execution_service.bootstrap.execution.main --host 127.0.0.1 --port 8007
```

Do uruchomienia workera dodaj `--worker`, na przykład:

```powershell
python -m shell.execution_service.bootstrap.execution.main --worker
```

Uruchomienie bez Dockera wymaga samodzielnego zapewnienia RabbitMQ, konfiguracji zmiennych środowiskowych oraz dostępnej bazy danych.

## API i dokumentacja

Po uruchomieniu usługi FastAPI dokumentacja OpenAPI jest dostępna pod:

```text
http://localhost:<port>/docs
http://localhost:<port>/redoc
```

Endpoint gotowości jest dostępny pod `/readiness`, a endpoint zdrowia pod `/health` w usługach, które go wystawiają.

## Testy i walidacja

Pełny lokalny pipeline uruchamia:

```powershell
.\run_tests.ps1
```

Przydatne opcje:

```powershell
.\run_tests.ps1 -UnitOnly
.\run_tests.ps1 -IntegrationOnly
.\run_tests.ps1 -SkipLint
.\run_tests.ps1 -SkipTypeCheck
.\run_tests.ps1 -SkipSecurity
.\run_tests.ps1 -SkipArchCheck
```

`POSTGRES_TEST_URL` włącza testy integracyjne wymagające PostgreSQL:

```powershell
$env:POSTGRES_TEST_URL = "postgresql+asyncpg://user:password@localhost:5432/shell_test"
.\run_tests.ps1
```

Pojedyncze komendy:

```powershell
# Wszystkie testy
python -m pytest shell/tests -q

# Testy architektury
python -m pytest shell/tests/architecture -q

# Testy konkretnej usługi
python -m pytest shell/tests/scheduling_service -q

# Testy platformy
python -m pytest shell/tests/platform -q

# Coverage
python -m pytest shell/tests/platform/unit shell/tests/*_service --cov=shell --cov-fail-under=80

# Lint
python -m ruff check shell shell/tests
python -m ruff format --check shell shell/tests

# Typowanie
python -m mypy --no-incremental shell

# Granice importów
.\.venv\Scripts\import-linter.exe lint

# Kontrola diffu
 git diff --check
```

## Migracje baz danych

Migracje są przechowywane w `shell/<service>/migrations/versions`. Każdy bounded context ma własny łańcuch Alembic. Heady można zweryfikować skryptem release:

```powershell
python -c "from scripts.verify_service_release import _migration_head; print(_migration_head('project_service'))"
```

Migracje usług `project_service` i `scheduling_service` zawierają adopcję wspólnego schematu sagi z biblioteki `saga-orchestration`.

## Struktura katalogów

```text
shell/
├── platform/              # wspólne mechanizmy techniczne
├── *_service/
│   ├── domain/            # agregaty, encje, VO i zdarzenia
│   ├── application/       # command/query handlery, DTO i porty
│   ├── process/           # sagi i orkiestracja wieloagregatowa
│   ├── infrastructure/    # SQL, messaging i adaptery
│   ├── framework/         # FastAPI i wejścia CLI
│   ├── bootstrap/         # composition root usługi
│   └── migrations/        # migracje Alembic
├── tests/                 # testy jednostkowe, integracyjne i architektury
├── certs/                 # lokalne certyfikaty, nie commituj kluczy prywatnych
└── backend.ps1            # agregator zarządzania usługami
```

Kierunek zależności jest kontrolowany przez testy architektury:

```text
domain <- application <- process <- infrastructure <- framework <- bootstrap
```

## Ważne skrypty

| Plik | Przeznaczenie |
|---|---|
| `shell/backend.ps1` | zbiorcze uruchamianie i zatrzymywanie usług |
| `run_tests.ps1` | pełny pipeline testów, lintowania, typowania i audytów |
| `scripts/generate-openapi.py` | generowanie `openapi.json` |
| `scripts/generate_mtls_certs.py` | generowanie certyfikatów mTLS |
| `scripts/verify_service_release.py` | weryfikacja artefaktów i headów migracji |
| `deploy.ps1` | szeroki pipeline wdrożeniowy; może formatować, budować obrazy i commitować |

`deploy.ps1` nie jest wymagany do zwykłego uruchomienia lokalnego. Przed jego użyciem sprawdź jego działanie i skutki dla repozytorium.
