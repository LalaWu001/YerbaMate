from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class FunctionFact:
    name: str
    visibility: str
    modifiers: list[str]
    line: int
    body: str
    signature: str = ""
    selector_hint: str = ""


@dataclass
class ContractFact:
    name: str
    kind: str
    file_path: str
    line: int
    inherits: list[str] = field(default_factory=list)
    functions: list[FunctionFact] = field(default_factory=list)
    events: list[str] = field(default_factory=list)
    modifiers: list[str] = field(default_factory=list)
    state_variables: list[str] = field(default_factory=list)


@dataclass
class FileFact:
    path: str
    classification: str
    size_bytes: int
    line_count: int
    imports: list[str] = field(default_factory=list)
    skipped_reason: str = ""


@dataclass
class ProjectSummary:
    project_name: str
    project_path: str
    solidity_files: list[str]
    contracts: list[ContractFact]
    files: list[FileFact] = field(default_factory=list)
    source_roots: list[str] = field(default_factory=list)
    dependency_files: list[str] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)
    generated_files: list[str] = field(default_factory=list)
    skipped_files: list[FileFact] = field(default_factory=list)
    import_graph: dict[str, list[str]] = field(default_factory=dict)
    inheritance_graph: dict[str, list[str]] = field(default_factory=dict)
    scan_warnings: list[str] = field(default_factory=list)


@dataclass
class AuditWorkspace:
    run_dir: Path
    artifacts_dir: Path
    reports_dir: Path


@dataclass
class AuditResult:
    workspace: AuditWorkspace
    report_path: Path
    artifacts: dict[str, Any]


def to_jsonable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    return value
