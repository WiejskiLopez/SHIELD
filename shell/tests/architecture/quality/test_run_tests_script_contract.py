"""Koncept: przenośny runner testów.

Reguła: runner zachowuje granice argumentów natywnych poleceń.
Poprawnie: proces otrzymuje tokenizowane argumenty bez ewaluacji tekstu.
"""

from pathlib import Path

_RUNNER = Path(__file__).parents[4] / "run_tests.ps1"


def test_runner_tokenizes_command_arguments_before_start_process() -> None:
    source = _RUNNER.read_text(encoding="utf-8")

    assert "PSParser]::Tokenize" in source
    assert "-ArgumentList $argumentList" in source
    assert "-split \"\\s+\", 2" not in source
    assert "Get-Command python -ErrorAction Stop" in source