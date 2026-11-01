"""Reusable widgets: tooltips, input fields with error marking, side panel, project list, flags."""

import tkinter as tk
from tkinter import messagebox, ttk

from .. import logging_setup
from ..i18n import T
from . import theme

log = logging_setup.get("gui")

LEFT_W = 410   # width of the left column in every tab


# ---------------------------------------------------------------------------
# Tooltips
# ---------------------------------------------------------------------------

class Tooltip:
    """Short explanation shown while the mouse rests on a widget."""

    def __init__(self, widget, text, delay=450):
        self.w, self.text, self.delay = widget, text, delay
        self.tip = self.job = None
        widget.bind("<Enter>", self.schedule, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<ButtonPress>", self.hide, add="+")

    def schedule(self, _=None):
        self.cancel()
        self.job = self.w.after(self.delay, self.show)

    def cancel(self):
        if self.job:
            self.w.after_cancel(self.job)
            self.job = None

    def show(self):
        self.job = None
        text = self.text() if callable(self.text) else self.text
        if not text or not self.w.winfo_ismapped():
            return
        x = self.w.winfo_rootx() + 12
        y = self.w.winfo_rooty() + self.w.winfo_height() + 6
        self.tip = tw = tk.Toplevel(self.w)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(tw, text=text, justify="left", background="#1f2937", foreground="white", relief="flat",
                 borderwidth=0, wraplength=320, font=(theme.FONT, 9), padx=9, pady=6).pack()

    def hide(self, _=None):
        self.cancel()
        if self.tip:
            self.tip.destroy()
            self.tip = None


def tip(widget, text):
    """Attach a tooltip and return the widget (for chained calls)."""
    Tooltip(widget, text)
    return widget


# ---------------------------------------------------------------------------
# Input fields
# ---------------------------------------------------------------------------

def entry(parent, var, width=10):
    return ttk.Entry(parent, textvariable=var, width=width)


def spinbox(parent, var, lo, hi, step, width=7):
    return ttk.Spinbox(parent, textvariable=var, from_=lo, to=hi, increment=step, width=width)


def mark(widget, bad):
    """Mark a field red (bad=True) or reset it."""
    cls = widget.winfo_class()
    if cls in ("TEntry", "TSpinbox", "TCombobox"):
        widget.configure(style=f"Error.{cls}" if bad else cls)


def number(var):
    """Number from an input field (comma allowed); ValueError for anything else."""
    txt = var.get().strip().replace(",", ".")
    if not txt:
        raise ValueError(T("Please enter a number."))
    try:
        return float(txt)
    except ValueError:
        raise ValueError(T("Please enter a number.")) from None


def info_text(parent, height):
    t = tk.Text(parent, width=50, height=height, font=(theme.MONO, 9), relief="flat", wrap="word",
                background="#f7f8fa", foreground=theme.TEXT, padx=8, pady=6, borderwidth=0,
                highlightthickness=0)
    t.tag_configure("err", foreground=theme.ERROR)
    t.tag_configure("errhead", foreground=theme.ERROR, font=(theme.MONO, 9, "bold"))
    return t


def set_info(widget, text="", errors=None):
    """Set the info text; errors (list) are shown in red at the top."""
    widget.configure(state="normal")
    widget.delete("1.0", "end")
    if errors:
        widget.insert("end", T("Please correct:") + "\n", "errhead")
        for e in errors:
            widget.insert("end", f"• {e}\n", "err")
        if text:
            widget.insert("end", "\n")
    if text:
        widget.insert("end", text)
    widget.configure(state="disabled")


def heading(parent, text, tiptext=None):
    w = ttk.Label(parent, text=text, style="Heading.TLabel")
    return tip(w, tiptext) if tiptext else w


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

class ScrollPanel(ttk.Frame):
    """Vertically scrollable frame; the scrollbar only appears when the content is taller."""

    def __init__(self, parent):
        super().__init__(parent, style="Card.TFrame")
        self.canvas = tk.Canvas(self, background=theme.CARD, highlightthickness=0, borderwidth=0)
        self.bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas, style="Card.TFrame", padding=(16, 14, 12, 8))
        self.win = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner.bind("<Configure>", self._update)
        self.canvas.bind("<Configure>", self._update)
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._wheel))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

    def _update(self, _=None):
        self.canvas.itemconfigure(self.win, width=self.canvas.winfo_width())
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        need = self.inner.winfo_reqheight() > self.canvas.winfo_height() + 2
        if need and not self.bar.winfo_ismapped():
            self.bar.pack(side="right", fill="y")
        elif not need and self.bar.winfo_ismapped():
            self.bar.pack_forget()
            self.canvas.yview_moveto(0)

    def _wheel(self, e):
        # lists and text fields scroll themselves
        if isinstance(e.widget, (tk.Listbox, tk.Text)) or self.inner.winfo_reqheight() <= self.canvas.winfo_height():
            return
        self.canvas.yview_scroll(-1 if e.delta > 0 else 1, "units")


