"""Sidebar with Task Assistant and Resource Monitor."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from openroad_gui.theme import (ACCENT_BLUE, ACCENT_GREEN, ACCENT_RED,
                                BG_DARK, BG_ELEVATED, BG_PANEL, BORDER,
                                FG_PRIMARY, FG_SECONDARY)
from openroad_gui.widgets.log_viewer import LogViewer


class TaskAssistant(ttk.Frame):
    """Scrollable list of warnings/errors from the flow log."""

    def __init__(self, master: tk.Misc, log_viewer: LogViewer, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.log_viewer = log_viewer
        self._entries: list[dict] = []
        self._build_ui()

    def _build_ui(self) -> None:
        # Header
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=8, pady=(8, 4))
        ttk.Label(header, text="Task Assistant", font=("", 11, "bold")).pack(side=tk.LEFT)
        ttk.Button(header, text="Clear", command=self.clear, width=8).pack(side=tk.RIGHT)

        # Treeview for entries
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        self.tree = ttk.Treeview(
            tree_frame,
            columns=("severity", "message"),
            show="headings",
            selectmode="browse",
            height=12,
        )
        self.tree.heading("severity", text="")
        self.tree.heading("message", text="Message")
        self.tree.column("severity", width=30, minwidth=30, anchor=tk.CENTER)
        self.tree.column("message", width=240, minwidth=150)

        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # Tags for coloring
        self.tree.tag_configure("warning", foreground="#d29922")
        self.tree.tag_configure("error", foreground="#f85149")
        self.tree.tag_configure("info", foreground="#58a6ff")

    def add_entry(self, severity: str, message: str) -> None:
        """Add a warning/error entry."""
        import time
        timestamp = time.strftime("%H:%M:%S")
        entry = {"severity": severity, "message": message, "time": timestamp}
        self._entries.append(entry)

        # Add to tree
        tag = severity.lower()
        if tag not in ("warning", "error", "info"):
            tag = "info"

        self.tree.insert("", tk.END, values=(severity[0].upper(), message), tags=(tag,))

        # Auto-scroll to bottom
        children = self.tree.get_children()
        if children:
            self.tree.see(children[-1])

    def clear(self) -> None:
        """Clear all entries."""
        self._entries.clear()
        self.tree.delete(*self.tree.get_children())


class ResourceMonitor(ttk.Frame):
    """Live CPU, Memory, and Disk usage sparklines."""

    def __init__(self, master: tk.Misc, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self._cpu_data: list[float] = []
        self._mem_data: list[float] = []
        self._disk_data: list[float] = []
        self._max_points = 60
        self._running = False
        self._psutil_available = False
        self._build_ui()
        self._try_import_psutil()

    def _build_ui(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=8, pady=(8, 4))
        ttk.Label(header, text="Resource Monitor", font=("", 11, "bold")).pack(side=tk.LEFT)

        # CPU
        self.cpu_frame = self._create_metric_row("CPU", "#58a6ff")
        self.cpu_frame.pack(fill=tk.X, padx=8, pady=4)

        # Memory
        self.mem_frame = self._create_metric_row("MEM", "#3fb950")
        self.mem_frame.pack(fill=tk.X, padx=8, pady=4)

        # Disk
        self.disk_frame = self._create_metric_row("DSK", "#d29922")
        self.disk_frame.pack(fill=tk.X, padx=8, pady=(4, 8))

    def _create_metric_row(self, label: str, color: str) -> ttk.Frame:
        frame = ttk.Frame(self)
        ttk.Label(frame, text=label, width=4, font=("", 9, "bold")).pack(side=tk.LEFT)
        canvas = tk.Canvas(frame, height=30, background=BG_PANEL, highlightthickness=0)
        canvas.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))
        value_label = ttk.Label(frame, text="0%", width=5, font=("", 9, "bold"))
        value_label.pack(side=tk.LEFT, padx=(8, 0))
        return frame

    def _try_import_psutil(self) -> None:
        try:
            import psutil
            self._psutil = psutil
            self._psutil_available = True
        except ImportError:
            self._psutil_available = False
            # Show placeholder message
            self._show_placeholder()

    def _show_placeholder(self) -> None:
        for frame in (self.cpu_frame, self.mem_frame, self.disk_frame):
            canvas = frame.winfo_children()[1]  # The canvas
            canvas.create_text(100, 15, text="psutil not installed\n# TODO: wire to real system stats",
                              fill=FG_SECONDARY, font=("TkDefaultFont", 8), anchor=tk.CENTER)

    def start(self) -> None:
        """Start monitoring."""
        if self._running:
            return
        if not self._psutil_available:
            return
        self._running = True
        self._update_loop()

    def stop(self) -> None:
        """Stop monitoring."""
        self._running = False

    def _update_loop(self) -> None:
        if not self._running:
            return

        try:
            # CPU
            cpu = self._psutil.cpu_percent(interval=None)
            self._cpu_data.append(cpu)
            if len(self._cpu_data) > self._max_points:
                self._cpu_data.pop(0)

            # Memory
            mem = self._psutil.virtual_memory()
            mem_pct = mem.percent
            self._mem_data.append(mem_pct)
            if len(self._mem_data) > self._max_points:
                self._mem_data.pop(0)

            # Disk I/O
            io = self._psutil.disk_io_counters()
            if io:
                disk = (io.read_bytes + io.write_bytes) / (1024 * 1024)  # MB
                self._disk_data.append(disk)
                if len(self._disk_data) > self._max_points:
                    self._disk_data.pop(0)

            self._draw_sparklines()
            self._update_labels()
        except Exception:
            pass

        self.after(2000, self._update_loop)

    def _draw_sparklines(self) -> None:
        for data, frame, color in [
            (self._cpu_data, self.cpu_frame, "#58a6ff"),
            (self._mem_data, self.mem_frame, "#3fb950"),
            (self._disk_data, self.disk_frame, "#d29922"),
        ]:
            canvas = frame.winfo_children()[1]  # Canvas is second child
            canvas.delete("all")
            w = canvas.winfo_width() or 200
            h = canvas.winfo_height() or 30
            if len(data) < 2:
                continue

            # Draw line
            points = []
            for i, val in enumerate(data):
                x = (i / (len(data) - 1)) * w
                y = h - (val / 100.0) * (h - 4) - 2
                points.extend([x, y])
            canvas.create_line(points, fill=color, width=2, smooth=True, splinesteps=12)

            # Fill under line
            fill_points = points + [w, h, 0, h]
            canvas.create_polygon(fill_points, fill=color, stipple="gray25", outline="")

    def _update_labels(self) -> None:
        if self._cpu_data:
            self.cpu_frame.winfo_children()[2].configure(text=f"{self._cpu_data[-1]:.0f}%")
        if self._mem_data:
            self.mem_frame.winfo_children()[2].configure(text=f"{self._mem_data[-1]:.0f}%")
        if self._disk_data:
            self.disk_frame.winfo_children()[2].configure(text=f"{self._disk_data[-1]:.1f}MB/s")


class Sidebar(ttk.Frame):
    """Right sidebar containing Task Assistant and Resource Monitor."""

    def __init__(self, master: tk.Misc, log_viewer: LogViewer, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.log_viewer = log_viewer
        self._build_ui()
        self._hook_log_viewer()
        # Start monitoring after a short delay to ensure UI is ready
        self.after(500, self.resource_monitor.start)

    def _build_ui(self) -> None:
        self.configure(style="Sidebar.TFrame")

        # Task Assistant (top, expands)
        self.task_assistant = TaskAssistant(self, self.log_viewer)
        self.task_assistant.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        # Separator
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=4)

        # Resource Monitor (bottom, fixed height)
        self.resource_monitor = ResourceMonitor(self)
        self.resource_monitor.pack(fill=tk.X, pady=(0, 8))

    def _hook_log_viewer(self) -> None:
        """Monkey-patch log_viewer to capture warnings/errors."""
        original_append = self.log_viewer.append
        original_log_error = self.log_viewer.log_error

        def hooked_append(stream: str, line: str) -> None:
            original_append(stream, line)
            # Filter for warnings/errors
            lower = line.lower()
            if "warning" in lower or "warn:" in lower:
                self.task_assistant.add_entry("Warning", line.strip())
            elif "error" in lower or "fail" in lower:
                self.task_assistant.add_entry("Error", line.strip())

        def hooked_log_error(message: str) -> None:
            original_log_error(message)
            self.task_assistant.add_entry("Error", message.strip())

        self.log_viewer.append = hooked_append
        self.log_viewer.log_error = hooked_log_error

    def start_monitoring(self) -> None:
        self.resource_monitor.start()

    def stop_monitoring(self) -> None:
        self.resource_monitor.stop()