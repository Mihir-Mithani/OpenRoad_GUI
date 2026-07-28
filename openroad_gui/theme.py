"""Centralized dark theme for OpenROAD Flow GUI."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


# Color palette
BG_DARK = "#0d1117"          # Main background
BG_PANEL = "#161b22"         # Panel/frame background
BG_ELEVATED = "#21262d"      # Elevated surfaces (buttons, inputs)
BG_HOVER = "#30363d"         # Hover state
BORDER = "#30363d"           # Borders
FG_PRIMARY = "#e6edf3"       # Primary text
FG_SECONDARY = "#8b949e"     # Secondary/muted text
FG_DISABLED = "#484f58"      # Disabled text
ACCENT_BLUE = "#3b82f6"      # Primary accent (running, active)
ACCENT_BLUE_HOVER = "#60a5fa"
ACCENT_GREEN = "#3fb950"     # Success, completed
ACCENT_GREEN_HOVER = "#56d364"
ACCENT_AMBER = "#d29922"     # Warning, pending
ACCENT_RED = "#f85149"       # Error, failed
ACCENT_RED_HOVER = "#ff7b72"
ACCENT_PURPLE = "#a371f7"    # Special actions
SELECTION_BG = "#264f78"     # Tree/list selection
SELECTION_FG = "#ffffff"

# Font
DEFAULT_FONT_FAMILY = "TkDefaultFont"
MONO_FONT_FAMILY = "Menlo" if "darwin" in __import__("sys").platform else "Monospace"


def setup_dark_theme(root: tk.Misc) -> ttk.Style:
    """Configure and apply the dark theme to the application.

    Args:
        root: The root Tk widget

    Returns:
        The configured ttk.Style instance
    """
    style = ttk.Style(root)

    # Use 'clam' as base for maximum customizability
    available_themes = style.theme_names()
    if "clam" in available_themes:
        style.theme_use("clam")

    # Configure root window background
    try:
        root.configure(background=BG_DARK)
    except tk.TclError:
        pass  # Some widgets don't support background config

    # ===== Core widget styles =====

    # Frame / LabelFrame
    style.configure("TFrame", background=BG_DARK)
    style.configure("TLabelframe", background=BG_DARK, bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER)
    style.configure("TLabelframe.Label", background=BG_DARK, foreground=FG_PRIMARY, font=(DEFAULT_FONT_FAMILY, 10, "bold"))

    # Label
    style.configure("TLabel", background=BG_DARK, foreground=FG_PRIMARY)
    style.configure("Secondary.TLabel", background=BG_DARK, foreground=FG_SECONDARY)
    style.configure("Bold.TLabel", background=BG_DARK, foreground=FG_PRIMARY, font=(DEFAULT_FONT_FAMILY, 10, "bold"))
    style.configure("Title.TLabel", background=BG_DARK, foreground=FG_PRIMARY, font=(DEFAULT_FONT_FAMILY, 11, "bold"))
    style.configure("Status.Ready.TLabel", background=BG_DARK, foreground=ACCENT_GREEN)
    style.configure("Status.Running.TLabel", background=BG_DARK, foreground=ACCENT_BLUE)
    style.configure("Status.Error.TLabel", background=BG_DARK, foreground=ACCENT_RED)

    # Button
    style.configure("TButton",
                    background=BG_ELEVATED,
                    foreground=FG_PRIMARY,
                    bordercolor=BORDER,
                    lightcolor=BG_ELEVATED,
                    darkcolor=BG_ELEVATED,
                    focuscolor=ACCENT_BLUE,
                    padding=(12, 6),
                    font=(DEFAULT_FONT_FAMILY, 9))
    style.map("TButton",
              background=[("active", BG_HOVER), ("pressed", ACCENT_BLUE), ("disabled", BG_ELEVATED)],
              foreground=[("disabled", FG_DISABLED)],
              bordercolor=[("focus", ACCENT_BLUE)])

    # Primary action button (Run Full Pipeline)
    style.configure("Primary.TButton",
                    background=ACCENT_BLUE,
                    foreground="#ffffff",
                    bordercolor=ACCENT_BLUE,
                    padding=(16, 8),
                    font=(DEFAULT_FONT_FAMILY, 10, "bold"))
    style.map("Primary.TButton",
              background=[("active", ACCENT_BLUE_HOVER), ("pressed", "#2563eb"), ("disabled", BG_ELEVATED)],
              foreground=[("disabled", FG_DISABLED)])

    # Stop button (destructive)
    style.configure("Danger.TButton",
                    background=ACCENT_RED,
                    foreground="#ffffff",
                    bordercolor=ACCENT_RED,
                    padding=(12, 6),
                    font=(DEFAULT_FONT_FAMILY, 9, "bold"))
    style.map("Danger.TButton",
              background=[("active", ACCENT_RED_HOVER), ("pressed", "#dc2626"), ("disabled", BG_ELEVATED)],
              foreground=[("disabled", FG_DISABLED)])

    # Small secondary buttons (OpenROAD GUI under nodes)
    style.configure("Secondary.TButton",
                    background=BG_ELEVATED,
                    foreground=FG_SECONDARY,
                    bordercolor=BORDER,
                    padding=(8, 4),
                    font=(DEFAULT_FONT_FAMILY, 8))
    style.map("Secondary.TButton",
              background=[("active", BG_HOVER), ("disabled", BG_ELEVATED)],
              foreground=[("active", FG_PRIMARY), ("disabled", FG_DISABLED)])

    # Toolbar/flat button (for header actions)
    style.configure("Flat.TButton",
                    background=BG_DARK,
                    foreground=FG_PRIMARY,
                    bordercolor=BORDER,
                    padding=(10, 5),
                    font=(DEFAULT_FONT_FAMILY, 9))
    style.map("Flat.TButton",
              background=[("active", BG_ELEVATED), ("disabled", BG_DARK)],
              foreground=[("disabled", FG_DISABLED)])

    # Entry
    style.configure("TEntry",
                    fieldbackground=BG_ELEVATED,
                    foreground=FG_PRIMARY,
                    bordercolor=BORDER,
                    lightcolor=BORDER,
                    darkcolor=BORDER,
                    insertcolor=FG_PRIMARY,
                    padding=(8, 6))
    style.map("TEntry",
              bordercolor=[("focus", ACCENT_BLUE)],
              fieldbackground=[("disabled", BG_ELEVATED)])

    # Combobox
    style.configure("TCombobox",
                    fieldbackground=BG_ELEVATED,
                    foreground=FG_PRIMARY,
                    bordercolor=BORDER,
                    arrowcolor=FG_PRIMARY,
                    padding=(8, 4))
    style.map("TCombobox",
              bordercolor=[("focus", ACCENT_BLUE)],
              fieldbackground=[("readonly", BG_ELEVATED), ("disabled", BG_ELEVATED)],
              foreground=[("disabled", FG_DISABLED)])

    # Notebook (tabs)
    style.configure("TNotebook", background=BG_DARK, borderwidth=0, tabmargins=(0, 0, 0, 0))
    style.configure("TNotebook.Tab",
                    background=BG_ELEVATED,
                    foreground=FG_SECONDARY,
                    bordercolor=BORDER,
                    lightcolor=BG_ELEVATED,
                    darkcolor=BG_ELEVATED,
                    padding=(16, 8),
                    font=(DEFAULT_FONT_FAMILY, 9))
    style.map("TNotebook.Tab",
              background=[("selected", BG_PANEL), ("active", BG_HOVER)],
              foreground=[("selected", FG_PRIMARY), ("active", FG_PRIMARY)],
              bordercolor=[("selected", ACCENT_BLUE)])

    # Treeview (project tree)
    style.configure("Treeview",
                    background=BG_PANEL,
                    foreground=FG_PRIMARY,
                    fieldbackground=BG_PANEL,
                    bordercolor=BORDER,
                    rowheight=24,
                    font=(DEFAULT_FONT_FAMILY, 10))
    style.configure("Treeview.Heading",
                    background=BG_ELEVATED,
                    foreground=FG_PRIMARY,
                    bordercolor=BORDER,
                    font=(DEFAULT_FONT_FAMILY, 10, "bold"))
    style.map("Treeview",
              background=[("selected", SELECTION_BG)],
              foreground=[("selected", SELECTION_FG)])

    # Progressbar
    style.configure("TProgressbar",
                    background=ACCENT_BLUE,
                    troughcolor=BG_ELEVATED,
                    bordercolor=BORDER,
                    lightcolor=ACCENT_BLUE,
                    darkcolor=ACCENT_BLUE,
                    thickness=6)

    # Progressbar variants
    style.configure("Success.TProgressbar", background=ACCENT_GREEN, lightcolor=ACCENT_GREEN, darkcolor=ACCENT_GREEN)
    style.configure("Warning.TProgressbar", background=ACCENT_AMBER, lightcolor=ACCENT_AMBER, darkcolor=ACCENT_AMBER)
    style.configure("Error.TProgressbar", background=ACCENT_RED, lightcolor=ACCENT_RED, darkcolor=ACCENT_RED)

    # Scrollbar
    style.configure("Vertical.TScrollbar",
                    background=BG_ELEVATED,
                    troughcolor=BG_DARK,
                    bordercolor=BORDER,
                    arrowcolor=FG_SECONDARY,
                    gripcount=0)
    style.map("Vertical.TScrollbar",
              background=[("active", BG_HOVER)],
              arrowcolor=[("active", FG_PRIMARY)])

    style.configure("Horizontal.TScrollbar",
                    background=BG_ELEVATED,
                    troughcolor=BG_DARK,
                    bordercolor=BORDER,
                    arrowcolor=FG_SECONDARY,
                    gripcount=0)
    style.map("Horizontal.TScrollbar",
              background=[("active", BG_HOVER)],
              arrowcolor=[("active", FG_PRIMARY)])

    # Separator
    style.configure("TSeparator", background=BORDER)

    # Checkbutton / Radiobutton
    style.configure("TCheckbutton", background=BG_DARK, foreground=FG_PRIMARY, focuscolor=ACCENT_BLUE)
    style.map("TCheckbutton",
              background=[("active", BG_DARK)],
              foreground=[("disabled", FG_DISABLED)])
    style.configure("TRadiobutton", background=BG_DARK, foreground=FG_PRIMARY, focuscolor=ACCENT_BLUE)
    style.map("TRadiobutton",
              background=[("active", BG_DARK)],
              foreground=[("disabled", FG_DISABLED)])

    # Scale (slider)
    style.configure("TScale", background=BG_DARK, troughcolor=BG_ELEVATED, bordercolor=BORDER)

    # PanedWindow
    style.configure("TPanedwindow", background=BG_DARK)
    style.configure("Sash", background=BG_ELEVATED, bordercolor=BORDER)

    # Menubutton (for dropdown menus)
    style.configure("TMenubutton",
                    background=BG_ELEVATED,
                    foreground=FG_PRIMARY,
                    bordercolor=BORDER,
                    padding=(10, 5),
                    font=(DEFAULT_FONT_FAMILY, 9))
    style.map("TMenubutton",
              background=[("active", BG_HOVER), ("disabled", BG_ELEVATED)],
              foreground=[("disabled", FG_DISABLED)])

    # Sizegrip
    style.configure("TSizegrip", background=BG_DARK, bordercolor=BORDER)

    return style


def apply_theme_to_tk_widgets(widget: tk.Misc) -> None:
    """Recursively apply dark background to raw tk widgets (Canvas, Text, etc.).

    ttk widgets are styled via setup_dark_theme(). This handles tk widgets
    that don't use ttk styling.
    """
    if isinstance(widget, (tk.Canvas, tk.Text, tk.Listbox, tk.Scrollbar)):
        try:
            widget.configure(
                background=BG_PANEL if isinstance(widget, (tk.Canvas, tk.Text)) else BG_DARK,
                foreground=FG_PRIMARY,
                insertbackground=FG_PRIMARY,
                selectbackground=SELECTION_BG,
                selectforeground=SELECTION_FG,
                highlightthickness=0,
                borderwidth=0,
            )
            if isinstance(widget, tk.Scrollbar):
                widget.configure(
                    background=BG_ELEVATED,
                    troughcolor=BG_DARK,
                    activebackground=BG_HOVER,
                    borderwidth=0,
                )
        except tk.TclError:
            pass

    # Recurse into children
    try:
        for child in widget.winfo_children():
            apply_theme_to_tk_widgets(child)
    except tk.TclError:
        pass


# Convenience function for creating themed tk widgets
def create_dark_canvas(parent, **kwargs) -> tk.Canvas:
    """Create a Canvas with dark theme defaults."""
    defaults = {
        "background": BG_PANEL,
        "highlightthickness": 0,
        "borderwidth": 0,
    }
    defaults.update(kwargs)
    return tk.Canvas(parent, **defaults)


def create_dark_text(parent, **kwargs) -> tk.Text:
    """Create a Text widget with dark theme defaults."""
    defaults = {
        "background": BG_PANEL,
        "foreground": FG_PRIMARY,
        "insertbackground": FG_PRIMARY,
        "selectbackground": SELECTION_BG,
        "selectforeground": SELECTION_FG,
        "highlightthickness": 0,
        "borderwidth": 0,
        "font": (MONO_FONT_FAMILY, 11),
    }
    defaults.update(kwargs)
    return tk.Text(parent, **defaults)


def create_dark_scrolled_text(parent, **kwargs) -> tk.Text:
    """Create a ScrolledText with dark theme."""
    from tkinter import scrolledtext
    defaults = {
        "background": BG_PANEL,
        "foreground": FG_PRIMARY,
        "insertbackground": FG_PRIMARY,
        "selectbackground": SELECTION_BG,
        "selectforeground": SELECTION_FG,
        "highlightthickness": 0,
        "borderwidth": 0,
        "font": (MONO_FONT_FAMILY, 11),
    }
    defaults.update(kwargs)
    return scrolledtext.ScrolledText(parent, **defaults)