def tab_layout(parent):
    """Standard tab layout: (left content frame, bottom-left button bar, right card)."""
    parent.configure(style="App.TFrame")
    left = ttk.Frame(parent, style="Card.TFrame", width=LEFT_W)
    left.pack(side="left", fill="y", padx=(12, 6), pady=12)
    left.pack_propagate(False)
    bottom = ttk.Frame(left, style="Card.TFrame", padding=(16, 8, 16, 14))
    bottom.pack(side="bottom", fill="x")
    ttk.Separator(left).pack(side="bottom", fill="x")
    panel = ScrollPanel(left)
    panel.pack(side="top", fill="both", expand=True)
    right = ttk.Frame(parent, style="Card.TFrame", padding=10)
    right.pack(side="right", fill="both", expand=True, padx=(6, 12), pady=12)
    return panel.inner, bottom, right


# ---------------------------------------------------------------------------
# Project list (4 visible rows, scrollable, with delete)
# ---------------------------------------------------------------------------

class ProjectList(ttk.Frame):
    """List of baseplate projects with a delete button.
    on_select(name or None) is called when the selection changes; on_deleted(name) after deleting."""

    def __init__(self, parent, on_select, on_deleted, tiptext="", allow_none=False):
        super().__init__(parent, style="Card.TFrame")
        self.on_select, self.on_deleted, self.allow_none = on_select, on_deleted, allow_none
        self.names, self.current = [], None
        box = ttk.Frame(self, style="Card.TFrame")
        box.pack(fill="x")
        self.lb = tk.Listbox(box, height=4, exportselection=False, activestyle="none")
        sb = ttk.Scrollbar(box, orient="vertical", command=self.lb.yview)
        self.lb.configure(yscrollcommand=sb.set)
        self.lb.pack(side="left", fill="x", expand=True)
        sb.pack(side="right", fill="y")
        tip(self.lb, tiptext)
        row = ttk.Frame(self, style="Card.TFrame")
        row.pack(fill="x", pady=(4, 0))
        self.empty = ttk.Label(row, text="", style="Muted.TLabel")
        self.empty.pack(side="left")
        tip(ttk.Button(row, text=T("Delete project"), style="SmallDanger.TButton", command=self.delete),
            T("Moves the selected project folder to the recycle bin (can be restored from there).")).pack(side="right")
        self.lb.bind("<<ListboxSelect>>", self._picked)

    def set_items(self, names, keep=True):
        """Fill the list; keeps the current selection if it still exists."""
        self.names = list(names)
        self.lb.delete(0, "end")
        for n in self.names:
            self.lb.insert("end", "  " + n)
        self.empty.configure(text="" if self.names else T("No projects yet."))
        target = self.current if keep and self.current in self.names else (self.names[0] if self.names else None)
        self.select(target, notify=target != self.current)

    def select(self, name, notify=True):
        self.lb.selection_clear(0, "end")
        if name in self.names:
            i = self.names.index(name)
            self.lb.selection_set(i)
            self.lb.see(i)
        changed = name != self.current
        self.current = name if name in self.names else None
        if notify and (changed or name is None):
            self.on_select(self.current)

    def get(self):
        return self.current

    def _picked(self, _):
        s = self.lb.curselection()
        if s:
            self.select(self.names[s[0]])

    def delete(self):
        from .. import projects
        name = self.current
        if not name:
            return
        if not messagebox.askyesno(T("Delete project"), T("Really delete project '{n}'?\n\nThe folder with all its "
                                                         "files goes to the recycle bin.", n=name)):
            return
        try:
            projects.delete_project(name)
        except Exception as e:  # noqa: BLE001
            log.exception("Deleting project %s failed", name)
            messagebox.showerror(T("Error"), str(e))
            return
        self.current = None
        self.on_deleted(name)


# ---------------------------------------------------------------------------
# Flags for the language switch
# ---------------------------------------------------------------------------

def flag_image(code, active, w=30, h=18):
    """Small flag as PhotoImage (inactive ones are faded)."""
    from PIL import Image, ImageDraw, ImageTk
    k = 4   # draw large, then scale down smoothly
    W, H = w * k, h * k
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    if code == "de":
        for i, col in enumerate(("#000000", "#dd0000", "#ffce00")):
            d.rectangle([0, i * H / 3, W, (i + 1) * H / 3], fill=col)
    else:   # Union Jack (simplified)
        d.rectangle([0, 0, W, H], fill="#012169")
        d.line([(0, 0), (W, H)], fill="white", width=int(H * 0.2))
        d.line([(0, H), (W, 0)], fill="white", width=int(H * 0.2))
        d.line([(0, 0), (W, H)], fill="#c8102e", width=int(H * 0.07))
        d.line([(0, H), (W, 0)], fill="#c8102e", width=int(H * 0.07))
        d.rectangle([W / 2 - H * 0.17, 0, W / 2 + H * 0.17, H], fill="white")
        d.rectangle([0, H / 2 - H * 0.17, W, H / 2 + H * 0.17], fill="white")
        d.rectangle([W / 2 - H * 0.1, 0, W / 2 + H * 0.1, H], fill="#c8102e")
        d.rectangle([0, H / 2 - H * 0.1, W, H / 2 + H * 0.1], fill="#c8102e")
    img = img.resize((w, h), Image.LANCZOS)
    if not active:
        img = Image.blend(img, Image.new("RGB", img.size, theme.BG), 0.55)
    return ImageTk.PhotoImage(img)

