"""Scrollable terminal/log viewer widget with interactive terminal (PTY-based)."""

from __future__ import annotations

import os
import pty
import queue
import select
import signal
import struct
import subprocess
import sys
import termios
import threading
import fcntl
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk
from typing import Optional


def _open_external_terminal(cwd: str) -> None:
    """Open system terminal at given directory."""
    try:
        if sys.platform == "darwin":
            # macOS: Terminal.app
            script = f'tell application "Terminal" to do script "cd {cwd} && clear"'
            subprocess.Popen(["osascript", "-e", script])
        elif sys.platform == "win32":
            # Windows: cmd or PowerShell
            subprocess.Popen(["cmd", "/k", f"cd /d {cwd}"])
        else:
            # Linux: try common terminals
            for term in ["gnome-terminal", "konsole", "xfce4-terminal", "xterm", "tilix", "alacritty", "kitty"]:
                try:
                    subprocess.Popen([term, "--working-directory", cwd])
                    break
                except FileNotFoundError:
                    continue
    except OSError as e:
        print(f"Failed to open terminal: {e}")


class TerminalWidget(ttk.Frame):
    """Interactive terminal emulator using a real PTY (like VS Code/PyCharm)."""

    def __init__(
        self,
        master: tk.Misc,
        shell: Optional[str] = None,
        cwd: Optional[str] = None,
        env: Optional[dict[str, str]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self.shell = shell or os.environ.get("SHELL", "/bin/bash")
        self.cwd = cwd or os.getcwd()
        self.env = env or os.environ.copy()
        self._fd: Optional[int] = None
        self._pid: Optional[int] = None
        self._running = False
        self.output_queue: "queue.Queue[tuple[str, str]]" = queue.Queue()
        self._build_ui()
        self._start_pty()

    def _build_ui(self) -> None:
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=4, pady=(4, 0))

        ttk.Label(toolbar, text="Terminal", font=("", 11, "bold")).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Clear", command=self.clear, width=8).pack(side=tk.RIGHT, padx=2)
        ttk.Button(toolbar, text="Restart", command=self.restart, width=8).pack(side=tk.RIGHT, padx=2)
        ttk.Button(toolbar, text="Open External Terminal", command=self._open_external, width=20).pack(side=tk.RIGHT, padx=2)

        self.text = scrolledtext.ScrolledText(
            self,
            wrap=tk.WORD,
            height=12,
            font=("Menlo", 11),
            state=tk.NORMAL,
            background="#1e1e1e",
            foreground="#d4d4d4",
            insertbackground="#d4d4d4",
        )
        self.text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Tags for colored output (for our own messages)
        self.text.tag_configure("stdout", foreground="#d4d4d4")
        self.text.tag_configure("stderr", foreground="#f48771")
        self.text.tag_configure("info", foreground="#4ec9b0")
        self.text.tag_configure("error", foreground="#ff6b6b", font=("Menlo", 11, "bold"))

        # Bind keys to send to PTY
        self.text.bind("<Key>", self._on_keypress)
        self.text.bind("<Return>", self._on_return)
        self.text.bind("<BackSpace>", self._on_backspace)
        self.text.bind("<Control-c>", self._on_ctrl_c)
        self.text.bind("<Control-d>", self._on_ctrl_d)
        self.text.bind("<Control-z>", self._on_ctrl_z)
        self.text.bind("<Up>", self._on_up)
        self.text.bind("<Down>", self._on_down)
        self.text.bind("<Left>", self._on_left)
        self.text.bind("<Right>", self._on_right)
        self.text.bind("<Home>", self._on_home)
        self.text.bind("<End>", self._on_end)
        self.text.focus_set()

    def _open_external(self) -> None:
        _open_external_terminal(self.cwd)

    def _start_pty(self) -> None:
        """Spawn shell in a real PTY."""
        self._stop_pty()

        try:
            # Fork with PTY
            pid, fd = pty.fork()
            if pid == 0:
                # Child process
                try:
                    os.chdir(self.cwd)
                except OSError:
                    pass
                os.execvpe(self.shell, [self.shell], self.env)
                os._exit(1)
            else:
                # Parent process
                self._pid = pid
                self._fd = fd
                self._running = True
                # Make FD non-blocking
                import fcntl
                flags = fcntl.fcntl(fd, fcntl.F_GETFL)
                fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
                # Start reader thread
                threading.Thread(target=self._read_loop, daemon=True).start()
                # Handle window size
                self._update_winsize()
                self.text.bind("<Configure>", lambda e: self._update_winsize())
                # Debug
                self._append(f"[Terminal started: shell={self.shell}, pid={pid}]\n", "info")
        except OSError as e:
            self._append(f"[Failed to start PTY: {e}]\n", "error")

    def _stop_pty(self) -> None:
        self._running = False
        if self._pid is not None:
            try:
                os.kill(self._pid, signal.SIGTERM)
            except OSError:
                pass
            self._pid = None
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None

    def _update_winsize(self) -> None:
        """Send terminal window size to PTY (for proper line wrapping)."""
        if self._fd is None:
            return
        try:
            self.text.update_idletasks()
            cols = max(1, self.text.winfo_width() // 8)
            rows = max(1, self.text.winfo_height() // 18)
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self._fd, termios.TIOCSWINSZ, winsize)
        except Exception:
            pass

    def _read_loop(self) -> None:
        """Read from PTY and queue output for UI thread."""
        while self._running and self._fd is not None:
            try:
                r, _, _ = select.select([self._fd], [], [], 0.1)
                if not r:
                    continue
                data = os.read(self._fd, 4096)
                if not data:
                    break
                # Decode as UTF-8, replace errors
                text = data.decode("utf-8", errors="replace")
                self.output_queue.put(("stdout", text))
            except OSError:
                break
            except Exception as e:
                self.output_queue.put(("error", f"[Read error: {e}]\n"))
                break
        if self._running:
            self.output_queue.put(("info", "\n[Shell exited]\n"))
        self._running = False

    def _drain_queue(self) -> None:
        """Periodically called to flush queue to text widget."""
        try:
            while True:
                tag, text = self.output_queue.get_nowait()
                if tag == "stdout":
                    self._append_raw(text)
                else:
                    self._append(text, tag)
        except queue.Empty:
            pass
        if self._running or not self.output_queue.empty():
            self.after(30, self._drain_queue)

    def _append_raw(self, text: str) -> None:
        """Append raw text from PTY (includes ANSI escapes — we strip or render)."""
        self.text.configure(state=tk.NORMAL)
        self.text.insert(tk.END, text)
        self.text.see(tk.END)
        self.text.configure(state=tk.NORMAL)

    def _append(self, text: str, tag: str = "stdout") -> None:
        """Append our own message with tag."""
        self.text.configure(state=tk.NORMAL)
        self.text.insert(tk.END, text, tag)
        self.text.see(tk.END)
        self.text.configure(state=tk.NORMAL)

    # --- Key handlers: send raw bytes to PTY ---
    def _send(self, data: bytes) -> None:
        if self._fd is not None and self._running:
            try:
                os.write(self._fd, data)
            except OSError:
                pass

    def _on_keypress(self, event: tk.Event) -> str:
        # Printable characters
        if len(event.char) == 1 and event.char.isprintable():
            self._send(event.char.encode())
            return "break"
        return ""

    def _on_return(self, _event: tk.Event) -> str:
        self._send(b"\r")
        return "break"

    def _on_backspace(self, _event: tk.Event) -> str:
        self._send(b"\x7f")  # DEL
        return "break"

    def _on_ctrl_c(self, _event: tk.Event) -> str:
        if self._pid:
            try:
                os.kill(self._pid, signal.SIGINT)
            except OSError:
                pass
        return "break"

    def _on_ctrl_d(self, _event: tk.Event) -> str:
        self._send(b"\x04")  # EOF
        return "break"

    def _on_ctrl_z(self, _event: tk.Event) -> str:
        if self._pid:
            try:
                os.kill(self._pid, signal.SIGTSTP)
            except OSError:
                pass
        return "break"

    def _on_up(self, _event: tk.Event) -> str:
        self._send(b"\x1b[A")
        return "break"

    def _on_down(self, _event: tk.Event) -> str:
        self._send(b"\x1b[B")
        return "break"

    def _on_left(self, _event: tk.Event) -> str:
        self._send(b"\x1b[D")
        return "break"

    def _on_right(self, _event: tk.Event) -> str:
        self._send(b"\x1b[C")
        return "break"

    def _on_home(self, _event: tk.Event) -> str:
        self._send(b"\x1b[H")
        return "break"

    def _on_end(self, _event: tk.Event) -> str:
        self._send(b"\x1b[F")
        return "break"

    def clear(self) -> None:
        self.text.configure(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.configure(state=tk.NORMAL)
        # Send clear screen sequence to shell
        self._send(b"\x1b[2J\x1b[H")

    def restart(self) -> None:
        self._stop_pty()
        self.clear()
        self._start_pty()

    def destroy(self) -> None:
        self._stop_pty()
        super().destroy()


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

        # Notebook for tabs: Flow Log | Terminal
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # --- Flow Log tab ---
        self.log_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.log_frame, text="Flow Log")

        self.text = scrolledtext.ScrolledText(
            self.log_frame,
            wrap=tk.WORD,
            height=12,
            font=("Menlo", 11),
            state=tk.DISABLED,
            background="#1e1e1e",
            foreground="#d4d4d4",
            insertbackground="#d4d4d4",
        )
        self.text.pack(fill=tk.BOTH, expand=True)

        self.text.tag_configure("stdout", foreground="#d4d4d4")
        self.text.tag_configure("stderr", foreground="#f48771")
        self.text.tag_configure("info", foreground="#4ec9b0")
        self.text.tag_configure("error", foreground="#ff6b6b", font=("Menlo", 11, "bold"))

        # --- Terminal tab ---
        self.terminal = TerminalWidget(self.notebook)
        self.notebook.add(self.terminal, text="Terminal")

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