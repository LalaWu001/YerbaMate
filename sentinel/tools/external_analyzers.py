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

    def run_semgrep(self, project_path: Path, output_dir: Path, enabled: bool) -> dict[str, Any]:
        if not enabled:
            return {"enabled": False, "available": False, "status": "skipped", "reason": "disabled"}
        semgrep = find_tool("semgrep")
        if not semgrep:
            return {"enabled": True, "available": False, "status": "skipped", "reason": "semgrep not found"}

        output_path = (output_dir / "semgrep_raw.json").resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = [semgrep, "scan", "--config", "auto", "--json", "--output", str(output_path), str(project_path.resolve())]
        result = self._run(command, project_path, timeout_seconds=180)
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
            "summary": self._summarize_semgrep(parsed),
        }

    def run_echidna(self, project_path: Path, output_dir: Path, enabled: bool) -> dict[str, Any]:
        if not enabled:
            return {"enabled": False, "available": False, "status": "skipped", "reason": "disabled"}
        echidna = find_tool("echidna")
        if not echidna:
            return {"enabled": True, "available": False, "status": "skipped", "reason": "echidna not found"}

        config_path = self._first_existing(
            project_path,
            ["echidna.yaml", "echidna.yml", "crytic.yaml", "crytic.yml"],
        )
        if not config_path:
            return {"enabled": True, "available": True, "status": "skipped", "reason": "echidna config not found"}

        output_path = (output_dir / "echidna_raw.json").resolve()
        command = [echidna, str(project_path.resolve()), "--config", str(config_path), "--format", "json"]
        result = self._run(command, project_path, timeout_seconds=300)
        if result["stdout"]:
            output_path.write_text(result["stdout"], encoding="utf-8")
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
            "summary": self._summarize_echidna(parsed),
        }

    def run_aderyn(self, project_path: Path, output_dir: Path, enabled: bool) -> dict[str, Any]:
        if not enabled:
            return {"enabled": False, "available": False, "status": "skipped", "reason": "disabled"}
        aderyn = find_tool("aderyn")
        if not aderyn:
            return {"enabled": True, "available": False, "status": "skipped", "reason": "aderyn not found"}

        output_path = (output_dir / "aderyn_report.md").resolve()
        command = [aderyn, str(project_path.resolve()), "--output", str(output_path)]
        result = self._run(command, project_path, timeout_seconds=180)
        return {
            "enabled": True,
            "available": True,
            "status": "completed" if result["returncode"] == 0 else "failed",
            "command": command,
            "returncode": result["returncode"],
            "stdout_preview": result["stdout"][:4000],
            "stderr_preview": result["stderr"][:4000],
            "raw_output_path": str(output_path) if output_path.exists() else "",
            "summary": {"report_generated": output_path.exists()},
        }

    @staticmethod
    def _run(command: list[str], cwd: Path, timeout_seconds: int) -> dict[str, Any]:
        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
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

    @staticmethod
    def _summarize_semgrep(raw: dict[str, Any]) -> dict[str, Any]:
        results = raw.get("results", []) if raw else []
        severity_counts: dict[str, int] = {}
        rules: dict[str, int] = {}
        for item in results:
            extra = item.get("extra", {})
            severity = extra.get("severity", "Unknown")
            rule_id = item.get("check_id", "unknown")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            rules[rule_id] = rules.get(rule_id, 0) + 1
        return {
            "finding_count": len(results),
            "severity_counts": severity_counts,
            "top_rules": dict(sorted(rules.items(), key=lambda item: item[1], reverse=True)[:10]),
        }

    @staticmethod
    def _summarize_echidna(raw: dict[str, Any]) -> dict[str, Any]:
        tests = raw.get("tests", []) if raw else []
        failed = [item for item in tests if item.get("status") not in {"passed", "solved"}]
        return {
            "test_count": len(tests),
            "failed_count": len(failed),
        }

    @staticmethod
    def _first_existing(root: Path, names: list[str]) -> Path | None:
        for name in names:
            candidate = root / name
            if candidate.exists():
                return candidate
        return None
