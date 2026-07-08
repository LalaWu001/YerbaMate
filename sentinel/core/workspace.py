from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sentinel.core.models import AuditWorkspace, to_jsonable


class WorkspaceStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def create(self, project_name: str) -> AuditWorkspace:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_name = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in project_name)
        run_dir = self.root / f"{safe_name}-{timestamp}"
        artifacts_dir = run_dir / "artifacts"
        reports_dir = run_dir / "reports"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        reports_dir.mkdir(parents=True, exist_ok=True)
        return AuditWorkspace(run_dir=run_dir, artifacts_dir=artifacts_dir, reports_dir=reports_dir)

    @staticmethod
    def write_json(path: Path, data: Any) -> None:
        path.write_text(
            json.dumps(to_jsonable(data), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def write_text(path: Path, data: str) -> None:
        path.write_text(data, encoding="utf-8")
