from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from sentinel.core.manager import AuditManager


class ContractSentinelApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("ContractSentinel Desktop")
        self.geometry("1040x700")
        self.minsize(900, 620)

        self.project_path = tk.StringVar()
        self.status_text = tk.StringVar(value="Ready")
        self.report_path: Path | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=14)
        root.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(root, text="ContractSentinel", font=("Segoe UI", 20, "bold"))
        title.pack(anchor=tk.W)

        subtitle = ttk.Label(
            root,
            text="Local smart contract audit agent demo",
            font=("Segoe UI", 10),
        )
        subtitle.pack(anchor=tk.W, pady=(0, 14))

        input_bar = ttk.Frame(root)
        input_bar.pack(fill=tk.X)

        path_entry = ttk.Entry(input_bar, textvariable=self.project_path)
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Button(input_bar, text="Browse", command=self._browse).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(input_bar, text="Run Audit", command=self._run_audit).pack(side=tk.LEFT, padx=(8, 0))

        body = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True, pady=(14, 8))

        left = ttk.Frame(body, padding=(0, 0, 10, 0))
        body.add(left, weight=1)

        right = ttk.Frame(body)
        body.add(right, weight=3)

        ttk.Label(left, text="Pipeline", font=("Segoe UI", 11, "bold")).pack(anchor=tk.W)
        self.steps = tk.Listbox(left, height=12)
        self.steps.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        for step in [
            "Project indexing",
            "Code fact extraction",
            "Protocol understanding",
            "Business rule selection",
            "Transaction flow analysis",
            "Threat modeling",
            "Verification",
            "Report generation",
        ]:
            self.steps.insert(tk.END, step)

        ttk.Label(right, text="Audit Report", font=("Segoe UI", 11, "bold")).pack(anchor=tk.W)
        self.report = tk.Text(right, wrap=tk.WORD, undo=False)
        self.report.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        self.report.insert(tk.END, "Choose a Solidity project folder and run an audit.")

        footer = ttk.Frame(root)
        footer.pack(fill=tk.X)
        ttk.Label(footer, textvariable=self.status_text).pack(side=tk.LEFT)
        ttk.Button(footer, text="Open Report Folder", command=self._open_report_folder).pack(side=tk.RIGHT)

    def _browse(self) -> None:
        selected = filedialog.askdirectory(title="Select Solidity project")
        if selected:
            self.project_path.set(selected)

    def _run_audit(self) -> None:
        project = Path(self.project_path.get().strip())
        if not project.exists():
            messagebox.showerror("Invalid project", "Please select an existing project folder.")
            return

        self.status_text.set("Running audit...")
        self.report.delete("1.0", tk.END)
        self.report.insert(tk.END, "Audit is running. Artifacts will be saved under audits/.")
        self.steps.selection_clear(0, tk.END)

        thread = threading.Thread(target=self._audit_worker, args=(project,), daemon=True)
        thread.start()

    def _audit_worker(self, project: Path) -> None:
        try:
            manager = AuditManager(workspace_root=Path("audits"))
            result = manager.audit(project)
            report_text = result.report_path.read_text(encoding="utf-8")
            self.after(0, self._show_result, result.report_path, report_text)
        except Exception as exc:
            self.after(0, self._show_error, exc)

    def _show_result(self, report_path: Path, report_text: str) -> None:
        self.report_path = report_path
        self.report.delete("1.0", tk.END)
        self.report.insert(tk.END, report_text)
        self.status_text.set(f"Audit complete: {report_path}")
        self.steps.selection_set(0, tk.END)

    def _show_error(self, exc: Exception) -> None:
        self.status_text.set("Audit failed")
        messagebox.showerror("Audit failed", str(exc))

    def _open_report_folder(self) -> None:
        if not self.report_path:
            messagebox.showinfo("No report yet", "Run an audit first.")
            return
        import os

        os.startfile(self.report_path.parent)


def run_desktop_app() -> None:
    app = ContractSentinelApp()
    app.mainloop()
