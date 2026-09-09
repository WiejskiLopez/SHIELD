# Relay outbox (EventOutboxRelay i CommandOutboxRelay)

## Cel / Co realizuje

Relay'e są mostem producenta między transactional outbox a brokerem: czytają niepublikowane
wiersze outboxa, budują kopertę i publikują ją przez transport. `EventOutboxRelay`
(`messaging/event/event_outbox_relay.py`) obsługuje `event_outbox`, `CommandOutboxRelay`
(`messaging/command/command_outbox_relay.py`) obsługuje `command_outbox`. Wspólny cykl
publikacji żyje w bazie `OutboxRelayBase` (`messaging/delivery/outbox_relay_base.py`).

## Problem

Transactional outbox gwarantuje atomowość zapisu domeny i rekordu outbox, ale nie przenosi
danych na broker ani do docelowego BC. Relay publikuje oczekujące wiersze, a brokerowy
consumer zapisuje je do lokalnego inboxa. Idempotencja opiera się na `source_service`
i logicznym ID (`event_id`/`command_id`); lokalny inbox posiada własne `id`.

## Realizacja techniczna

### OutboxRelayBase (wspólny cykl publikacji)

Konstruktor przyjmuje `session_factory`, transport, `batch_size: int = 100` oraz
parametry odpornościowe z defaultami jak procesor inboxa (`max_retries = 3`,
`retry_backoff_seconds = 30`, `max_retry_backoff_seconds = 3600`,
`retry_jitter_seconds = 0.0`, `lease_duration_seconds = 60`,
`consecutive_failure_limit = 20`, `worker_id` z autogeneracją).
Wykrywanie dialektu — `self._skip_locked = dialect_name not in ("sqlite",)` (na bazach
niebędących SQLite włączany jest `FOR UPDATE SKIP LOCKED`).

Podklasy dostarczają: `outbox_model`, `order_column` (event: `occurred_at`; command:
`issued_at`) oraz `_to_envelope(row)`.

Cykl życia wiersza (lustro inboxa): `PENDING → PROCESSING → SENT / RETRY / DEAD_LETTER`
(kolumny w `OutboxStateMixin`, statusy w `OutboxStatus`). `published_at` pozostaje
znacznikiem wysyłki i jest ustawiane wyłącznie po udanej publikacji — crash między
deliver a mark skutkuje re-deliverem (at-least-once; inbox konsumenta jest idempotentny).

`run_once() -> OutboxBatchResult`:

1. claim: `select(outbox_model).where(published_at IS NULL AND status IN (PENDING, RETRY)
   AND next_attempt_at <= now(DB) OR (PROCESSING po lease))`, `order_by(order_column)`,
   `limit(batch_size)`, a gdy `_skip_locked` → `.with_for_update(skip_locked=True)`;
   claimowane wiersze dostają `PROCESSING` + `claimed_by` + `lease_until`;
2. dla każdego wiersza osobno: `_to_envelope(row)` (błąd mapowania = deterministyczny,
   wiersz od razu do `DEAD_LETTER` z `ENVELOPE_BUILD_ERROR`), potem
   `await self._transport.deliver(envelope)` — każdy wynik zapisywany jest własną
   krótką transakcją, więc poison row nigdy nie blokuje reszty batcha;
3. błąd transportu rzędu wiersza (nack, `NO_ROUTE`, timeout) → `RETRY` z backoff
   `min(cap, base * 2**(n-1)) + jitter`, po `max_retries` → `DEAD_LETTER` + `logger.critical`;
4. błąd połączenia (`ConnectionError`: broker nieosiągalny) przerywa rundę —
   nietknięte wiersze wracają do `PENDING`, a błąd jest propagowany, żeby polling
   worker wycofał się wykładniczo zamiast nabijać `retry_count` zdrowym wierszom;
5. breaker kolejnych porażek (`consecutive_failure_limit`) robi to samo dla
   nieklasyfikowalnych kaskad;
6. wynik strukturalny `OutboxBatchResult(claimed/processed/retried/dead_lettered/failed/
   duration_ms)` — te same nazwy pól co `InboxBatchResult`, więc `PollingWorker`
   loguje go bez zmian.

Wszystkie znaczniki czasu pochodzą z zegara bazy (`CURRENT_TIMESTAMP`), a komunikaty
błędów są przycinane i pozbawiane sekretów w URL-ach (`_sanitize_error_message`).

Operacyjnie: zaległości widać w `OutboxMetricsService.snapshot()` (bez `DEAD_LETTER`;
osobny gauge), `OutboxReplayService` cofa `DEAD_LETTER`/`SENT` do `PENDING`, a retention
(`DeliveryRetentionService`) czyści stare `DEAD_LETTER` z outboxów tak samo jak z inboxów.

## Kluczowe pliki

- `shell/platform/infrastructure/messaging/delivery/outbox_relay_base.py` (OutboxRelayBase)
- `shell/platform/infrastructure/messaging/event/event_outbox_relay.py` (EventOutboxRelay)
- `shell/platform/infrastructure/messaging/command/command_outbox_relay.py` (CommandOutboxRelay)
- `shell/platform/application/ports/transport/{event,command}_transport.py` (koperty + porty)

## Powiązane koncepcje

- [transactional-outbox](transactional-outbox.md)
- [delivery-transport](delivery-transport.md)
- [inbox-lifecycle](inbox-lifecycle.md)
- [delivery-overview](delivery-overview.md)
- [delivery-models](delivery-models.md)
- [unit-of-work](unit-of-work.md)