"""
Flat, light theme on top of ttk's 'clam' (no extra dependency).

Layout idea: grey window background, white cards for the left settings panel and the
right preview, blue accent for primary actions and focus, red for errors.

Styles for widgets:
    Accent.TButton   primary action (filled blue)
    Danger.TButton   destructive action (red text)
    Small.TButton    compact secondary button
    Heading.TLabel   section heading      Muted.TLabel  hint text      Error.TLabel  error text
    Card.TFrame      white panel          App.TFrame    grey background
    Error.TEntry / Error.TSpinbox         field with an invalid value
"""

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

BG = "#eef0f4"          # window
CARD = "#ffffff"        # panels
BORDER = "#d6dbe3"
TEXT = "#1f2937"
MUTED = "#6b7280"
ACCENT = "#2563eb"
ACCENT_HOVER = "#1d4ed8"
ACCENT_SOFT = "#e0e9ff"
BUTTON = "#f3f5f8"
BUTTON_HOVER = "#e6eaf0"
ERROR = "#dc2626"
ERROR_BG = "#fdecec"
FONT = "Segoe UI"
MONO = "Consolas"


def apply(root):
    """Configure all ttk styles and classic widget defaults."""
    base = tkfont.nametofont("TkDefaultFont")
    base.configure(family=FONT, size=10)
    for name in ("TkTextFont", "TkMenuFont", "TkHeadingFont"):
        tkfont.nametofont(name).configure(family=FONT, size=10)
    root.configure(background=BG)
    root.option_add("*Font", (FONT, 10))
    root.option_add("*Listbox.background", CARD)
    root.option_add("*Listbox.foreground", TEXT)
    root.option_add("*Listbox.selectBackground", ACCENT)
    root.option_add("*Listbox.selectForeground", "white")
    root.option_add("*Listbox.relief", "flat")
    root.option_add("*Listbox.highlightThickness", 1)
    root.option_add("*Listbox.highlightColor", ACCENT)
    root.option_add("*Listbox.highlightBackground", BORDER)
    root.option_add("*TCombobox*Listbox.font", (FONT, 10))

    s = ttk.Style(root)
    s.theme_use("clam")
    s.configure(".", background=CARD, foreground=TEXT, font=(FONT, 10), bordercolor=BORDER,
                lightcolor=CARD, darkcolor=CARD, troughcolor=BG, focuscolor=ACCENT,
                selectbackground=ACCENT, selectforeground="white", insertcolor=TEXT)
    s.configure("TFrame", background=CARD)
    s.configure("Card.TFrame", background=CARD)
    s.configure("App.TFrame", background=BG)
    s.configure("TLabel", background=CARD, foreground=TEXT)
    s.configure("Heading.TLabel", font=(FONT, 11, "bold"), foreground=TEXT)
    s.configure("Muted.TLabel", foreground=MUTED, font=(FONT, 9))
    s.configure("Error.TLabel", foreground=ERROR, font=(FONT, 9))
    s.configure("App.TLabel", background=BG, foreground=MUTED, font=(FONT, 9))

    # buttons
    s.configure("TButton", background=BUTTON, foreground=TEXT, bordercolor=BORDER, lightcolor=BUTTON,
                darkcolor=BUTTON, relief="flat", padding=(12, 6), focusthickness=0)
    s.map("TButton", background=[("pressed", BUTTON_HOVER), ("active", BUTTON_HOVER), ("disabled", BUTTON)],
          lightcolor=[("active", BUTTON_HOVER)], darkcolor=[("active", BUTTON_HOVER)],
          foreground=[("disabled", "#a0a7b2")])
    s.configure("Accent.TButton", background=ACCENT, foreground="white", bordercolor=ACCENT, lightcolor=ACCENT,
                darkcolor=ACCENT, font=(FONT, 10, "bold"), padding=(12, 8))
    s.map("Accent.TButton", background=[("pressed", ACCENT_HOVER), ("active", ACCENT_HOVER)],
          lightcolor=[("active", ACCENT_HOVER)], darkcolor=[("active", ACCENT_HOVER)],
          bordercolor=[("active", ACCENT_HOVER)])
    s.configure("Danger.TButton", foreground=ERROR)
    s.configure("Small.TButton", padding=(8, 3), font=(FONT, 9))
    s.configure("SmallDanger.TButton", padding=(8, 3), font=(FONT, 9), foreground=ERROR)
    for st_ in ("Danger.TButton", "Small.TButton", "SmallDanger.TButton"):
        s.map(st_, background=[("pressed", BUTTON_HOVER), ("active", BUTTON_HOVER)],
              lightcolor=[("active", BUTTON_HOVER)], darkcolor=[("active", BUTTON_HOVER)])

    # input fields
    for cls in ("TEntry", "TSpinbox", "TCombobox"):
        s.configure(cls, fieldbackground=CARD, background=CARD, foreground=TEXT, bordercolor=BORDER,
                    lightcolor=CARD, darkcolor=CARD, arrowcolor=MUTED, padding=(6, 4), insertcolor=TEXT)
        s.map(cls, bordercolor=[("focus", ACCENT)], lightcolor=[("focus", ACCENT)],
              fieldbackground=[("disabled", BG), ("readonly", CARD)], foreground=[("disabled", "#9aa1ab")])
        s.configure(f"Error.{cls}", fieldbackground=ERROR_BG, bordercolor=ERROR, lightcolor=ERROR, darkcolor=ERROR)
        s.map(f"Error.{cls}", bordercolor=[("focus", ERROR)], lightcolor=[("focus", ERROR)])
    s.configure("TSpinbox", arrowsize=11)
    s.map("TCombobox", selectbackground=[("readonly", CARD)], selectforeground=[("readonly", TEXT)])

    # check and radio buttons
    for cls in ("TCheckbutton", "TRadiobutton"):
        s.configure(cls, background=CARD, foreground=TEXT, indicatorbackground=CARD, indicatorforeground=ACCENT,
                    indicatormargin=(0, 0, 6, 0), padding=(0, 2), focusthickness=0)
        s.map(cls, background=[("active", CARD)], indicatorbackground=[("selected", ACCENT), ("active", ACCENT_SOFT)],
              indicatorforeground=[("selected", "white")], foreground=[("disabled", "#9aa1ab")])

    # notebook as a flat tab bar
    s.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(12, 8, 12, 0))
    s.configure("TNotebook.Tab", background=BG, foreground=MUTED, padding=(18, 8), borderwidth=0,
                font=(FONT, 10, "bold"), lightcolor=BG, bordercolor=BG)
    s.map("TNotebook.Tab", background=[("selected", CARD), ("active", "#e4e8ef")],
          foreground=[("selected", ACCENT), ("active", TEXT)], lightcolor=[("selected", CARD)],
          bordercolor=[("selected", CARD)])

    # slim scrollbars
    s.configure("Vertical.TScrollbar", background=BUTTON, troughcolor=CARD, bordercolor=CARD, arrowcolor=MUTED,
                lightcolor=BUTTON, darkcolor=BUTTON, gripcount=0, arrowsize=12)
    s.map("Vertical.TScrollbar", background=[("active", BUTTON_HOVER)])
    s.configure("TSeparator", background=BORDER)


def canvas(parent, **kw):
    """Canvas in card colour without the default highlight border."""
    return tk.Canvas(parent, background=CARD, highlightthickness=0, **kw)
