#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Deploy SHELL: walidacja formatu + testy + commit + openapi + start wszystkich obrazow.

.DESCRIPTION
    Obrazy NIE sa uruchamiane bezposrednio przez ten skrypt - budowane i wznawiane
    sa przez skrypty per-service (shell/<service>/docker/scripts/manage.ps1 oraz
    shell/rabbitmq/docker/scripts/manage.ps1). Ten skrypt jedynie je wywoluje
    po kolei, jako zbiorczy orchestrator deployu.
#>
param(
    [string]$Message = "deploy: $(Get-Date -Format 'yyyy-MM-dd HH:mm')",
    [switch]$Commit
)

Write-Host "=== Krok 0: Sprawdzenie formatu ===" -ForegroundColor Cyan
python -m ruff format --check shell/ shell/tests
if ($LASTEXITCODE -ne 0) {
    Write-Host "Sprawdzenie formatu nie powiodlo sie" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== Krok 1: Testy ===" -ForegroundColor Cyan
& "$PSScriptRoot\run_tests.ps1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Testy nie przeszly - deploy anulowany" -ForegroundColor Red
    exit 1
}

if ($Commit) {
    Write-Host "`n=== Krok 2: Commit ===" -ForegroundColor Cyan
    git add -- deploy.ps1 .gitignore scripts shell openapi.json
    if ($LASTEXITCODE -eq 0) {
        git commit -m $Message
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Commit anulowany (brak zmian lub blad)" -ForegroundColor Yellow
    }
} else {
    Write-Host "`n=== Krok 2: Commit pominiety (uzyj -Commit jawnie) ===" -ForegroundColor Yellow
}

Write-Host "`n=== Krok 3: OpenAPI spec ===" -ForegroundColor Cyan
python scripts/generate-openapi.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Generowanie openapi nie powiodlo sie" -ForegroundColor Red
    exit 1
}

$shellDir = Join-Path $PSScriptRoot "shell"
$services = [ordered]@{
    user         = "shell\user_service\docker\scripts\manage.ps1"
    definition   = "shell\definition_service\docker\scripts\manage.ps1"
    session      = "shell\session_service\docker\scripts\manage.ps1"
    ingestion    = "shell\ingestion_service\docker\scripts\manage.ps1"
    project      = "shell\project_service\docker\scripts\manage.ps1"
    scheduling   = "shell\scheduling_service\docker\scripts\manage.ps1"
    execution    = "shell\execution_service\docker\scripts\manage.ps1"
    rabbit       = "shell\rabbitmq\docker\scripts\manage.ps1"
}

Write-Host "`n=== Krok 4: Build + start obrazow (per-service) ===" -ForegroundColor Cyan
& (Join-Path $PSScriptRoot $services["rabbit"]) up
if ($LASTEXITCODE -ne 0) {
    Write-Host "Start rabbit nie powiodl sie" -ForegroundColor Red
    exit 1
}

foreach ($name in $services.Keys) {
    if ($name -eq "rabbit") {
        continue
    }
    Write-Host "--- $name ---" -ForegroundColor Yellow
    & (Join-Path $PSScriptRoot $services[$name]) redeploy
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Redeploy $name nie powiodl sie" -ForegroundColor Red
        exit 1
    }
}

Write-Host "`n=== Deploy zakonczony ===" -ForegroundColor Green