"""Koncept: fail-closed na poziomie fabryki aplikacji.

Reguła: każda ``create_*_app`` w ``*/framework/*/api/app.py`` musi odrzucać
pusty klucz API (``raise ValueError``), zanim powstanie aplikacja bez autha.
Wyjątek: fabryka z parametrem ``auth_enabled`` może dopuścić pusty klucz
wyłącznie gdy ``auth_enabled=False`` (jawny opt-out dla testów).

Poprawnie: ``if not api_key: raise ValueError(... fail-closed)`` albo
``if auth_enabled and not api_key: raise ValueError`` albo
``if not (api_key or jwt_secret): raise ValueError``.
"""

from __future__ import annotations

from _arch_helpers import BASE, architecture_assertion_message


def test_every_app_factory_fail_closed() -> None:
    # Wszystkie fabryki aplikacji: 7 serwisowych (przez setup_api_common)
    # + 6 agregatowych (samodzielne mikroserwisy z własnym AuthMiddleware).
    candidates = tuple(BASE.glob("*_service/framework/**/api/app.py"))
    app_files = tuple(p for p in candidates if "def create_" in p.read_text(encoding="utf-8"))
    assert len(app_files) == 13, f"expected 13 app factories, found {len(app_files)}: {app_files}"

    violations: list[str] = []
    for path in app_files:
        content = path.read_text(encoding="utf-8")
        has_factory = "def create_" in content and "_app(" in content
        has_guard = (
            "if not api_key:" in content
            or "if auth_enabled and not api_key:" in content
            or "if not (api_key or jwt_secret):" in content
        )
        has_raise = "raise ValueError" in content and "fail-closed" in content
        if not has_factory:
            violations.append(f"{path}: no create_*_app factory found")
        elif not (has_guard and has_raise):
            violations.append(f"{path}: missing fail-closed guard on empty api_key")

    assert not violations, architecture_assertion_message(
        "reguła testowana przez test_every_app_factory_fail_closed",
        "warunek zapisany w asercji musi być spełniony",
        "Every create_*_app factory must reject empty api_key:\n" + "\n".join(violations),
    )
