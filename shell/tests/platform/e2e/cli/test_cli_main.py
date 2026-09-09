from __future__ import annotations

from shell.platform.framework.cli.main import main


class TestCliMain:
    def test_main_no_args_returns_1(self) -> None:
        assert main([]) == 1

    def test_main_unknown_mode_returns_1(self) -> None:
        assert main(["unknown_mode"]) == 1

    def test_main_known_mode_flag_returns_0(self, capsys) -> None:
        assert main(["--mode", "agent"]) == 0
        captured = capsys.readouterr()
        assert "agent" in captured.out

    def test_main_known_positional_mode_returns_0(self) -> None:
        assert main(["agent"]) == 0

    def test_main_known_flags_return_0(self) -> None:
        assert main(["--dry-run"]) == 0
        assert main(["--log-level", "DEBUG"]) == 0

    def test_main_help_returns_0(self, capsys) -> None:
        assert main(["--help"]) == 0
