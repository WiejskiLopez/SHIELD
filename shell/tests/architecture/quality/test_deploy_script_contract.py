"""Koncept: deterministyczny deploy.

Reguła: deploy waliduje format bez mutowania drzewa roboczego.
Poprawnie: sprawdzenie formatu nie uruchamia automatycznego formatowania.
"""

from pathlib import Path

_DEPLOY = Path(__file__).parents[4] / "deploy.ps1"


def test_deploy_checks_format_without_autoformatting() -> None:
    source = _DEPLOY.read_text(encoding="utf-8")

    assert "ruff format --check shell/ shell/tests" in source
    assert "ruff format shell/ shell/tests" not in source