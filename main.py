from __future__ import annotations

import sys

from sentinel.app import run_desktop_app
from sentinel.cli import run_cli


def main() -> int:
    if len(sys.argv) > 1:
        return run_cli(sys.argv[1:])
    run_desktop_app()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
