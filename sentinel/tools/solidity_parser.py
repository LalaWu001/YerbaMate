from __future__ import annotations

import re
from pathlib import Path

from sentinel.core.models import ContractFact, FileFact, FunctionFact, ProjectSummary


CONTRACT_RE = re.compile(
    r"\b(contract|interface|library)\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s+is\s+([^{}]+?))?\s*\{",
    re.MULTILINE,
)
FUNCTION_RE = re.compile(
    r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)\s*(\([^)]*\))\s*([^{};]*)\{",
    re.MULTILINE,
)
EVENT_RE = re.compile(r"\bevent\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
MODIFIER_RE = re.compile(r"\bmodifier\s+([A-Za-z_][A-Za-z0-9_]*)\s*")
IMPORT_RE = re.compile(r"\bimport\s+(?:[^;]*?\s+from\s+)?[\"']([^\"']+)[\"'];")
STATE_RE = re.compile(
    r"^\s*(?:mapping\s*\([^;]+\)|[A-Za-z_][A-Za-z0-9_<>\[\]]*)\s+"
    r"(?:public|private|internal|constant|immutable|override|\s)*"
    r"([A-Za-z_][A-Za-z0-9_]*)\s*(?:=|;)",
    re.MULTILINE,
)


class SolidityProjectAnalyzer:
    DEFAULT_EXCLUDED_DIRS = {
        ".git",
        ".github",
        ".openzeppelin",
        ".vscode",
        "artifacts",
        "broadcast",
        "cache",
        "dist",
        "node_modules",
        "out",
        "release",
        "typechain",
        "types",
    }
    DEFAULT_MAX_FILE_BYTES = 1_200_000
    DEFAULT_MAX_FILES = 2500

    def analyze(self, project_path: Path) -> ProjectSummary:
        solidity_files, skipped_files, scan_warnings = self._discover_solidity_files(project_path)
        contracts: list[ContractFact] = []
        files: list[FileFact] = []
        import_graph: dict[str, list[str]] = {}
        for file_path in solidity_files:
            file_fact, parsed_contracts = self._parse_file(project_path, file_path)
            files.append(file_fact)
            import_graph[file_fact.path] = file_fact.imports
            contracts.extend(parsed_contracts)

        inheritance_graph = {contract.name: contract.inherits for contract in contracts if contract.inherits}
        dependency_files = [item.path for item in files if item.classification == "dependency"]
        test_files = [item.path for item in files if item.classification == "test"]
        generated_files = [item.path for item in files if item.classification == "generated"]

        return ProjectSummary(
            project_name=project_path.name,
            project_path=str(project_path),
            solidity_files=[str(path.relative_to(project_path)) for path in solidity_files],
            contracts=contracts,
            files=files,
            source_roots=self._detect_source_roots(files),
            dependency_files=dependency_files,
            test_files=test_files,
            generated_files=generated_files,
            skipped_files=skipped_files,
            import_graph=import_graph,
            inheritance_graph=inheritance_graph,
            scan_warnings=scan_warnings,
        )

    def _discover_solidity_files(self, root: Path) -> tuple[list[Path], list[FileFact], list[str]]:
        discovered: list[Path] = []
        skipped: list[FileFact] = []
        warnings: list[str] = []
        for file_path in sorted(root.rglob("*.sol")):
            relative_parts = file_path.relative_to(root).parts
            relative = str(file_path.relative_to(root))
            if any(part in self.DEFAULT_EXCLUDED_DIRS for part in relative_parts):
                skipped.append(self._file_fact(root, file_path, "skipped", "excluded_directory"))
                continue
            size_bytes = file_path.stat().st_size
            if size_bytes > self.DEFAULT_MAX_FILE_BYTES:
                skipped.append(self._file_fact(root, file_path, "skipped", "file_too_large"))
                continue
            discovered.append(file_path)
            if len(discovered) >= self.DEFAULT_MAX_FILES:
                warnings.append(f"Scan stopped after {self.DEFAULT_MAX_FILES} Solidity files. Narrow source roots for deeper analysis.")
                break
        return discovered, skipped, warnings

    def _parse_file(self, root: Path, file_path: Path) -> tuple[FileFact, list[ContractFact]]:
        source = file_path.read_text(encoding="utf-8", errors="ignore")
        relative = str(file_path.relative_to(root))
        file_fact = self._file_fact(root, file_path, self._classify_file(file_path.relative_to(root)), "")
        file_fact.imports = IMPORT_RE.findall(source)
        contract_matches = list(CONTRACT_RE.finditer(source))
        parsed: list[ContractFact] = []

        for index, match in enumerate(contract_matches):
            start = match.start()
            end = contract_matches[index + 1].start() if index + 1 < len(contract_matches) else len(source)
            block = source[start:end]
            parsed.append(
                ContractFact(
                    name=match.group(2),
                    kind=match.group(1),
                    file_path=relative,
                    line=self._line_number(source, match.start()),
                    inherits=self._parse_inherits(match.group(3) or ""),
                    functions=self._parse_functions(source, block, start),
                    events=EVENT_RE.findall(block),
                    modifiers=MODIFIER_RE.findall(block),
                    state_variables=self._parse_state_variables(block),
                )
            )

        return file_fact, parsed

    def _parse_functions(self, full_source: str, block: str, offset: int) -> list[FunctionFact]:
        functions: list[FunctionFact] = []
        for match in FUNCTION_RE.finditer(block):
            name = match.group(1)
            args = match.group(2)
            signature_tail = match.group(3)
            body = self._extract_body(block, match.end() - 1)
            modifiers = self._extract_modifiers(signature_tail)
            visibility = self._extract_visibility(signature_tail)
            signature = f"{name}{self._normalize_signature_args(args)}"
            functions.append(
                FunctionFact(
                    name=name,
                    visibility=visibility,
                    modifiers=modifiers,
                    line=self._line_number(full_source, offset + match.start()),
                    body=body,
                    signature=signature,
                    selector_hint=self._selector_hint(signature),
                )
            )
        return functions

    def _file_fact(self, root: Path, file_path: Path, classification: str, skipped_reason: str = "") -> FileFact:
        source = file_path.read_text(encoding="utf-8", errors="ignore") if not skipped_reason else ""
        return FileFact(
            path=str(file_path.relative_to(root)),
            classification=classification,
            size_bytes=file_path.stat().st_size,
            line_count=source.count("\n") + 1 if source else 0,
            imports=[],
            skipped_reason=skipped_reason,
        )

    @staticmethod
    def _classify_file(relative_path: Path) -> str:
        parts = {part.lower() for part in relative_path.parts}
        path_text = str(relative_path).lower()
        if {"test", "tests"} & parts or path_text.endswith(".t.sol"):
            return "test"
        if {"script", "scripts"} & parts:
            return "script"
        if {"lib", "libs", "vendor", "dependencies"} & parts:
            return "dependency"
        if {"generated", "gen"} & parts or "generated" in path_text:
            return "generated"
        return "project"

    @staticmethod
    def _detect_source_roots(files: list[FileFact]) -> list[str]:
        roots: dict[str, int] = {}
        for file in files:
            first = file.path.replace("\\", "/").split("/")[0]
            roots[first] = roots.get(first, 0) + 1
        return [root for root, _count in sorted(roots.items(), key=lambda item: (-item[1], item[0]))]

    @staticmethod
    def _parse_inherits(raw: str) -> list[str]:
        if not raw:
            return []
        names = []
        for part in raw.split(","):
            match = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)", part.strip())
            if match:
                names.append(match.group(1))
        return names

    @staticmethod
    def _normalize_signature_args(args: str) -> str:
        raw = args.strip()[1:-1].strip()
        if not raw:
            return "()"
        normalized = []
        for arg in raw.split(","):
            tokens = [token for token in arg.strip().split() if token not in {"memory", "calldata", "storage", "payable"}]
            normalized.append(tokens[0] if tokens else "")
        return "(" + ",".join(normalized) + ")"

    @staticmethod
    def _selector_hint(signature: str) -> str:
        # This is a stable display hint, not an EVM selector. A true selector needs Keccak.
        import hashlib

        return "0x" + hashlib.sha256(signature.encode("utf-8")).hexdigest()[:8]

    @staticmethod
    def _extract_body(source: str, brace_index: int) -> str:
        depth = 0
        for index in range(brace_index, len(source)):
            if source[index] == "{":
                depth += 1
            elif source[index] == "}":
                depth -= 1
                if depth == 0:
                    return source[brace_index + 1 : index]
        return ""

    @staticmethod
    def _extract_visibility(signature_tail: str) -> str:
        for visibility in ("external", "public", "internal", "private"):
            if re.search(rf"\b{visibility}\b", signature_tail):
                return visibility
        return "default"

    @staticmethod
    def _extract_modifiers(signature_tail: str) -> list[str]:
        ignored = {
            "external",
            "public",
            "internal",
            "private",
            "view",
            "pure",
            "payable",
            "virtual",
            "override",
            "returns",
            "memory",
            "calldata",
            "storage",
            "bool",
            "address",
            "string",
            "bytes",
            "bytes4",
            "bytes32",
            "int",
            "uint",
            "uint8",
            "uint16",
            "uint24",
            "uint32",
            "uint40",
            "uint48",
            "uint56",
            "uint64",
            "uint72",
            "uint80",
            "uint88",
            "uint96",
            "uint104",
            "uint112",
            "uint120",
            "uint128",
            "uint136",
            "uint144",
            "uint152",
            "uint160",
            "uint168",
            "uint176",
            "uint184",
            "uint192",
            "uint200",
            "uint208",
            "uint216",
            "uint224",
            "uint232",
            "uint240",
            "uint248",
            "uint256",
            "int8",
            "int16",
            "int24",
            "int32",
            "int40",
            "int48",
            "int56",
            "int64",
            "int72",
            "int80",
            "int88",
            "int96",
            "int104",
            "int112",
            "int120",
            "int128",
            "int136",
            "int144",
            "int152",
            "int160",
            "int168",
            "int176",
            "int184",
            "int192",
            "int200",
            "int208",
            "int216",
            "int224",
            "int232",
            "int240",
            "int248",
            "int256",
        }
        tokens = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", signature_tail)
        return [token for token in tokens if token not in ignored]

    @staticmethod
    def _parse_state_variables(block: str) -> list[str]:
        declarations = SolidityProjectAnalyzer._top_level_semicolon_statements(block)
        names = []
        for name in STATE_RE.findall("\n".join(declarations)):
            if name not in {"if", "for", "while", "return", "require"}:
                names.append(name)
        return sorted(set(names))

    @staticmethod
    def _top_level_semicolon_statements(block: str) -> list[str]:
        statements: list[str] = []
        current: list[str] = []
        depth = 0
        seen_contract_body = False
        for char in block:
            if char == "{":
                depth += 1
                seen_contract_body = True
                current = []
                continue
            if char == "}":
                depth = max(0, depth - 1)
                current = []
                continue
            if not seen_contract_body:
                continue
            if depth == 1:
                current.append(char)
                if char == ";":
                    statement = "".join(current).strip()
                    if not statement.startswith(("function ", "event ", "modifier ", "using ")):
                        statements.append(statement)
                    current = []
        return statements

    @staticmethod
    def _line_number(source: str, index: int) -> int:
        return source.count("\n", 0, index) + 1
