from __future__ import annotations

import subprocess
from pathlib import Path

from sentinel.tools.tool_locator import find_tool


class ToolProbe:
    TOOLS = {
        "slither": ["slither", "--version"],
        "forge": ["forge", "--version"],
        "solc": ["solc", "--version"],
        "echidna": ["echidna", "--version"],
        "semgrep": ["semgrep", "--version"],
        "aderyn": ["aderyn", "--version"],
        "halmos": ["halmos", "--version"],
    }

    def probe(self, project_path: Path) -> dict:
        tools = {}
        for name, command in self.TOOLS.items():
            executable = find_tool(command[0])
            if not executable:
                tools[name] = {"available": False, "version": "", "error": "not found"}
                continue
            try:
                command = [executable, *command[1:]]
                completed = subprocess.run(
                    command,
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                version = (completed.stdout or completed.stderr).strip().splitlines()[0] if (completed.stdout or completed.stderr).strip() else ""
                tools[name] = {"available": True, "version": version, "error": ""}
            except (subprocess.SubprocessError, OSError) as exc:
                tools[name] = {"available": True, "version": "", "error": str(exc)}

        project_files = {
            "foundry_toml": (project_path / "foundry.toml").exists(),
            "hardhat_config": any((project_path / name).exists() for name in ["hardhat.config.ts", "hardhat.config.js"]),
            "package_json": (project_path / "package.json").exists(),
            "remappings": (project_path / "remappings.txt").exists(),
        }
        return {"tools": tools, "project_files": project_files}
