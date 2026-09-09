"""Ładowacz konfiguracji z jawnymi granicami deploymentu, runtime'u i usług."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from shell.platform.infrastructure.configuration.config_slices import (
        AuthConfig,
        DeploymentConfig,
        PlatformRuntimeConfig,
        ServiceConfig,
    )

_VALID_PROFILES = frozenset({"dev", "prod"})
_VALID_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})


def _config_dir() -> Path:
    """Rozpoznaj współdzielony katalog konfiguracyjny środowiska."""
    configured_dir = os.environ.get("SHELL_CONFIG_DIR")
    if configured_dir:
        return Path(configured_dir)
    return Path(__file__).resolve().parents[3] / "config"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Rekurencyjnie scalaj override z base."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_yaml(path: Path) -> dict[str, Any]:
    """Wczytaj plik YAML, zwracając pusty dict jeśli brakuje."""
    if not path.exists():
        return {}
    display_name = path.name
    with open(path, encoding="utf-8") as fh:
        result: Any = yaml.safe_load(fh)
        if result is None:
            raise ValueError(f"Pusty lub niepoprawny plik YAML: {display_name}")
        if not isinstance(result, dict):
            raise ValueError(f"Plik YAML {display_name} nie zawiera mapowania")
        return result


def _int_setting(values: dict[str, Any], name: str, default: int) -> int:
    raw = values.get(name, default)
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Nieprawidłowa konfiguracja całkowita: {name}") from exc
    return value


def _float_setting(values: dict[str, Any], name: str, default: float) -> float:
    raw = values.get(name, default)
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Nieprawidłowa konfiguracja numeryczna: {name}") from exc
    return value


def _require_range(name: str, value: int | float, *, minimum: int | float) -> int | float:
    if value < minimum:
        raise ValueError(f"Nieprawidłowa konfiguracja: {name} musi być >= {minimum}")
    return value


@dataclass
class EventsConfig:
    outbox_batch_size: int = 100
    inbox_batch_size: int = 50
    worker_poll_interval: float = 1.0
    worker_backoff_factor: float = 2.0
    worker_max_backoff: float = 30.0
    worker_heartbeat_interval_seconds: float = 15.0
    worker_max_batch_time_seconds: float = 45.0
    broker_url: str = ""


@dataclass(frozen=True, slots=True)
class LoadedConfiguration:
    """Zwalidowana konfiguracja z jawnymi granicami własności."""

    deployment: DeploymentConfig
    platform_runtime: PlatformRuntimeConfig
    auth: AuthConfig
    service: ServiceConfig
    test_db_dir: str | None = None

    @classmethod
    def from_environment(
        cls,
        component_config_dir: Path | None = None,
        *,
        service_name: str | None = None,
    ) -> LoadedConfiguration:
        """Zbuduj konfigurację z plików YAML i zmiennych środowiskowych.

        Kolejność ładowania (ostatni wygrywa):
        1. config/default.yaml — ustawienia wspólne + active_profile
        2. config/{active_profile}.yaml  — nadpisania specyficzne dla profilu
        3. Zmienne środowiskowe (SHELL_DATABASE_URL, SHELL_MAX_STEP, SHELL_RESET_DB)

        Bezpieczeństwo: reset_db honorowane tylko gdy active_profile == 'dev'.
        Gdy podano service_name, produkcja wymaga zmiennych środowiskowych
        tej usługi: database, broker, api_key.
        """
        config_dir = (
            component_config_dir
            if component_config_dir is not None and (component_config_dir / "default.yaml").exists()
            else _config_dir()
        )

        # 1. Załaduj domyślne
        defaults = _load_yaml(config_dir / "default.yaml")

        # 2. Określ aktywny profil ze środowiska lub domyślnych.
        active_profile = os.environ.get("SHELL_PROFILE", defaults.get("active_profile", "prod"))
        if active_profile not in _VALID_PROFILES:
            raise ValueError(f"Nieprawidłowa konfiguracja: profil musi być jednym z {_VALID_PROFILES}")

        # 3. Załaduj config specyficzny dla profilu
        profile_file = config_dir / f"{active_profile}.yaml"
        profile_data = _load_yaml(profile_file)

        # 4. Scal ustawienia wspólne z komponentem profilu, gdy podano.
        merged = _deep_merge(defaults, profile_data)
        if component_config_dir is not None:
            component_file = component_config_dir / "database_dev.yaml"
            merged = _deep_merge(merged, _load_yaml(component_file))
        merged["profile"] = active_profile

        # 5. Nadpisania ze zmiennych środowiskowych używają jednej precedencji dla obu profili.
        service_prefix = None if service_name is None else f"{service_name.upper()}_SERVICE"
        database_env = "SHELL_DATABASE_URL"
        legacy_database_env = (
            f"{service_prefix}_DATABASE_URL" if service_prefix is not None else None
        )
        selected_database_env = next(
            (
                variable
                for variable in (legacy_database_env, database_env)
                if variable is not None and variable in os.environ
            ),
            None,
        )
        if selected_database_env is not None:
            env_db_url = os.environ[selected_database_env]
            if not env_db_url:
                raise ValueError(
                    f"Nieprawidłowa konfiguracja: {selected_database_env} nie może być puste"
                )
            merged["database_url"] = env_db_url
        elif service_name is not None and active_profile == "prod":
            required_database_env = legacy_database_env or database_env
            raise ValueError(
                f"Nieprawidłowa konfiguracja produkcyjna: {required_database_env} jest wymagana"
            )

        env_max_step = os.environ.get("SHELL_MAX_STEP")
        if env_max_step is not None:
            merged["max_step"] = env_max_step

        env_max_parallel = os.environ.get("SHELL_MAX_PARALLEL")
        if env_max_parallel is not None:
            merged["max_parallel"] = env_max_parallel

        # reset_db: honorowany tylko w profilu dev
        env_reset = os.environ.get("SHELL_RESET_DB", "").lower()
        reset_db = env_reset in ("1", "true", "yes")
        if reset_db and active_profile != "dev":
            raise ValueError("Nieprawidłowa konfiguracja: reset_db dozwolone tylko w profilu dev")

        env_log_level = os.environ.get("SHELL_LOG_LEVEL")
        if env_log_level:
            merged["log_level"] = env_log_level

        if "SHELL_API_KEY" in os.environ:
            if (
                service_name is not None
                and active_profile == "prod"
                and not os.environ["SHELL_API_KEY"]
            ):
                raise ValueError(
                    "Nieprawidłowa konfiguracja produkcyjna: SHELL_API_KEY nie może być puste"
                )
            merged["api_key"] = os.environ["SHELL_API_KEY"]
        elif service_name is not None and active_profile == "prod":
            raise ValueError("Nieprawidłowa konfiguracja produkcyjna: SHELL_API_KEY jest wymagane")

        env_broker_url = os.environ.get("SHELL_EVENTS_BROKER_URL")
        if env_broker_url:
            merged.setdefault("events", {})["broker_url"] = env_broker_url
        elif service_name is not None and active_profile == "prod":
            raise ValueError("Nieprawidłowa konfiguracja produkcyjna: SHELL_EVENTS_BROKER_URL jest wymagane")

        env_test_db_dir = os.environ.get("SHELL_TEST_DB_DIR")
        if env_test_db_dir:
            merged["test_db_dir"] = env_test_db_dir

        max_step = int(_require_range("max_step", _int_setting(merged, "max_step", 20), minimum=0))
        max_parallel = int(
            _require_range("max_parallel", _int_setting(merged, "max_parallel", 4), minimum=1)
        )
        log_level = str(merged.get("log_level", "INFO")).upper()
        if log_level not in _VALID_LOG_LEVELS:
            raise ValueError(f"Nieprawidłowa konfiguracja: log_level={log_level}")
        seed_dev_data = bool(merged.get("seed_dev_data", False))
        if seed_dev_data and active_profile != "dev":
            raise ValueError("Nieprawidłowa konfiguracja: seed_dev_data dozwolone tylko w profilu dev")
        events = merged.get("events", {})
        if not isinstance(events, dict):
            raise ValueError("Nieprawidłowa konfiguracja: events musi być mapowaniem")

        outbox_batch_size = int(
            _require_range(
                "events.outbox_batch_size",
                _int_setting(events, "outbox_batch_size", 100),
                minimum=1,
            )
        )
        inbox_batch_size = int(
            _require_range(
                "events.inbox_batch_size", _int_setting(events, "inbox_batch_size", 50), minimum=1
            )
        )
        worker_poll_interval = float(
            _require_range(
                "events.worker_poll_interval",
                _float_setting(events, "worker_poll_interval", 1.0),
                minimum=0.0,
            )
        )
        worker_backoff_factor = float(
            _require_range(
                "events.worker_backoff_factor",
                _float_setting(events, "worker_backoff_factor", 2.0),
                minimum=0.0,
            )
        )
        worker_max_backoff = float(
            _require_range(
                "events.worker_max_backoff",
                _float_setting(events, "worker_max_backoff", 30.0),
                minimum=0.0,
            )
        )
        worker_heartbeat_interval_seconds = float(
            _require_range(
                "events.worker_heartbeat_interval_seconds",
                _float_setting(events, "worker_heartbeat_interval_seconds", 15.0),
                minimum=0.0,
            )
        )
        worker_max_batch_time_seconds = float(
            _require_range(
                "events.worker_max_batch_time_seconds",
                _float_setting(events, "worker_max_batch_time_seconds", 45.0),
                minimum=0.0,
            )
        )

        from shell.platform.infrastructure.configuration.config_slices import (
            AuthConfig,
            DeploymentConfig,
            PlatformRuntimeConfig,
            ServiceConfig,
        )

        return cls(
            deployment=DeploymentConfig(
                profile=merged.get("profile", "prod"),
                database_url=merged.get("database_url", ""),
            ),
            platform_runtime=PlatformRuntimeConfig(
                log_level=log_level,
                events=EventsConfig(
                    outbox_batch_size=outbox_batch_size,
                    inbox_batch_size=inbox_batch_size,
                    worker_poll_interval=worker_poll_interval,
                    worker_backoff_factor=worker_backoff_factor,
                    worker_max_backoff=worker_max_backoff,
                    worker_heartbeat_interval_seconds=worker_heartbeat_interval_seconds,
                    worker_max_batch_time_seconds=worker_max_batch_time_seconds,
                    broker_url=events.get("broker_url", ""),
                ),
            ),
            auth=AuthConfig(api_key=str(merged.get("api_key", ""))),
            service=ServiceConfig(
                max_step=max_step,
                max_parallel=max_parallel,
                seed_dev_data=seed_dev_data,
                reset_db=reset_db,
            ),
            test_db_dir=merged.get("test_db_dir"),
        )