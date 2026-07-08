from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from sentinel.tools.tool_locator import find_tool


class ExternalAnalyzerRunner:
    def run_slither(self, project_path: Path, output_dir: Path, enabled: bool) -> dict[str, Any]:
        if not enabled:
            return {"enabled": False, "available": False, "status": "skipped", "reason": "disabled"}
        slither = find_tool("slither")
        if not slither:
            return {"enabled": True, "available": False, "status": "skipped", "reason": "slither not found"}

        output_path = (output_dir / "slither_raw.json").resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = [slither, str(project_path.resolve()), "--json", str(output_path)]
        result = self._run(command, project_path, timeout_seconds=120)
        parsed = self._read_json(output_path)
        return {
            "enabled": True,
            "available": True,
            "status": "completed" if result["returncode"] == 0 else "failed",
            "command": command,
            "returncode": result["returncode"],
            "stdout_preview": result["stdout"][:4000],
            "stderr_preview": result["stderr"][:4000],
            "raw_output_path": str(output_path) if output_path.exists() else "",
            "summary": self._summarize_slither(parsed),
        }

    def run_foundry(self, project_path: Path, enabled: bool) -> dict[str, Any]:
        if not enabled:
            return {"enabled": False, "available": False, "status": "skipped", "reason": "disabled"}
        forge = find_tool("forge")
        if not forge:
            return {"enabled": True, "available": False, "status": "skipped", "reason": "forge not found"}
        if not (project_path / "foundry.toml").exists():
            return {"enabled": True, "available": True, "status": "skipped", "reason": "foundry.toml not found"}

        build = self._run([forge, "build"], project_path, timeout_seconds=180)
        tests = self._run([forge, "test", "-vv"], project_path, timeout_seconds=240)
        return {
            "enabled": True,
            "available": True,
            "status": "completed" if build["returncode"] == 0 and tests["returncode"] == 0 else "failed",
            "build": build,
            "test": tests,
        }

    @staticmethod
    def _run(command: list[str], cwd: Path, timeout_seconds: int) -> dict[str, Any]:
        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            return {
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        except subprocess.TimeoutExpired as exc:
            return {
                "returncode": -1,
                "stdout": exc.stdout or "",
                "stderr": f"timeout after {timeout_seconds}s\n{exc.stderr or ''}",
            }
        except OSError as exc:
            return {"returncode": -1, "stdout": "", "stderr": str(exc)}

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _summarize_slither(raw: dict[str, Any]) -> dict[str, Any]:
        detectors = raw.get("results", {}).get("detectors", []) if raw else []
        severity_counts: dict[str, int] = {}
        categories: dict[str, int] = {}
        for detector in detectors:
            impact = detector.get("impact", "Unknown")
            check = detector.get("check", "unknown")
            severity_counts[impact] = severity_counts.get(impact, 0) + 1
            categories[check] = categories.get(check, 0) + 1
        return {
            "detector_count": len(detectors),
            "severity_counts": severity_counts,
            "top_categories": dict(sorted(categories.items(), key=lambda item: item[1], reverse=True)[:10]),
        }
