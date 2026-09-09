"""Main CLI entrypoint for shell — dispatches to per-mode command handlers."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from shell.platform.framework.cli.parser import build_parser

if TYPE_CHECKING:
    from collections.abc import Sequence

KNOWN_MODES = frozenset(
    {
        "agent",
        "router",
        "tasker",
        "tool",
        "worker",
        "import-task",
        "route",
        "run-tasker",
    }
)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry-point — first positional arg is the mode/subcommand."""
    arguments = list(argv) if argv is not None else sys.argv[1:]
    if not arguments:
        print("Usage: shell <mode> [options]", file=sys.stderr)
        return 1

    if arguments and not arguments[0].startswith("-"):
        mode = arguments[0]
        if mode not in KNOWN_MODES:
            print(f"Unknown mode: {mode!r}", file=sys.stderr)
            return 1
        parser = build_parser()
        try:
            parsed = parser.parse_args(arguments[1:])
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 2
            return code
        if parsed.mode is None:
            parsed.mode = mode
        print(parsed)
        return 0

    parser = build_parser()
    try:
        parsed = parser.parse_args(arguments)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 2
        if code == 0:
            return 0
        if arguments and not arguments[0].startswith("-"):
            print(f"Unknown mode: {arguments[0]!r}", file=sys.stderr)
            return 1
        return code
    if parsed.mode is not None and parsed.mode not in KNOWN_MODES:
        print(f"Unknown mode: {parsed.mode!r}", file=sys.stderr)
        return 1
    print(parsed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
