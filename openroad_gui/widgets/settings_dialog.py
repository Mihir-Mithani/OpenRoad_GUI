"""Settings dialog for environment and path configuration."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from openroad_gui.config import AppConfig, PLATFORMS, save_config


class SettingsDialog(tk.Toplevel):
    def __init__(
        self,
        master: tk.Misc,
        config: AppConfig,
        on_save: Callable[[AppConfig], None],
    ) -> None:
        super().__init__(master)
        self.config = config
        self.on_save = on_save
        self.title("Settings")
        self.resizable(True, False)
        self.minsize(520, 420)

        self._build_ui()
        self._load_values()

        self.transient(master)
        self.grab_set()

    def _build_ui(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        paths_tab = ttk.Frame(notebook, padding=8)
        design_tab = ttk.Frame(notebook, padding=8)
        env_tab = ttk.Frame(notebook, padding=8)
        notebook.add(paths_tab, text="Paths")
        notebook.add(design_tab, text="Active Design")
        notebook.add(env_tab, text="Environment")

        # Paths tab
        self.orfs_var = tk.StringVar()
        self._add_path_row(paths_tab, "OpenROAD Root (ORFS):", self.orfs_var, 0)

        self.klayout_var = tk.StringVar()
        self._add_path_row(paths_tab, "KLayout binary:", self.klayout_var, 1, file_picker=True)

        # Design tab
        ttk.Label(design_tab, text="Platform:").grid(row=0, column=0, sticky=tk.W, pady=4)
        self.platform_var = tk.StringVar()
        ttk.Combobox(
            design_tab,
            textvariable=self.platform_var,
            values=PLATFORMS,
            state="readonly",
            width=30,
        ).grid(row=0, column=1, sticky=tk.EW, pady=4)

        ttk.Label(design_tab, text="Design name:").grid(row=1, column=0, sticky=tk.W, pady=4)
        self.design_var = tk.StringVar()
        ttk.Entry(design_tab, textvariable=self.design_var, width=32).grid(
            row=1, column=1, sticky=tk.EW, pady=4
        )

        ttk.Label(design_tab, text="config.mk path:").grid(row=2, column=0, sticky=tk.W, pady=4)
        self.config_var = tk.StringVar()
        config_frame = ttk.Frame(design_tab)
        config_frame.grid(row=2, column=1, sticky=tk.EW, pady=4)
        ttk.Entry(config_frame, textvariable=self.config_var, width=36).pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )
        ttk.Button(
            config_frame,
            text="Browse…",
            command=self._browse_config,
        ).pack(side=tk.LEFT, padx=(4, 0))

        ttk.Button(
            design_tab,
            text="Auto-fill config from design name",
            command=self._autofill_config,
        ).grid(row=3, column=1, sticky=tk.W, pady=8)

        design_tab.columnconfigure(1, weight=1)

        # Environment tab
        ttk.Label(
            env_tab,
            text="Extra environment variables (one per line, KEY=VALUE):",
        ).pack(anchor=tk.W)
        self.env_text = tk.Text(env_tab, height=10, width=50, font=("Menlo", 11))
        self.env_text.pack(fill=tk.BOTH, expand=True, pady=4)

        ttk.Label(
            env_tab,
            text="These are exported after sourcing use-openroad.sh.",
            foreground="gray",
        ).pack(anchor=tk.W)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=8, pady=(0, 8))
        ttk.Button(btn_frame, text="Save", command=self._save).pack(side=tk.RIGHT, padx=4)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT)

    def _add_path_row(
        self,
        parent: ttk.Frame,
        label: str,
        variable: tk.StringVar,
        row: int,
        *,
        file_picker: bool = False,
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=4)
        entry = ttk.Entry(parent, textvariable=variable, width=48)
        entry.grid(row=row, column=1, sticky=tk.EW, pady=4, padx=(4, 0))

        def browse() -> None:
            if file_picker:
                path = filedialog.askopenfilename(title=label)
            else:
                path = filedialog.askdirectory(title=label)
            if path:
                variable.set(path)

        ttk.Button(parent, text="Browse…", command=browse).grid(
            row=row, column=2, padx=4, pady=4
        )
        parent.columnconfigure(1, weight=1)

    def _load_values(self) -> None:
        self.orfs_var.set(self.config.orfs_root)
        self.klayout_var.set(self.config.klayout_cmd)
        self.platform_var.set(self.config.platform)
        self.design_var.set(self.config.design_name)
        self.config_var.set(self.config.design_config)

        env_lines = [f"{k}={v}" for k, v in self.config.extra_env.items()]
        self.env_text.delete("1.0", tk.END)
        self.env_text.insert("1.0", "\n".join(env_lines))

    def _browse_config(self) -> None:
        initial = self.config.flow_dir / "designs"
        path = filedialog.askopenfilename(
            title="Select config.mk",
            initialdir=str(initial) if initial.is_dir() else None,
            filetypes=[("Makefile config", "config.mk"), ("All files", "*.*")],
        )
        if path:
            self.config_var.set(path)
            rel = Path(path)
            if "designs" in rel.parts:
                idx = rel.parts.index("designs")
                if idx + 2 < len(rel.parts):
                    self.platform_var.set(rel.parts[idx + 1])
                    self.design_var.set(rel.parts[idx + 2])

    def _autofill_config(self) -> None:
        platform = self.platform_var.get().strip()
        design = self.design_var.get().strip()
        if platform and design:
            self.config_var.set(f"./designs/{platform}/{design}/config.mk")

    def _parse_extra_env(self) -> dict[str, str]:
        result: dict[str, str] = {}
        for line in self.env_text.get("1.0", tk.END).splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip()
        return result

    def _save(self) -> None:
        updated = AppConfig(
            orfs_root=self.orfs_var.get().strip(),
            klayout_cmd=self.klayout_var.get().strip(),
            design_config=self.config_var.get().strip(),
            platform=self.platform_var.get().strip(),
            design_name=self.design_var.get().strip(),
            extra_env=self._parse_extra_env(),
            last_project_dir=self.config.last_project_dir,
        )

        if updated.design_config and not updated.design_config.startswith("./"):
            flow = updated.flow_dir
            try:
                rel = Path(updated.design_config).relative_to(flow)
                updated.design_config = f"./{rel.as_posix()}"
            except ValueError:
                pass

        errors = updated.validate()
        if errors:
            messagebox.showwarning("Validation", "\n".join(errors))

        save_config(updated)
        self.on_save(updated)
        self.destroy()
