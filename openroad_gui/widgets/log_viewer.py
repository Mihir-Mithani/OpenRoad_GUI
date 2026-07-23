"""Scrollable terminal/log viewer widget."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk


class LogViewer(ttk.Frame):
    def __init__(self, master: tk.Misc, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self._build_ui()

    def _build_ui(self) -> None:
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=4, pady=(4, 0))

        ttk.Label(toolbar, text="Flow Log", font=("", 11, "bold")).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Clear", command=self.clear, width=8).pack(
            side=tk.RIGHT, padx=2
        )
        ttk.Button(toolbar, text="Export Log...", command=self._export_log, width=10).pack(
            side=tk.RIGHT, padx=2
        )

        self.text = scrolledtext.ScrolledText(
            self,
            wrap=tk.WORD,
            height=12,
            font=("Menlo", 11),
            state=tk.DISABLED,
            background="#1e1e1e",
            foreground="#d4d4d4",
            insertbackground="#d4d4d4",
        )
        self.text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.text.tag_configure("stdout", foreground="#d4d4d4")
        self.text.tag_configure("stderr", foreground="#f48771")
        self.text.tag_configure("info", foreground="#4ec9b0")
        self.text.tag_configure("error", foreground="#ff6b6b", font=("Menlo", 11, "bold"))

    def append(self, stream: str, line: str) -> None:
        self.text.configure(state=tk.NORMAL)
        tag = stream if stream in ("stdout", "stderr") else "info"
        self.text.insert(tk.END, line, tag)
        self.text.see(tk.END)
        self.text.configure(state=tk.DISABLED)

    def log_info(self, message: str) -> None:
        self.append("info", message if message.endswith("\n") else message + "\n")

    def log_error(self, message: str) -> None:
        self.text.configure(state=tk.NORMAL)
        self.text.insert(tk.END, message + "\n", "error")
        self.text.see(tk.END)
        self.text.configure(state=tk.DISABLED)

    def clear(self) -> None:
        self.text.configure(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.configure(state=tk.DISABLED)

    def get_text(self) -> str:
        """Get all text content from the log viewer."""
        return self.text.get("1.0", tk.END)

    def _export_log(self) -> None:
        """Export the log content to a file."""
        content = self.get_text()
        if not content.strip():
            return
        path = filedialog.asksaveasfilename(
            title="Export Log",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
            except OSError:
                pass  # Silently ignore export errors
