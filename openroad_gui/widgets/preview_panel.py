"""Unified file preview with text and GDS image modes."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext, ttk


class PreviewPanel(ttk.LabelFrame):
    def __init__(self, master: tk.Misc, **kwargs) -> None:
        super().__init__(master, text="File Preview", padding=4, **kwargs)
        self._photo: tk.PhotoImage | None = None
        self._current_path: Path | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.text_tab = ttk.Frame(self.notebook)
        self.image_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.text_tab, text="Text")
        self.notebook.add(self.image_tab, text="Layout")

        self.text = scrolledtext.ScrolledText(
            self.text_tab,
            wrap=tk.NONE,
            font=("Menlo", 11),
            state=tk.DISABLED,
        )
        self.text.pack(fill=tk.BOTH, expand=True)

        self.image_canvas = tk.Canvas(self.image_tab, background="#2b2b2b", highlightthickness=0)
        image_vsb = ttk.Scrollbar(self.image_tab, orient=tk.VERTICAL, command=self.image_canvas.yview)
        image_hsb = ttk.Scrollbar(self.image_tab, orient=tk.HORIZONTAL, command=self.image_canvas.xview)
        self.image_canvas.configure(xscrollcommand=image_hsb.set, yscrollcommand=image_vsb.set)

        image_vsb.pack(side=tk.RIGHT, fill=tk.Y)
        image_hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.image_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.image_label = ttk.Label(self.image_canvas, text="No layout preview")
        self.image_window = self.image_canvas.create_window(0, 0, anchor=tk.NW, window=self.image_label)

        self.image_label.bind("<Configure>", self._on_image_configure)

        self.actions = ttk.Frame(self)
        self.actions.pack(fill=tk.X, pady=(4, 0))

    def add_action(self, text: str, command) -> None:
        ttk.Button(self.actions, text=text, command=command).pack(side=tk.LEFT, padx=(0, 8))

    @property
    def current_path(self) -> Path | None:
        return self._current_path

    def show_text(self, path: Path | None, content: str) -> None:
        self._current_path = path
        self.notebook.select(self.text_tab)
        self.text.configure(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", content)
        self.text.configure(state=tk.DISABLED)

    def show_image(self, path: Path, png_path: Path, caption: str = "") -> None:
        self._current_path = path
        self.notebook.select(self.image_tab)
        self._photo = tk.PhotoImage(file=str(png_path))
        self.image_label.configure(image=self._photo, text="")
        if caption:
            self.configure(text=f"File Preview — {caption}")

    def show_image_error(self, path: Path, message: str) -> None:
        self._current_path = path
        self.notebook.select(self.image_tab)
        self._photo = None
        self.image_label.configure(image="", text=message)
        self.configure(text="File Preview — Layout")

    def clear_image(self) -> None:
        self._photo = None
        self.image_label.configure(image="", text="No layout preview")

    def _on_image_configure(self, _event: tk.Event) -> None:
        self.image_canvas.configure(scrollregion=self.image_canvas.bbox(tk.ALL))
