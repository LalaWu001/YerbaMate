from __future__ import annotations

import argparse
import json
from pathlib import Path

from sentinel.core.config import AuditConfig
from sentinel.core.manager import AuditManager


def run_cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="ContractSentinel")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit_parser = subparsers.add_parser("audit", help="Audit a local Solidity project")
    audit_parser.add_argument("project_path", help="Path to a Solidity project or folder")
    audit_parser.add_argument(
        "--workspace-root",
        default="audits",
        help="Directory where audit artifacts are written",
    )
    audit_parser.add_argument(
        "--config",
        default=None,
        help="Path to an audit config JSON file",
    )
    audit_parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable run metadata",
    )

    args = parser.parse_args(argv)

    if args.command == "audit":
        config = AuditConfig.from_file(Path(args.config)) if args.config else AuditConfig.default()
        manager = AuditManager(workspace_root=Path(args.workspace_root), config=config)
        result = manager.audit(Path(args.project_path))
        if args.json:
            print(
                json.dumps(
                    {
                        "report_path": str(result.report_path),
                        "run_dir": str(result.workspace.run_dir),
                        "artifacts_dir": str(result.workspace.artifacts_dir),
                        "reports_dir": str(result.workspace.reports_dir),
                    },
                    ensure_ascii=False,
                )
            )
            return 0
        print(f"Audit complete: {result.report_path}")
        print(f"Artifacts: {result.workspace.run_dir}")
        return 0

    return 2
