from __future__ import annotations

import os
import shutil
from pathlib import Path


def find_tool(name: str) -> str | None:
    direct = shutil.which(name)
    if direct:
        return direct

    home = Path.home()
    candidates = {
        "slither": [
            home / ".local" / "bin" / "slither.exe",
            home / "pipx" / "venvs" / "slither-analyzer" / "Scripts" / "slither.exe",
        ],
        "forge": [
            home / ".foundry" / "bin" / "forge.exe",
            home / "foundry" / "forge.exe",
        ],
        "solc": [
            home / ".solc-select" / "artifacts" / "solc.exe",
        ],
        "echidna": [
            home / ".local" / "bin" / "echidna.exe",
        ],
        "semgrep": [
            home / ".local" / "bin" / "semgrep.exe",
            home / "pipx" / "venvs" / "semgrep" / "Scripts" / "semgrep.exe",
        ],
        "aderyn": [
            home / ".local" / "bin" / "aderyn.exe",
            home / ".cargo" / "bin" / "aderyn.exe",
        ],
        "halmos": [
            home / ".local" / "bin" / "halmos.exe",
            home / "pipx" / "venvs" / "halmos" / "Scripts" / "halmos.exe",
        ],
    }.get(name, [])

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    extra_paths = os.getenv("YERBAMATE_TOOL_PATHS", os.getenv("CONTRACTSENTINEL_TOOL_PATHS", ""))
    for folder in [Path(item.strip()) for item in extra_paths.split(os.pathsep) if item.strip()]:
        candidate = folder / f"{name}.exe"
        if candidate.exists():
            return str(candidate)
    return None
