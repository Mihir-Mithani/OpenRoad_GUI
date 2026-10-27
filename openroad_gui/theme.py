"""Centralized theme system for OpenROAD Flow GUI with Light/Dark mode support."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
import sys


class ThemeManager:
    """Centralized theme manager with Light/Dark mode support."""

    # Dark mode colors (matching gui_update.md specification)
    DARK = {
        "BG_APP": "#0A1320",
        "BG_HEADER": "#0B1524",
        "BG_SIDEBAR": "#0D1928",
        "BG_PANEL": "#101C2B",
        "BG_ELEVATED": "#142337",
        "BG_INPUT": "#0C1726",
        "BORDER": "#26384F",
        "FG_PRIMARY": "#F0F5FF",
        "FG_SECONDARY": "#A7B7CD",
        "FG_DISABLED": "#6B7B8D",
        "ACCENT_BLUE": "#2D7DFF",
        "ACCENT_BLUE_HOVER": "#4DA3FF",
        "ACCENT_GREEN": "#39D785",
        "ACCENT_GREEN_HOVER": "#56E096",
        "ACCENT_AMBER": "#FFC857",
        "ACCENT_RED": "#FF667A",
        "ACCENT_RED_HOVER": "#FF8A8A",
        "ACCENT_PURPLE": "#C084FC",
        "ACCENT_BLUE_HOVER": "#4DA3FF",
        "ACCENT_GREEN_HOVER": "#56E096",
        "ACCENT_RED_HOVER": "#FF8A8A",
        "ACCENT_AMBER": "#FFC857",
        "SELECTION_BG": "#264F78",
        "SELECTION_FG": "#FFFFFF",
        "LOG_BG": "#050B13",
    }

    # Light mode colors (professional light theme)
    LIGHT = {
        "BG_APP": "#F5F7FA",
        "BG_HEADER": "#FFFFFF",
        "BG_SIDEBAR": "#F0F2F5",
        "BG_PANEL": "#FFFFFF",
        "BG_ELEVATED": "#F5F7FA",
        "BG_INPUT": "#FFFFFF",
        "BORDER": "#D0D5DD",
        "FG_PRIMARY": "#1D2939",
        "FG_SECONDARY": "#667085",
        "FG_DISABLED": "#98A2B3",
        "ACCENT_BLUE": "#1E6FEF",
        "ACCENT_BLUE_HOVER": "#3B82F6",
        "ACCENT_GREEN": "#12B76A",
        "ACCENT_GREEN_HOVER": "#22C55E",
        "ACCENT_AMBER": "#F59E0B",
        "ACCENT_RED": "#EF4444",
        "ACCENT_RED_HOVER": "#F87171",
        "ACCENT_PURPLE": "#A855F7",
        "ACCENT_BLUE_HOVER": "#3B82F6",
        "ACCENT_GREEN_HOVER": "#34D399",
        "ACCENT_RED_HOVER": "#FCA5A5",
        "ACCENT_AMBER": "#F59E0B",
        "SELECTION_BG": "#E0E7FF",
        "SELECTION_FG": "#1E1E1E",
        "LOG_BG": "#F5F7FA",
        "BORDER": "#D0D5DD",
        "FG_PRIMARY": "#1D2939",
        "FG_SECONDARY": "#667085",
        "FG_DISABLED": "#98A2B3",
        "ACCENT_BLUE_HOVER": "#3B82F6",
        "ACCENT_GREEN_HOVER": "#34D399",
        "ACCENT_RED_HOVER": "#FCA5A5",
        "ACCENT_AMBER": "#F59E0B",
        "SELECTION_BG": "#E0E7FF",
        "SELECTION_FG": "#1E1E1E",
        "LOG_BG": "#FFFFFF",
        "BG_APP": "#F5F7FA",
        "BG_HEADER": "#FFFFFF",
        "BG_SIDEBAR": "#F0F2F5",
        "BG_PANEL": "#FFFFFF",
        "BG_ELEVATED": "#F5F7FA",
        "BG_INPUT": "#FFFFFF",
        "BORDER": "#D0D5DD",
    }

    # Font configuration
    DEFAULT_FONT_FAMILY = "TkDefaultFont"
    MONO_FONT_FAMILY = "Menlo" if sys.platform == "darwin" else "Monospace"

    def __init__(self, root: tk.Tk):
        self.root = root
        self._dark_mode = True  # Default to dark mode
        self.style = ttk.Style(root)
        self._init_themes()
        self._apply_theme()

    def _init_themes(self):
        """Initialize both light and dark theme configurations."""
        # Dark theme config
        self._dark_theme = self.DARK.copy()
        self._dark_theme.update({
            "DEFAULT_FONT_FAMILY": "TkDefaultFont",
            "MONO_FONT_FAMILY": "Menlo" if sys.platform == "darwin" else "Monospace",
        })

        # Light theme config
        self._light_theme = self.LIGHT.copy()
        self._light_theme.update({
            "DEFAULT_FONT_FAMILY": "TkDefaultFont",
            "MONO_FONT_FAMILY": "Menlo" if sys.platform == "darwin" else "Monospace",
        })

    def _get_current_theme(self) -> dict:
        """Get current theme dictionary."""
        return self._dark_theme if self._dark_mode else self._light_theme

    def toggle_theme(self) -> None:
        """Toggle between light and dark mode."""
        self._dark_mode = not self._dark_mode
        self._apply_theme()

    def set_dark_mode(self, dark: bool = True):
        """Set theme mode explicitly."""
        if self._dark_mode != dark:
            self._dark_mode = dark
            self._apply_theme()

    def is_dark_mode(self) -> bool:
        return self._dark_mode

    def _apply_theme(self):
        """Apply current theme to all widgets."""
        theme = self._get_current_theme()

        # Configure ttk Style
        style = ttk.Style(self.root)

        # Use 'clam' as base for maximum customizability
        if "clam" in style.theme_names():
            style.theme_use("clam")

        t = theme  # shorthand

        # Configure root window background
        try:
            self.root.configure(background=t["BG_APP"])
        except tk.TclError:
            pass

        # ===== Core widget styles =====

        # Frame / LabelFrame
        style.configure("TFrame", background=t["BG_APP"])
        style.configure("TLabelframe",
                       background=t["BG_APP"],
                       bordercolor=t["BORDER"],
                       lightcolor=t["BORDER"],
                       darkcolor=t["BORDER"])
        style.configure("TLabelframe.Label",
                       background=t["BG_APP"],
                       foreground=t["FG_PRIMARY"],
                       font=("TkDefaultFont", 10, "bold"))

        # Label
        style.configure("TLabel", background=t["BG_APP"], foreground=t["FG_PRIMARY"])
        style.configure("Secondary.TLabel", background=t["BG_APP"], foreground=t["FG_SECONDARY"])
        style.configure("Bold.TLabel", background=t["BG_APP"], foreground=t["FG_PRIMARY"], font=("TkDefaultFont", 10, "bold"))
        style.configure("Title.TLabel", background=t["BG_APP"], foreground=t["FG_PRIMARY"], font=("TkDefaultFont", 11, "bold"))
        style.configure("Status.Ready.TLabel", background=t["BG_APP"], foreground=t["ACCENT_GREEN"])
        style.configure("Status.Running.TLabel", background=t["BG_APP"], foreground=t["ACCENT_BLUE"])
        style.configure("Status.Error.TLabel", background=t["BG_APP"], foreground=t["ACCENT_RED"])

        # Button
        style.configure("TButton",
                        background=t["BG_ELEVATED"],
                        foreground=t["FG_PRIMARY"],
                        bordercolor=t["BORDER"],
                        lightcolor=t["BG_ELEVATED"],
                        darkcolor=t["BG_ELEVATED"],
                        focuscolor=t["ACCENT_BLUE"],
                        padding=(12, 6),
                        font=("TkDefaultFont", 9))
        style.map("TButton",
                  background=[("active", t["BG_ELEVATED"]), ("pressed", t["ACCENT_BLUE"]), ("disabled", t["BG_ELEVATED"])],
                  foreground=[("disabled", t["FG_DISABLED"])],
                  bordercolor=[("focus", t["ACCENT_BLUE"])])

        # Primary action button (Run Full Pipeline)
        style.configure("Primary.TButton",
                        background=t["ACCENT_BLUE"],
                        foreground="#ffffff",
                        bordercolor=t["ACCENT_BLUE"],
                        padding=(16, 8),
                        font=("TkDefaultFont", 10, "bold"))
        style.map("Primary.TButton",
                  background=[("active", t["ACCENT_BLUE_HOVER"]), ("pressed", "#1E5FD6"), ("disabled", t["BG_ELEVATED"])],
                  foreground=[("disabled", t["FG_DISABLED"])])

        # Stop button (destructive)
        style.configure("Danger.TButton",
                        background=t["ACCENT_RED"],
                        foreground="#ffffff",
                        bordercolor=t["ACCENT_RED"],
                        padding=(12, 6),
                        font=("TkDefaultFont", 9, "bold"))
        style.map("Danger.TButton",
                  background=[("active", t["ACCENT_RED_HOVER"]), ("pressed", "#DC2626"), ("disabled", t["BG_ELEVATED"])],
                  foreground=[("disabled", t["FG_DISABLED"])])

        # Small secondary buttons
        style.configure("Secondary.TButton",
                        background=t["BG_ELEVATED"],
                        foreground=t["FG_SECONDARY"],
                        bordercolor=t["BORDER"],
                        padding=(8, 4),
                        font=("TkDefaultFont", 8))
        style.map("Secondary.TButton",
                  background=[("active", t["BG_HOVER"]), ("disabled", t["BG_ELEVATED"])],
                  foreground=[("active", t["FG_PRIMARY"]), ("disabled", t["FG_DISABLED"])])

        # Toolbar/flat button (for header actions)
        style.configure("Flat.TButton",
                        background=t["BG_APP"],
                        foreground=t["FG_PRIMARY"],
                        bordercolor=t["BORDER"],
                        padding=(10, 5),
                        font=("TkDefaultFont", 9))
        style.map("Flat.TButton",
                  background=[("active", t["BG_ELEVATED"]), ("disabled", t["BG_APP"])],
                  foreground=[("disabled", t["FG_DISABLED"])])

        # Entry
        style.configure("TEntry",
                        fieldbackground=t["BG_INPUT"],
                        foreground=t["FG_PRIMARY"],
                        bordercolor=t["BORDER"],
                        lightcolor=t["BORDER"],
                        darkcolor=t["BORDER"],
                        insertcolor=t["FG_PRIMARY"],
                        padding=(8, 6))
        style.map("TEntry",
                  bordercolor=[("focus", t["ACCENT_BLUE"])],
                  fieldbackground=[("disabled", t["BG_ELEVATED"])])

        # Combobox
        style.configure("TCombobox",
                        fieldbackground=t["BG_ELEVATED"],
                        foreground=t["FG_PRIMARY"],
                        bordercolor=t["BORDER"],
                        arrowcolor=t["FG_PRIMARY"],
                        padding=(8, 4))
        style.map("TCombobox",
                  bordercolor=[("focus", t["ACCENT_BLUE"])],
                  fieldbackground=[("readonly", t["BG_ELEVATED"]), ("disabled", t["BG_ELEVATED"])],
                  foreground=[("disabled", t["FG_DISABLED"])])

        # Notebook (tabs)
        style.configure("TNotebook", background=t["BG_APP"], borderwidth=0, tabmargins=(0, 0, 0, 0))
        style.configure("TNotebook.Tab",
                        background=t["BG_ELEVATED"],
                        foreground=t["FG_SECONDARY"],
                        bordercolor=t["BORDER"],
                        lightcolor=t["BG_ELEVATED"],
                        darkcolor=t["BG_ELEVATED"],
                        padding=(16, 8),
                        font=("TkDefaultFont", 9))
        style.map("TNotebook.Tab",
                  background=[("selected", t["BG_PANEL"]), ("active", t["BG_ELEVATED"])],
                  foreground=[("selected", t["FG_PRIMARY"]), ("active", t["FG_PRIMARY"])],
                  bordercolor=[("selected", t["ACCENT_BLUE"])])

        # Treeview (project tree)
        style.configure("Treeview",
                        background=t["BG_PANEL"],
                        foreground=t["FG_PRIMARY"],
                        fieldbackground=t["BG_PANEL"],
                        bordercolor=t["BORDER"],
                        rowheight=24,
                        font=("TkDefaultFont", 10))
        style.configure("Treeview.Heading",
                        background=t["BG_ELEVATED"],
                        foreground=t["FG_PRIMARY"],
                        bordercolor=t["BORDER"],
                        font=("TkDefaultFont", 10, "bold"))
        style.map("Treeview",
                  background=[("selected", t["SELECTION_BG"])],
                  foreground=[("selected", t["SELECTION_FG"])])

        # Progressbar
        style.configure("TProgressbar",
                        background=t["ACCENT_BLUE"],
                        troughcolor=t["BG_ELEVATED"],
                        bordercolor=t["BORDER"],
                        lightcolor=t["ACCENT_BLUE"],
                        darkcolor=t["ACCENT_BLUE"],
                        thickness=6)

        # Progressbar variants
        style.configure("Success.TProgressbar", background=t["ACCENT_GREEN"], lightcolor=t["ACCENT_GREEN"], darkcolor=t["ACCENT_GREEN"])
        style.configure("Warning.TProgressbar", background=t["ACCENT_AMBER"], lightcolor=t["ACCENT_AMBER"], darkcolor=t["ACCENT_AMBER"])
        style.configure("Error.TProgressbar", background=t["ACCENT_RED"], lightcolor=t["ACCENT_RED"], darkcolor=t["ACCENT_RED"])

        # Scrollbar
        style.configure("Vertical.TScrollbar",
                        background=t["BG_ELEVATED"],
                        troughcolor=t["BG_APP"],
                        bordercolor=t["BORDER"],
                        arrowcolor=t["FG_SECONDARY"],
                        gripcount=0)
        style.map("Vertical.TScrollbar",
                  background=[("active", t["BG_HOVER"] if "BG_HOVER" in theme else t["BG_ELEVATED"])],
                  arrowcolor=[("active", t["FG_PRIMARY"])])

        style.configure("Horizontal.TScrollbar",
                        background=t["BG_ELEVATED"],
                        troughcolor=t["BG_APP"],
                        bordercolor=t["BORDER"],
                        arrowcolor=t["FG_SECONDARY"],
                        gripcount=0)
        style.map("Horizontal.TScrollbar",
                  background=[("active", t["BG_HOVER"] if "BG_HOVER" in theme else t["BG_ELEVATED"])],
                  arrowcolor=[("active", t["FG_PRIMARY"])])

        # Separator
        style.configure("TSeparator", background=t["BORDER"])

        # Checkbutton / Radiobutton
        style.configure("TCheckbutton", background=t["BG_APP"], foreground=t["FG_PRIMARY"], focuscolor=t["ACCENT_BLUE"])
        style.map("TCheckbutton",
                  background=[("active", t["BG_APP"])],
                  foreground=[("disabled", t["FG_DISABLED"])])
        style.configure("TRadiobutton", background=t["BG_APP"], foreground=t["FG_PRIMARY"], focuscolor=t["ACCENT_BLUE"])
        style.map("TRadiobutton",
                  background=[("active", t["BG_APP"])],
                  foreground=[("disabled", t["FG_DISABLED"])])

        # Scale (slider)
        style.configure("TScale", background=t["BG_APP"], troughcolor=t["BG_ELEVATED"], bordercolor=t["BORDER"])

        # PanedWindow
        style.configure("TPanedwindow", background=t["BG_APP"])
        style.configure("Sash", background=t["BG_ELEVATED"], bordercolor=t["BORDER"])

        # Menubutton (for dropdown menus)
        style.configure("TMenubutton",
                        background=t["BG_ELEVATED"],
                        foreground=t["FG_PRIMARY"],
                        bordercolor=t["BORDER"],
                        padding=(10, 5),
                        font=("TkDefaultFont", 9))
        style.map("TMenubutton",
                  background=[("active", t["BG_HOVER"] if "BG_HOVER" in theme else t["BG_ELEVATED"]), ("disabled", t["BG_ELEVATED"])],
                  foreground=[("disabled", t["FG_DISABLED"])])

        # Sizegrip
        style.configure("TSizegrip", background=t["BG_APP"], bordercolor=t["BORDER"])

        # Apply theme to tk widgets
        self._apply_theme_to_tk_widgets(self.root)

    def _apply_theme_to_tk_widgets(self, widget: tk.Misc) -> None:
        """Recursively apply theme to raw tk widgets."""
        theme = self._get_current_theme()

        if isinstance(widget, (tk.Canvas, tk.Text, tk.Listbox, tk.Scrollbar)):
            try:
                is_text_or_canvas = isinstance(widget, (tk.Canvas, tk.Text))
                widget.configure(
                    background=theme["BG_PANEL"] if is_text_or_canvas else theme["BG_APP"],
                    foreground=theme["FG_PRIMARY"],
                    insertbackground=theme["FG_PRIMARY"],
                    selectbackground=theme["SELECTION_BG"],
                    selectforeground=theme["SELECTION_FG"],
                    highlightthickness=0,
                    borderwidth=0,
                )
                if isinstance(widget, tk.Scrollbar):
                    widget.configure(
                        background=theme["BG_ELEVATED"],
                        troughcolor=theme["BG_APP"],
                        activebackground=theme["BG_HOVER"] if "BG_HOVER" in theme else theme["BG_ELEVATED"],
                        borderwidth=0,
                    )
            except tk.TclError:
                pass

        # Recurse into children
        try:
            for child in widget.winfo_children():
                self._apply_theme_to_tk_widgets(child)
        except tk.TclError:
            pass

    def get_colors(self) -> dict:
        """Get current theme colors for custom widgets."""
        return self._get_current_theme()


# Global theme manager instance (initialized in app.py)
_theme_manager: "ThemeManager | None" = None


def init_theme(root: tk.Tk) -> "ThemeManager":
    """Initialize global theme manager."""
    global _theme_manager
    _theme_manager = ThemeManager(root)
    return _theme_manager


def get_theme_manager() -> "ThemeManager":
    """Get global theme manager instance."""
    global _theme_manager
    if _theme_manager is None:
        raise RuntimeError("ThemeManager not initialized. Call init_theme(root) first.")
    return _theme_manager


def toggle_theme():
    """Toggle between light and dark mode."""
    if _theme_manager:
        _theme_manager.toggle_theme()


def set_dark_mode(dark: bool = True):
    """Set theme mode explicitly."""
    if _theme_manager:
        _theme_manager.set_dark_mode(dark)