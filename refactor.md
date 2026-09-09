# Refactor / audyt projektu SHELL

Data audytu: 2026-09-08. Data ostatniej weryfikacji: 2026-09-09.
Zakres: `shell/platform`, `shell/*_service`, `shell/tests`, `pyproject.toml`, `pytest.ini`, `run_tests.ps1`, `deploy.ps1`, `.github/`, `docs/`, `scripts/`, `gui/`.

Lista jest posortowana od najistotniejszego do najmniej istotnego. P0 = bezpieczeństwo / utrata danych / zepsuty deploy, P3 = higiena / DX.

---

## P1 — wysokie (poprawność logiki, wyścigi, ciche błędy)

---

## P2 — średnie (architektura, niespójności między BC)

### 1. Asymetria CQRS — martwe agregaty
- Pozostają niepodłączone `project_state`, `definition.graph_definition_embedding`, `definition.node_link_definition` oraz część execution state models. Usunięcie ich persistence i migracji nadal wymaga decyzji domenowej; aktualny inventory CQRS i podstawowe read-side'y są objęte testami architektury.

### 2. Cztery topologie `domain`, dwa wzorce eventów obcych
- Pozostaje analiza ewentualnych dalszych wspólnych portów i mostków integracyjnych; nie znaleziono obecnie mostka, który można bezpiecznie przenieść do `process/` bez zmiany kontraktu.

### 3. Sagi tylko w 2/7 BC, single-step
- Tylko `project/scheduling` mają `process/`; `saga_definition` ma jeden krok `provision -> release` z tymi samymi timeoutami; istnieją dwa domy (`process/` i `infrastructure/*/saga/`); tylko `execution` ma `upcaster.py` (v1→v2), reszta `{1}`.
- Deklaracje obu sag mają test kontraktu wymagający kroku, kompensacji, dodatniego timeoutu i retry.
- Pozostaje decyzja: jeśli saga jest jednoetapowa, rozważyć prosty handler; jeśli zostaje, ujednolicić upcastery i lokalizację.

### 4. DI: różne polityki subskrypcji i warianty `app.py`
- `definition` nie ma outbox-relay ani command-workera, a `user` nie konsumuje eventów.
- `app.py`: `definition/scheduling` fail-closed, reszta nie; `session` ma własny `/health` z backlogiem; `execution` używa `include_routes`.
- Pozostaje ujednolicić pozostałe warianty `app.py` i politykę workerów.

---

## P3 — testy, CI, zależności, DX

### 5. `pyproject.toml`
- Pozostaje: ograniczenie pre-existing reguł bezpieczeństwa Ruff (`S101/S311/S603/S106`) do świadomie opisanych wyjątków i follow-upów.

### 6. Testy
- Pozostaje: per-BC coverage, `RABBIT_TEST_URL` gate oraz redundantne `@pytest.mark.asyncio` przy `asyncio_mode=auto`.

### 7. `run_tests.ps1` tylko Windows + potrójne testy
- Pozostaje: przenośność narzędzi runnera, wielokrotne przebiegi testów oraz opcje `-Parallel`/`--lf`/JUnit.
- Pozostaje ujednolicić flagi Bandit, przenośny wybór narzędzi, jeden przebieg z `--cov` oraz wspólne flagi z CI.

### 8. CI: niereprodukowalne, dziurawe gate
- Pozostaje: cache, filtry `paths` oraz pełniejsze pokrycie testami biblioteki saga.
- `remaining/user/session-service.yml` nie obejmuje w filtrach `paths` `tests/system`, `contracts`, `platform`. `user-service.yml:49` może paść, gdy wygenerowane są `openapi.json/dist`.
- `publish-api-spec.yml:23` używa `pip install -e .` bez locka, brakuje walidacji OpenAPI, a `npm publish` nie ma `.npmrc/provenance`.
- `security-scan.yml`: Trivy `fs+image` ma `exit-code:1 HIGH,CRITICAL` i `ignore-unfixed:true` tylko dla obrazów; brakuje SARIF.
- `.github/` zawiera pomocnicze pliki kolidujące z `copilot-instructions.md` (`agent.md`, `ai_chat.md`, `veny_instal.md`, `open_code.md`, `instrukcje.txt`, `test.md`).
- Fix: `--locked` wszędzie, `paths` z `platform+system+contracts`, SARIF upload i sprzątnięcie `.github/`.

### 9. `deploy.ps1` / `backend.ps1`
- `deploy.ps1` sprawdza już format bez mutowania drzewa; pozostaje `git add deploy.ps1 .gitignore scripts shell openapi.json`, który pomija `pyproject/packaging/docs/workflows`, oraz sekwencyjny redeploy 7 serwisów bez health-wait/rollback.
- Fix: poprawny zakres `git add` oraz health-wait z rollbackiem.

### 10. Martwe pliki i brud DX
- Usunięte zostały nieużywane skrypty pomocnicze, deprecated shim testowy oraz osierocony `shell/alembic.ini`.
- Pozostaje ustalić strategię lockfile, ponieważ repozytorium ma rootowy lockfile, lockfile `shell/` oraz osobne lockfile pakietów serwisowych.
- Pozostaje opisać role `shell/certificates`, `shell/certs` i `packaging/shell-certificates`; `prepare_mtls_ca.ps1` oraz `generate_mtls_certs.py` są używane i nie są duplikatami.
- Pozostaje posprzątać lokalne artefakty (`tmp/`, `tmp-test/`, cache, logi i pliki baz danych) oraz sprawdzić historię pod kątem rzeczywistych sekretów.

---

## Uwagi środowiskowe

- Certyfikaty są śledzone przez Git; przed usunięciem lub rotacją trzeba sprawdzić ich zastosowanie w testach i demonstracjach.
- Guardrail rejestracji Query pomija pliki testowe i przechodzi dla wszystkich produkcyjnych dispatchy.
