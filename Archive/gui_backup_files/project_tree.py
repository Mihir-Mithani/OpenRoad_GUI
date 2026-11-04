"""Project directory tree widget."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Callable

from openroad_gui.config import PLATFORMS
from openroad_gui.templates import create_design, write_template_file

IGNORED_DIRS = {
    ".git",
    "__pycache__",
    "objects",
    "reports",
    "logs",
    "BUILD",
    "src",
}

RESULT_EXTENSIONS = {".gds", ".odb", ".def", ".v", ".spef", ".sdc"}


class ProjectTree(ttk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        on_select: Callable[[Path], None] | None = None,
        on_view_gds: Callable[[Path], None] | None = None,
        on_open_or_gui: Callable[[Path], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self.on_select = on_select
        self.on_view_gds = on_view_gds
        self.on_open_or_gui = on_open_or_gui
        self.root_path: Path | None = None
        self.active_results_dir: Path | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=4, pady=4)

        ttk.Label(header, text="Project", font=("", 11, "bold")).pack(side=tk.LEFT)
        ttk.Button(header, text="↻", width=3, command=self.refresh).pack(
            side=tk.RIGHT
        )

        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))

        self.tree = ttk.Treeview(tree_frame, show="tree", selectmode="browse")
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Button-3>", self._show_context_menu)

        actions = ttk.Frame(self)
        actions.pack(fill=tk.X, padx=4, pady=4)

        ttk.Button(actions, text="New Design", command=self._new_design).pack(
            fill=tk.X, pady=2
        )
        ttk.Button(actions, text="Open Folder", command=self._open_folder).pack(
            fill=tk.X, pady=2
        )

        self._dir_context_menu = tk.Menu(self, tearoff=0)
        self._dir_context_menu.add_command(
            label="New Verilog (.v)", command=lambda: self._add_template("verilog")
        )
        self._dir_context_menu.add_command(
            label="New Testbench (.tb)", command=lambda: self._add_template("testbench")
        )
        self._dir_context_menu.add_command(
            label="New SDC (.sdc)", command=lambda: self._add_template("sdc")
        )
        self._dir_context_menu.add_command(
            label="New config.mk", command=lambda: self._add_template("config_mk")
        )
        self._dir_context_menu.add_command(
            label="New config.json", command=lambda: self._add_template("config_json")
        )
        self._dir_context_menu.add_separator()
        self._dir_context_menu.add_command(label="Refresh", command=self.refresh)

        self._file_context_menu = tk.Menu(self, tearoff=0)
        self._file_context_menu.add_command(
            label="View in KLayout", command=self._ctx_view_gds
        )
        self._file_context_menu.add_command(
            label="Preview Layout", command=self._ctx_preview_gds
        )
        self._file_context_menu.add_separator()
        self._file_context_menu.add_command(
            label="View in OpenROAD GUI", command=self._ctx_open_or_gui
        )
        self._file_context_menu.add_separator()
        self._file_context_menu.add_command(label="Refresh", command=self.refresh)

        self._path_map: dict[str, Path] = {}
        self._context_target: Path | None = None

    def set_root(self, path: Path, active_results_dir: Path | None = None) -> None:
        self.root_path = path
        self.active_results_dir = active_results_dir
        self.refresh()

    def refresh(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self._path_map.clear()

        if not self.root_path or not self.root_path.exists():
            self.tree.insert("", tk.END, text="(no project loaded)", open=True)
            return

        root_id = self.tree.insert("", tk.END, text=self.root_path.name, open=True)
        self._path_map[root_id] = self.root_path

        if self.active_results_dir and self.active_results_dir.is_dir():
            label = f"results ({self.active_results_dir.parent.name})/"
            results_id = self.tree.insert(root_id, tk.END, text=label, open=True)
            self._path_map[results_id] = self.active_results_dir
            self._populate_results(results_id, self.active_results_dir)

        self._populate(root_id, self.root_path, depth=0, skip_results=True)

    def _populate_results(self, parent_id: str, directory: Path) -> None:
        try:
            entries = sorted(
                directory.iterdir(),
                key=lambda p: (not p.is_dir(), p.name.lower()),
            )
        except PermissionError:
            return

        for entry in entries:
            if entry.is_dir():
                node_id = self.tree.insert(parent_id, tk.END, text=entry.name + "/", open=True)
                self._path_map[node_id] = entry
                self._populate_results(node_id, entry)
            elif entry.suffix.lower() in RESULT_EXTENSIONS:
                node_id = self.tree.insert(parent_id, tk.END, text=entry.name)
                self._path_map[node_id] = entry

    def _populate(
        self, parent_id: str, directory: Path, depth: int, *, skip_results: bool = False
    ) -> None:
        if depth > 6:
            return

        try:
            entries = sorted(
                directory.iterdir(),
                key=lambda p: (not p.is_dir(), p.name.lower()),
            )
        except PermissionError:
            return

        for entry in entries:
            if entry.name.startswith(".") and entry.name != ".gitkeep":
                continue
            if entry.is_dir():
                if entry.name in IGNORED_DIRS:
                    continue
                if skip_results and entry.name == "results":
                    continue

            label = entry.name + ("/" if entry.is_dir() else "")
            node_id = self.tree.insert(parent_id, tk.END, text=label, open=depth < 2)
            self._path_map[node_id] = entry

            if entry.is_dir():
                self._populate(node_id, entry, depth + 1, skip_results=skip_results)

    def get_selected_path(self) -> Path | None:
        selection = self.tree.selection()
        if not selection:
            return None
        return self._path_map.get(selection[0])

    def _on_tree_select(self, _event: tk.Event) -> None:
        path = self.get_selected_path()
        if path and self.on_select:
            self.on_select(path)

    def _on_double_click(self, _event: tk.Event) -> None:
        path = self.get_selected_path()
        if not path:
            return
        if path.suffix.lower() == ".gds" and self.on_view_gds:
            self.on_view_gds(path)
        elif path.is_file() and self.on_select:
            self.on_select(path)

    def _show_context_menu(self, event: tk.Event) -> None:
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)
        self._context_target = self._path_map.get(item)
        if not self._context_target:
            return

        if self._context_target.is_dir():
            self._dir_context_menu.post(event.x_root, event.y_root)
        elif self._context_target.suffix.lower() in {".gds", ".odb"}:
            menu = tk.Menu(self, tearoff=0)
            if self._context_target.suffix.lower() == ".gds":
                menu.add_command(label="View in KLayout", command=self._ctx_view_gds)
                menu.add_command(label="Preview Layout", command=self._ctx_preview_gds)
                menu.add_separator()
            if self._context_target.suffix.lower() == ".odb":
                menu.add_command(
                    label="View in OpenROAD GUI", command=self._ctx_open_or_gui
                )
                menu.add_separator()
            menu.add_command(label="Refresh", command=self.refresh)
            menu.post(event.x_root, event.y_root)

    def _ctx_view_gds(self) -> None:
        if self._context_target and self.on_view_gds:
            self.on_view_gds(self._context_target)

    def _ctx_preview_gds(self) -> None:
        if self._context_target and self.on_select:
            self.on_select(self._context_target)

    def _ctx_open_or_gui(self) -> None:
        if self._context_target and self.on_open_or_gui:
            self.on_open_or_gui(self._context_target)

    def _designs_dir(self) -> Path | None:
        if not self.root_path:
            return None
        designs = self.root_path / "designs"
        return designs if designs.is_dir() else None

    def _new_design(self) -> None:
        designs_dir = self._designs_dir()
        if not designs_dir:
            messagebox.showerror(
                "No designs directory",
                "Open an OpenROAD flow/ directory first (Settings → Flow Directory).",
            )
            return

        dialog = _NewDesignDialog(self)
        self.wait_window(dialog)
        if not dialog.result:
            return

        platform, design_name = dialog.result
        try:
            config_path = create_design(designs_dir, platform, design_name)
        except OSError as exc:
            messagebox.showerror("Create failed", str(exc))
            return

        self.refresh()
        messagebox.showinfo(
            "Design created",
            f"Created designs/{platform}/{design_name}/\n\n"
            f"config.mk: {config_path.name}",
        )
        if self.on_select:
            self.on_select(config_path)

    def _add_template(self, template_type: str) -> None:
        target = self._context_target
        if not target or not target.is_dir():
            return

        module_name = simpledialog.askstring(
            "Module name",
            "Enter the design/module name:",
            initialvalue=target.name,
            parent=self,
        )
        if not module_name:
            return

        platform = target.parent.name if target.parent.name in PLATFORMS else "asap7"
        try:
            path = write_template_file(target, template_type, module_name, platform)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Template failed", str(exc))
            return

        self.refresh()
        messagebox.showinfo("File created", str(path))

    def _open_folder(self) -> None:
        path = filedialog.askdirectory(title="Select OpenROAD flow/ directory")
        if path:
            self.set_root(Path(path))


class _NewDesignDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.title("New Design")
        self.resizable(False, False)
        self.result: tuple[str, str] | None = None

        ttk.Label(self, text="Platform (PDK):").grid(row=0, column=0, padx=8, pady=8, sticky=tk.W)
        self.platform_var = tk.StringVar(value="asap7")
        platform_box = ttk.Combobox(
            self,
            textvariable=self.platform_var,
            values=PLATFORMS,
            state="readonly",
            width=24,
        )
        platform_box.grid(row=0, column=1, padx=8, pady=8)

        ttk.Label(self, text="Design name:").grid(row=1, column=0, padx=8, pady=8, sticky=tk.W)
        self.name_var = tk.StringVar(value="my_design")
        ttk.Entry(self, textvariable=self.name_var, width=26).grid(
            row=1, column=1, padx=8, pady=8
        )

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=8)
        ttk.Button(btn_frame, text="Create", command=self._on_create).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(
            side=tk.LEFT, padx=4
        )

        self.transient(master.winfo_toplevel())
        self.grab_set()

    def _on_create(self) -> None:
        platform = self.platform_var.get().strip()
        name = self.name_var.get().strip()
        if not platform or not name:
            messagebox.showwarning("Missing fields", "Platform and design name are required.")
            return
        if not name.replace("_", "").isalnum():
            messagebox.showwarning(
                "Invalid name",
                "Design name should contain only letters, numbers, and underscores.",
            )
            return
        self.result = (platform, name)
        self.destroy()
