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
    }.get(name, [])

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    extra_paths = os.getenv("CONTRACTSENTINEL_TOOL_PATHS", "")
    for folder in [Path(item.strip()) for item in extra_paths.split(os.pathsep) if item.strip()]:
        candidate = folder / f"{name}.exe"
        if candidate.exists():
            return str(candidate)
    return None
