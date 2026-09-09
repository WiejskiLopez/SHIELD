# Integration Mapper

## Cel / Co realizuje

`IntegrationEventMapper` w `shell/platform/infrastructure/mapping/integration_event_mapper.py` konwertuje DomainEvent na zarejestrowany IntegrationEvent bez per-aggregatowych mapperów. Rejestr jest przekazywany jawnie przez composition root, a mapper używa refleksji wyłącznie do odczytu pól dataclass; błędy zgłasza jako `IntegrationMappingError`.

## Problem

Eventy domenowe emitowane przez agregaty (np. `UserCreatedEvent`) muszą być publikowane między bounded contextami jako IntegrationEventy (`UserCreatedIntegrationEvent`) z kompletem pól koperty (event_id, correlation_id, causation_id, occurred_at, aggregate_id, schema_version). Ręczne mapowanie każdej pary klas w każdym BC prowadzi do powielania kodu i rozjazdu kontraktów. Rozwiązanie: jeden mapper oparty na jawnym rejestrze per BC — jeśli IntegrationEvent nie jest zarejestrowany, jest to błąd konfiguracji.

## Realizacja techniczna

### Jawny rejestr

Composition root przekazuje mapowanie nazwy klasy eventu domenowego na klasę
eventu integracyjnego. Mapper nie zna nazw modułów, bounded contextów ani
konwencji lokalizacji kontraktów.

`map(domain_event)` wyznacza klasę IntegrationEvent z tego rejestru.

<!-- Dawny opis wyszukiwania klas po topologii modułów został usunięty. -->

<!--

1. **Nazwa klasy**: `event_cls.__name__.replace("Event", "IntegrationEvent")` — `UserCreatedEvent` → `UserCreatedIntegrationEvent`.
2. **Moduł**: na podstawie `event_cls.__module__` wyznaczana jest **jedna** obsługiwana topologia — per-BC w ekstrakcji `_service`:

- `parts = module.split(".")`; wymagane `len(parts) > 5`, `parts[0] == "shell"`, `parts[1].endswith("_service")`, `parts[2] == "domain"`;
- `shell.<bc>_service.domain.<bc>.aggregates.<agg>.events.<file>` → `shell.<bc>_service.application.<bc>.<agg>.integration_events.<file>`;
- inna topologia → `IntegrationMappingError("Unsupported domain event module topology: ...")`.

Nazwa pliku powstaje z nazwy klasy przez `re.sub(r"(?<!^)(?=[A-Z])", "_", int_name).lower()` (PascalCase → snake_case). Moduł jest importowany przez `importlib.import_module`, a klasa pobierana przez `getattr(mod, int_name)`. Brak modułu (`ModuleNotFoundError`) lub brak klasy w module → `IntegrationMappingError` z komunikatem naprawy.
-->

### Budowa kwargs i mapowanie pól

`map(domain_event)`:

1. Uzupełnia pola koperty: `event_id=str(domain_event.event_id.value)`, `correlation_id=get_or_create_correlation_id()`, `causation_id=get_causation_id()` (z kontekstu — patrz [tracing-context](tracing-context.md)), `occurred_at`, `aggregate_id=str(...)`, `schema_version=1` (stała — wersja jest nadawana na granicy kontraktu).
2. `ENVELOPE_FIELDS` — frozenset nazw pól `IntegrationEvent` (`dataclasses.fields(IntegrationEvent)`) — służy do pominięcia pól koperty przy mapowaniu pól biznesowych.
3. Dla każdego pozostałego pola klasy IntegrationEvent pobiera atrybut o tej samej nazwie z eventu domenowego i konwertuje przez `_to_str(raw)` (`str(raw.value)` albo `None`).
4. Zwraca `int_cls(**kwargs)`.

Dzięki temu **nazwy pól biznesowych** muszą się zgadzać między DomainEvent a IntegrationEvent, a wartości są łańcuchowane (`str`), z zachowaniem `None`.

### `IntegrationMappingError`

`shell/platform/infrastructure/mapping/integration_mapping_error.py` definiuje `IntegrationMappingError(ValueError)` — zgłaszany przy braku zdarzenia w jawnym rejestrze albo nieprawidłowej strukturze eventu domenowego.

## Kluczowe pliki

- `shell/platform/infrastructure/mapping/integration_event_mapper.py`
- `shell/platform/infrastructure/mapping/integration_mapping_error.py`

## Powiązane koncepcje

- [integration-contracts](integration-contracts.md)
- [domain-event](domain-event.md)
- [tracing-context](tracing-context.md)
- [transactional-outbox](transactional-outbox.md)
- [relay](relay.md)