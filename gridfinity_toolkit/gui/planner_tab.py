"""
Planner tab ("Combined Grid"): place bins on the grid of a baseplate project, stack them in
levels, look at the drawer in 3D and export print-ready plates.

Selection:
    click a type in the list  -> its bins are highlighted; the height field changes the whole type
    click the box behind a type -> export it or not (unticked = placeholder, e.g. for bins you already have)
    click a bin in the grid   -> only that bin is selected (Ctrl+click: several); changing their height
                                 changes their type if they are all of its bins, otherwise they become a new type
    click a free cell         -> place the selected type
    drag over free cells      -> new bin of that size with its own name (becomes a new type)
    drag a handle of the selected bin -> resize it along the grid
    drag a bin                -> move it (with the other selected bins and everything stacked on them)
    double-click a bin        -> rename its type
    Ctrl+C / Ctrl+V           -> copy the selected bins, then click where the copy goes
    Ctrl+Z / Ctrl+Y           -> undo / redo
    plates (made in the Bin tab) close cells on level 0 or are a lid on a stacking surface
    no type selected          -> new bins use the Bin tab settings with the height from the height field
    right-click / Del key     -> remove a bin (bins stacked on it stay; without support they turn red)
"""

import json
import math
import os
import tkinter as tk
from tkinter import font as tkfont
from tkinter import colorchooser, messagebox, ttk
from types import SimpleNamespace

import numpy as np

from .. import bins as binlib
from .. import logging_setup, paths, projects
from ..grid import EPS, PITCH, bump_name, fmt, tint
from ..i18n import T
from ..print_layout import duration_text
from ..baseplate import seat_height
from ..planner import (DEFAULT_STYLE, RED, STYLE_KEYS, Scene, bin_widths, change_style, check, edges, export,
                       floating, floating_note, free_color, height_note, highest, is_plate, level_role, load_types,
                       magnet_notes, move, overlap_xy, partial_widths, plate_style, remove, resize, resting_on,
                       skipped_types, stack_levels, style_of, summary, top, type_details)
from . import theme, widgets as w
from .viewer import View3D

log = logging_setup.get("planner_tab")

HIGHLIGHT = "#facc15"
BLOCKED_DARK = "#7f1d1d"   # outline and hatching of bins that stick through the current level
CHECK_MARGIN = 8           # pixels between the export boxes of the type list and its right edge


def build(parent, app=None, state=None):
    """Build the tab. Returns an object with refresh(), add_type(), select_project(), type_names()
    and get_state()."""
    root = parent.winfo_toplevel()
    state = state or {}
    base_too = tk.BooleanVar(value=state.get("base_too", True))
    type_colors = tk.BooleanVar(value=state.get("type_colors", False))
    singles = tk.BooleanVar(value=state.get("singles", False))
    rotated = tk.BooleanVar(value=state.get("rotated", False))
    level_var = tk.StringVar(value=state.get("level", "0"))
    view = tk.StringVar(value=state.get("view", "2d"))
    dim_levels = tk.BooleanVar(value=state.get("dim_levels", True))
    he_var = tk.StringVar(value="")
    mm_var = tk.StringVar(value="")
    drawer_var = tk.StringVar(value="")
    status = tk.StringVar(value="")
    search_var = tk.StringVar(value="")
    st = {"plan": None, "folder": None, "name": None, "bins": [], "types": load_types(), "geo": None,
          "press": None, "hover": None, "grab": None, "scene": Scene(), "job3d": None, "sel_bins": [],
          "he_loading": False, "he_job": None, "free_h": None, "he_sync": False, "drawer_loading": False,
          "move": None, "ghosts": None, "clip": None, "paste": False, "hist": [], "redo": [],
          "type_focus": False, "shown": []}

    frm, bottom, right = w.tab_layout(parent)

    # --- left panel ------------------------------------------------------------
    w.heading(frm, T("Project"), T("Grid from the Baseplate tab that you plan on.")).pack(anchor="w")
    plist = w.ProjectList(frm, lambda n: open_project(n), lambda n: app.projects_changed() if app else refresh(),
                          T("Grid from the Baseplate tab that you plan on."))
    plist.pack(anchor="w", fill="x", pady=(4, 0))
    proj_info = ttk.Label(frm, text=T("First create a project in the Baseplate tab."), style="Muted.TLabel")
    proj_info.pack(anchor="w", pady=(4, 0))

    lrow = ttk.Frame(frm)
    lrow.pack(anchor="w", fill="x", pady=(14, 0))
    lvl_tip = T("Height of the bin bottom in units. 0 = on the baseplate, higher = stacked.")
    w.heading(lrow, T("Level (units above floor):"), lvl_tip).pack(side="left")
    lvl_spin = w.tip(w.spinbox(lrow, level_var, 0, 60, 1, width=5), lvl_tip)
    lvl_spin.pack(side="left", padx=6)
    lvl_up = w.tip(ttk.Button(lrow, text="▲", width=3, style="Small.TButton"), T("To the next stacking surface above."))
    lvl_up.pack(side="left")
    lvl_down = w.tip(ttk.Button(lrow, text="▼", width=3, style="Small.TButton"), T("To the next stacking surface below."))
    lvl_down.pack(side="left", padx=(3, 0))
    lvl_info = ttk.Label(frm, text="", style="Muted.TLabel")
    lvl_info.pack(anchor="w")

    w.heading(frm, T("Bin types")).pack(anchor="w", pady=(14, 4))
    srow = ttk.Frame(frm)
    srow.pack(anchor="w", fill="x", pady=(0, 4))
    search_tip = T("Shows only the types whose name or details contain this text, e.g. '2x1', '6 HE' or 'hexagon'.")
    w.tip(ttk.Label(srow, text=T("Search")), search_tip).pack(side="left")
    search_ent = w.tip(ttk.Entry(srow, textvariable=search_var), search_tip)
    search_ent.pack(side="left", fill="x", expand=True, padx=(6, 4))
    w.tip(ttk.Button(srow, text="✕", width=3, style="Small.TButton", command=lambda: search_var.set("")),
          T("Clear the search: show all types.")).pack(side="left")
    arow = ttk.Frame(frm)
    arow.pack(anchor="w", fill="x", pady=(0, 4))
    types_list = w.tip(tk.Listbox(frm, height=8, exportselection=False, activestyle="none"),
                       T("Click a type to select it: free cells get this type, and its bins are highlighted. "
                         "Double-click to rename it. Click the box behind it to export the type or not "
                         "(placeholder, e.g. for bins you already have)."))
    # header box of the export column: right-aligned above the boxes in the list
    all_btn = w.tip(ttk.Label(arow, text=T("Select all") + "  ☐", font=types_list.cget("font"), cursor="hand2",
                              padding=0),
                    T("☑ = export, ☐ = placeholder only. Ticks the export box of all types shown "
                      "(click again to untick them)."))
    all_btn.pack(side="right", padx=(0, CHECK_MARGIN + 2))
    types_list.pack(anchor="w", fill="x")
    trow = ttk.Frame(frm)
    trow.pack(anchor="w", fill="x", pady=(4, 0))
    w.tip(ttk.Checkbutton(trow, text=T("rotated (key R)"), variable=rotated),
          T("Swaps width and depth of the type when placing.")).pack(side="left")
    trow2 = ttk.Frame(frm)
    trow2.pack(anchor="w", fill="x", pady=(4, 0))
    he_tip = T("Height in units. With a type selected it changes all bins of that type; with bins selected in "
               "the grid only those (they get a new type unless they are all bins of their type).")
    mm_tip = T("Height in mm without stacking lip, e.g. what you measured. The next larger height in units "
               "(steps of 3.5 mm) is used.")
    w.tip(ttk.Label(trow2, text=T("Height (mm)")), mm_tip).pack(side="left")
    mm_spin = w.tip(w.spinbox(trow2, mm_var, 7, 280, 1, width=5), mm_tip)
    mm_spin.pack(side="left", padx=(6, 4))
    he_spin = w.tip(w.spinbox(trow2, he_var, 1, 40, 0.5, width=5), he_tip)
    he_spin.pack(side="left")
    w.tip(ttk.Label(trow2, text=T("units")), he_tip).pack(side="left", padx=(4, 0))
    h_real = ttk.Label(trow2, text="", style="Muted.TLabel")
    h_real.pack(side="left", padx=(6, 0))
    scope = ttk.Label(frm, text="", style="Muted.TLabel", wraplength=w.LEFT_W - 50)
    scope.pack(anchor="w", pady=(2, 0))


    brow = ttk.Frame(frm)
    brow.pack(anchor="w", fill="x", pady=(8, 0))
    ttk.Label(frm, textvariable=status, style="Error.TLabel", wraplength=w.LEFT_W - 50).pack(anchor="w", pady=(6, 0))
    info = w.info_text(frm, 10)
    info.configure(wrap="none")

    # --- right side ------------------------------------------------------------
    vbar = ttk.Frame(right)
    vbar.pack(anchor="w", fill="x")
    view_tip = T("Top view for planning or 3D view for looking.")
    w.tip(ttk.Radiobutton(vbar, text=T("2D grid"), value="2d", variable=view), view_tip).pack(side="left")
    w.tip(ttk.Radiobutton(vbar, text=T("3D view"), value="3d", variable=view), view_tip).pack(side="left", padx=10)
    dim_check = w.tip(ttk.Checkbutton(vbar, text=T("Grey out other levels"), variable=dim_levels),
                      T("3D view: bins that do not start on the current level are grey and see-through, so you can see what is "
                        "below them."))
    canvas = theme.canvas(right)
    view3d = View3D(right)

    # --- data ---------------------------------------------------------------
    def level():
        """Current level; invalid input is marked red and counts as 0."""
        try:
            z = w.number(level_var)
            ok = z >= 0 and abs(z * 2 - round(z * 2)) < 1e-6
        except ValueError:
            z, ok = 0.0, False
        w.mark(lvl_spin, not ok)
        if not ok:
            status.set(T("Level: please enter a whole or half number from 0."))
        return max(0.0, z) if ok else 0.0

    def type_names():
        return [t["name"] for t in st["types"]]

    def all_names():
        return set(type_names()) | {b.get("name") for b in st["bins"]}

    def row_type(row):
        """Index in st["types"] of a list row (two rows per type, filtered by the search), or None."""
        return st["shown"][row // 2] if 0 <= row < 2 * len(st["shown"]) else None

    def type_row(k):
        """Name row of type k in the list, or None if the search hides it."""
        return 2 * st["shown"].index(k) if k in st["shown"] else None

    def sel_type():
        s = types_list.curselection()
        k = row_type(s[0]) if s else None
        return st["types"][k] if k is not None and k < len(st["types"]) else None

    def free_type():
        """Template when no type is selected: Bin tab settings, height from the height field if one was typed."""
        style = (app.bin_tab_style() if app else None) or dict(DEFAULT_STYLE)
        if st["free_h"] is not None and st["free_h"] >= binlib.min_height(style["lip"], style["wall"]) - EPS:
            style["h"] = st["free_h"]
        return dict(style, nx=1, ny=1, name="", color=free_color(st["types"]))

    def draw_type():
        return sel_type() or free_type()

    def highlighted():
        """Bins to highlight: the selected bins, otherwise right after a click on a type in the list
        all bins of that type (until the next click in the grid or Esc)."""
        if st["sel_bins"]:
            return list(st["sel_bins"])
        t = sel_type()
        return [b for b in st["bins"] if t and st["type_focus"] and b.get("name") == t["name"]]

    def clear_selection():
        """Nothing selected or highlighted any more, no type chosen either."""
        st["sel_bins"], st["type_focus"], st["hover"] = [], False, None
        types_list.selection_clear(0, "end")
        status.set("")
        show_height()
        redraw()

    def select_type(k):
        types_list.selection_clear(0, "end")
        if 0 <= k < len(st["types"]):
            if type_row(k) is None:   # hidden by the search: show all types again
                search_var.set("")
            row = type_row(k)
            types_list.selection_set(row, row + 1)
            types_list.see(row + 1)
        show_height()

    def show_types(select=None):
        """Fill the list with the types matching the search; select: index to select, else keep the current one."""
        cur = sel_type()
        q = search_var.get().strip().lower()
        st["shown"] = [n for n, t in enumerate(st["types"])
                       if not q or q in t["name"].lower() or q in type_details(t).lower()]
        types_list.delete(0, "end")
        indent = pad_to("", list_font().measure("  ■  "))
        for row_n, n in enumerate(st["shown"]):
            t = st["types"][n]
            types_list.insert("end", name_row(t))
            types_list.insert("end", indent + type_details(t)
                              + ("" if exported(t) else "  · " + T("placeholder, not exported")))
            for row in (2 * row_n, 2 * row_n + 1):
                types_list.itemconfigure(row, foreground=t["color"] if row % 2 == 0 else theme.MUTED,
                                         selectforeground="white", selectbackground=t["color"])
        # keep the current type; nothing chosen stays nothing chosen
        k = select if isinstance(select, int) else next((n for n, x in enumerate(st["types"]) if x is cur), None)
        if k is not None and st["types"] and (isinstance(select, int) or type_row(k) is not None):
            select_type(min(k, len(st["types"]) - 1))
        else:
            show_height()
        shown = [st["types"][n] for n in st["shown"]]
        all_btn.configure(text=T("Select all") + ("  ☑" if shown and all(map(exported, shown)) else "  ☐"))
        st["list_w"] = types_list.winfo_width()

    def exported(t):
        return t.get("export", True)

    def list_font():
        return tkfont.Font(font=types_list.cget("font"))

    def pad_to(text, px):
        """text plus spaces up to px pixels wide (hair spaces fill the last few pixels)."""
        f = list_font()
        gap = px - f.measure(text)
        sp, hair = f.measure(" ") or 1, f.measure(" ") or 1
        n = max(0, gap - hair) // sp if gap > sp else 0
        return text + " " * n + " " * max(0, (gap - n * sp) // hair)

    def check_x():
        """Left edge of the export box at the right end of a name row, in listbox pixels."""
        edge = int(types_list.cget("borderwidth")) + int(types_list.cget("highlightthickness"))
        return types_list.winfo_width() - edge - CHECK_MARGIN - list_font().measure("☑")

    def name_row(t):
        """Icon and name on the left, export box right-aligned (long names are shortened with …)."""
        f, box = list_font(), "☑" if exported(t) else "☐"
        left, room = ("  ▭  " if is_plate(t) else "  ■  ") + t["name"], check_x() - 2 - 8
        if f.measure(left) > room:
            while len(left) > 6 and f.measure(left + "…") > room:
                left = left[:-1]
            left += "…"
        return pad_to(left, check_x() - 2) + box

    def on_list_resize(e):
        if e.width != st.get("list_w"):   # boxes stay at the right edge
            show_types()

    def set_export(types, on):
        """Export the types or make them placeholders (they stay in the grid but get no files)."""
        for t in types:
            if on:
                t.pop("export", None)
            else:
                t["export"] = False
        log.info("Export %s for types: %s", "on" if on else "off", ", ".join(t["name"] for t in types))
        fill_types_list()
        redraw()

    def toggle_all():
        shown = [st["types"][n] for n in st["shown"]]
        if shown:
            set_export(shown, not all(map(exported, shown)))

    def on_check_click(e):
        """Click on the box behind a type name: export it or not, without changing the selection."""
        row = types_list.nearest(e.y)
        box = types_list.bbox(row)
        k = row_type(row)
        if k is None or row % 2 or not box or not box[1] <= e.y < box[1] + box[3] or e.x < check_x() - 4:
            return None
        t = st["types"][k]
        set_export([t], not exported(t))
        status.set(T("Type '{n}' is exported.", n=t["name"]) if exported(t) else
                   T("Type '{n}' is a placeholder now: it stays in the grid but is not exported.", n=t["name"]))
        return "break"

    def fill_types_list(select=None):
        """Types changed: refresh the list, save the types and remember the state for undo."""
        show_types(select)
        try:
            projects.save_bin_types(st["types"])
        except OSError as e:
            status.set(T("Types could not be saved: {e}", e=e))
        remember()

    # --- undo / redo: snapshots of bins and types after every change -------------
    def snapshot():
        return json.dumps({"bins": st["bins"], "types": st["types"]})

    def remember():
        snap = snapshot()
        if not st["hist"] or st["hist"][-1] != snap:
            st["hist"] = (st["hist"] + [snap])[-100:]
            st["redo"] = []

    def restore(snap):
        d = json.loads(snap)
        st["bins"], st["types"], st["sel_bins"], st["ghosts"], st["paste"] = d["bins"], d["types"], [], None, False
        if st["folder"]:
            try:
                projects.save_layout(st["folder"], st["bins"])
            except OSError as e:
                status.set(T("Layout could not be saved: {e}", e=e))
        fill_types_list()
        w.set_info(info, summary(st["plan"], st["bins"]) if st["plan"] else "")
        update_levels()
        show_height()
        redraw()

    def undo():
        if len(st["hist"]) > 1:
            st["redo"].append(st["hist"].pop())
            restore(st["hist"][-1])
            status.set(T("Undone."))
            log.info("Undo (%d steps left)", len(st["hist"]) - 1)
        else:
            status.set(T("Nothing to undo."))

    def redo():
        if st["redo"]:
            snap = st["redo"].pop()
            st["hist"].append(snap)
            restore(snap)
            status.set(T("Redone."))
            log.info("Redo")
        else:
            status.set(T("Nothing to redo."))

    def on_types_select(_):
        s = types_list.curselection()
        if s and row_type(s[0]) is not None:
            st["sel_bins"] = []   # a type click always means the whole type
            st["type_focus"] = True
            select_type(row_type(s[0]))
        status.set("")
        redraw()

    def show_height():
        """Put the height of the selection into the field without triggering a change."""
        bs, t = st["sel_bins"], sel_type()
        st["he_loading"] = True
        if bs:   # several bins with different heights: empty field
            hs = {x["style"]["h"] for x in bs}
            he_var.set(fmt(bs[0]["style"]["h"]) if len(hs) == 1 else "")
        else:
            he_var.set(fmt(t["h"]) if t else "")
        st["he_loading"] = False
        w.mark(he_spin, False)
        fixed = all(is_plate(x["style"]) for x in bs) if bs else bool(t and is_plate(t))
        for spin in (he_spin, mm_spin):   # plates have a fixed height
            spin.state(["disabled"] if fixed else ["!disabled"])
        if len(bs) == 1:
            scope.configure(text=T("Applies to: only the selected bin '{n}'", n=bs[0].get("name") or "?"))
        elif bs:
            scope.configure(text=T("Applies to: the {c} selected bins", c=len(bs)))
        elif t:
            n = sum(1 for x in st["bins"] if x.get("name") == t["name"])
            scope.configure(text=T("Applies to: type '{n}' and its {c} placed bins", n=t["name"], c=n))
        else:
            st["he_loading"] = True
            he_var.set(fmt(free_type()["h"]))
            st["he_loading"] = False
            scope.configure(text=T("No type selected: new bins get the Bin tab settings with this height."))

    def on_height(*_):
        if st["he_loading"]:
            return
        if st["he_job"]:
            root.after_cancel(st["he_job"])
        st["he_job"] = root.after(500, apply_height)   # apply after a short typing pause

    def parse_height(lip, wall):
        h = w.number(he_var)
        hmin = binlib.min_height(lip, wall)
        if abs(h * 2 - round(h * 2)) > 1e-6:
            raise ValueError(T("Whole or half units only."))
        if not hmin <= h <= 40:
            raise ValueError(T("Please between {a} and {b} units.", a=fmt(hmin), b="40"))
        return h

    def apply_height():
        st["he_job"] = None
        bs, t, p = st["sel_bins"], sel_type(), st["plan"]
        if (bs and all(is_plate(x["style"]) for x in bs)) or (not bs and t and is_plate(t)):
            status.set(T("Plates have a fixed height."))
            show_height()
            return
        bs = [x for x in bs if not is_plate(x["style"])]
        styles = [x["style"] for x in bs] or [t or free_type()]
        try:   # the strictest minimum height of all targets
            h = parse_height(any(s["lip"] for s in styles), max(s["wall"] for s in styles))
        except ValueError as e:
            w.mark(he_spin, True)
            status.set(T("Height: {e}", e=e))
            return
        w.mark(he_spin, False)
        if not bs and not t:   # only remembered for the next bins drawn freely
            st["free_h"] = h
            return
        if all(abs(h - s["h"]) < EPS for s in styles):
            return
        if bs:
            height_of_bins(bs, h)
        else:   # whole type
            old = t["h"]
            t["h"] = h
            targets = [x for x in st["bins"] if x.get("name") == t["name"]]
            changed, kept = change_style(p, st["bins"], targets, style_of(t), color=t["color"]) if p else (0, 0)
            log.info("Height of %s: %s -> %s HE (%d placed changed, %d unchanged)", t["name"], fmt(old), fmt(h),
                     changed, kept)
            msg = T("Type '{n}' set to {h} units, {c} placed bins adjusted.", n=t["name"], h=fmt(h), c=changed)
            if kept:
                msg += " " + T("{k} stayed unchanged because the new height would collide with stacked bins.",
                               k=kept)
            fill_types_list(select=st["types"].index(t))
            status.set(msg)
        save_layout()
        show_height()
        redraw()

    def height_of_bins(bs, h):
        """Height for selected bins, per type: all bins of a type selected -> the type changes; only some of
        them -> those become a new type together."""
        p, groups, msgs, changed, kept = st["plan"], {}, [], 0, 0
        for b in bs:
            groups.setdefault(b.get("name") or "", []).append(b)
        for name, group in groups.items():
            t = next((x for x in st["types"] if x["name"] == name), None)
            if t and len(group) == sum(1 for x in st["bins"] if x.get("name") == name):
                t["h"] = h
                c, k = change_style(p, st["bins"], group, style_of(t), color=t["color"])
                if c:
                    msgs.append(T("Type '{n}' set to {h} units, {c} placed bins adjusted.", n=name, h=fmt(h), c=c))
            else:
                new_name = bump_name(name or binlib.next_bin_name(all_names()), all_names())
                color = free_color(st["types"])
                style = dict(group[0]["style"], h=h)
                c, k = change_style(p, st["bins"], group, style, color=color, name=new_name)
                if c:
                    st["types"].append(dict(style, nx=group[0]["ni"], ny=group[0]["nj"], name=new_name, color=color))
                    msgs.append(T("Bin set to {h} units and saved as new type '{n}'.", h=fmt(h), n=new_name)
                                if c == 1 else T("{c} bins set to {h} units and saved as new type '{n}'.", c=c,
                                                 h=fmt(h), n=new_name))
            log.info("Height of %d selected bins of %s -> %s HE (%d changed, %d unchanged)", len(group), name or "?",
                     fmt(h), c, k)
            changed, kept = changed + c, kept + k
        if not changed and kept:
            msgs.append(T("Not possible: {e}.", e=T("the new height would collide with stacked bins")))
        elif kept:
            msgs.append(T("{k} stayed unchanged because the new height would collide with stacked bins.", k=kept))
        k = next((n for n, x in enumerate(st["types"]) if x["name"] == bs[0].get("name")), None)
        fill_types_list(select=k)
        st["sel_bins"] = bs
        status.set(" ".join(msgs))

    def show_real():
        """Show the real height next to the units when the typed mm differ from it."""
        try:
            h, mm = w.number(he_var), w.number(mm_var)
        except ValueError:
            h_real.configure(text="")
            return
        real = h * binlib.UNIT_H
        h_real.configure(text=f"= {fmt(real)} mm" if abs(real - mm) > 1e-6 else "")

    def mm_to_units(mm):
        return math.ceil(mm / (binlib.UNIT_H / 2) - 1e-6) / 2

    def on_mm(*_):
        """mm typed: take the next larger half unit, leave the typed mm as they are."""
        if st["he_sync"]:
            return
        try:
            mm = w.number(mm_var)
            ok = mm > 0
        except ValueError:
            ok = False
        w.mark(mm_spin, not ok and bool(mm_var.get().strip()))
        if ok:
            st["he_sync"] = True
            try:
                he_var.set(fmt(mm_to_units(mm)))
            finally:
                st["he_sync"] = False
        show_real()

    def sync_mm(*_):
        """Units changed: set the mm field to that height, unless the typed mm already lead to it."""
        if st["he_sync"]:
            show_real()
            return
        try:
            h = w.number(he_var)
        except ValueError:
            show_real()
            return
        try:
            keep = abs(mm_to_units(w.number(mm_var)) - h) < EPS
        except ValueError:
            keep = False
        if not keep:
            st["he_sync"] = True
            try:
                mm_var.set(fmt(h * binlib.UNIT_H))
            finally:
                st["he_sync"] = False
        w.mark(mm_spin, False)
        show_real()

    he_var.trace_add("write", on_height)
    he_var.trace_add("write", sync_mm)
    mm_var.trace_add("write", on_mm)

    def save_layout():
        if st["folder"]:
            try:
                projects.save_layout(st["folder"], st["bins"])
            except OSError as e:
                status.set(T("Layout could not be saved: {e}", e=e))
        w.set_info(info, summary(st["plan"], st["bins"]) if st["plan"] else "")
        update_levels()
        remember()

    def drawer_limit():
        """Drawer height from the field; empty = no limit, invalid is marked red and ignored."""
        txt = drawer_var.get().strip()
        if not txt:
            w.mark(drawer_spin, False)
            return None
        try:
            h = w.number(drawer_var)
            ok = h > 0
        except ValueError:
            ok = False
        w.mark(drawer_spin, not ok)
        return h if ok else None

    def on_drawer(*_):
        if st["drawer_loading"]:
            return
        limit = drawer_limit()
        if st["folder"] and (limit or not drawer_var.get().strip()):
            try:
                projects.save_drawer_height(st["folder"], limit)
            except OSError as e:
                status.set(T("Layout could not be saved: {e}", e=e))
        update_levels()

    def update_levels():
        lv = stack_levels(st["bins"])
        lvl_info.configure(text=T("Stacking surfaces: {v}", v=", ".join(f"{fmt(x)} HE" for x in lv) or T("none")))
        p = st["plan"]
        if not p:
            top_value.configure(text="–", foreground="#111827")
            for lbl in info_lines.values():
                lbl.pack_forget()
            return
        mm, b = highest(p, st["bins"])
        limit = drawer_limit()
        too_high = bool(limit) and mm > limit + EPS
        top_value.configure(text=f"{mm:.1f} mm", foreground=theme.ERROR if too_high else "#111827")
        if b is None:
            part = T("only the baseplate")
        else:
            part = T("{n}, top at {z} units", n=b.get("name") or "?", z=fmt(b["z"] + b["style"]["h"]))
            part += " " + T("+ stacking lip") if b["style"]["lip"] else ""
        lines = {"part": (part, theme.MUTED)}
        note = floating_note(st["bins"])
        if note:
            lines["floating"] = (note, theme.ERROR)
        if limit:
            lines["drawer"] = ((T("Drawer {m} mm: {d} mm too high!", m=fmt(limit), d=f"{mm - limit:.1f}"), theme.ERROR)
                               if too_high else
                               (T("Drawer {m} mm: {d} mm left", m=fmt(limit), d=f"{limit - mm:.1f}"), "#15803d"))
            z = level()
            room = limit - seat_height(p.get("style", "thin")) - z * binlib.UNIT_H
            fits = math.floor((room - binlib.LIP_TOP) / (binlib.UNIT_H / 2) + 1e-6) / 2
            if fits >= binlib.min_height(True, 0.8):
                txt = T("Above level {z} units: {r} mm up to the drawer top, bins up to {h} units fit "
                        "(with stacking lip).", z=fmt(z), r=f"{room:.1f}", h=fmt(fits))
            else:
                txt = T("Above level {z} units: only {r} mm up to the drawer top, no bin fits there.",
                        z=fmt(z), r=f"{max(room, 0):.1f}")
            lines["room"] = (txt, "#111827")
        else:
            lines["room"] = (T("Enter the drawer height to see how much room is left above each level."),
                             theme.MUTED)
        for key, lbl in info_lines.items():
            lbl.pack_forget()
            if key in lines:
                lbl.configure(text=lines[key][0], foreground=lines[key][1])
                lbl.pack(anchor="w", fill="x", padx=8, pady=(1, 6 if key == "room" else 0))

    def jump(direction):
        stops = sorted({0.0, *stack_levels(st["bins"]), *(round(b["z"], 3) for b in floating(st["bins"]))})
        cur = level()
        nxt = [s for s in stops if s > cur + EPS] if direction > 0 else [s for s in stops if s < cur - EPS]
        if nxt:
            level_var.set(fmt(nxt[0] if direction > 0 else nxt[-1]))

    lvl_up.configure(command=lambda: jump(1))
    lvl_down.configure(command=lambda: jump(-1))

    def refresh(force=False):
        """Re-read the project list; force: reload the open project (baseplate changed)."""
        before = plist.get()
        plist.set_items(projects.list_projects())
        if force and plist.get() == before:
            open_project(before)

    def select_project(name):
        refresh()
        if plist.get() == name:
            open_project(name)
        else:
            plist.select(name)

    def open_project(name):
        st.update(plan=None, folder=None, name=None, bins=[], sel_bins=[])
        status.set("")
        if name:
            folder = projects.project_dir(name)
            try:
                p = projects.load_project(folder)
            except Exception as e:  # noqa: BLE001 - a broken project must not break the tool
                log.exception("Project %s could not be loaded", folder)
                proj_info.configure(text=T("Error: {e}", e=e), style="Error.TLabel")
                redraw()
                return
            by_style = {tuple(t[k] for k in STYLE_KEYS): t["name"] for t in st["types"]}
            bins, dropped = [], 0
            for b in sorted(projects.load_layout(folder), key=lambda b: b.get("z", 0.0)):
                try:
                    b.setdefault("z", 0.0)
                    if not b.get("name"):   # older layouts: name of the type with the same style
                        b["name"] = by_style.get(tuple(b["style"].get(k) for k in STYLE_KEYS), "")
                    if check(p, bins, b["i"], b["j"], b["ni"], b["nj"], b["z"], b["style"]["h"]) is None:
                        bins.append(b)
                    else:
                        dropped += 1
                except (KeyError, TypeError):
                    dropped += 1
            if dropped:
                log.warning("%s: %d bins no longer fit the grid and were removed", name, dropped)
                status.set(T("{n} bins no longer fit the changed grid and were removed.", n=dropped))
            st.update(plan=p, folder=folder, name=name, bins=bins)
            st["drawer_loading"] = True
            limit = projects.load_drawer_height(folder)
            drawer_var.set(fmt(limit) if limit else "")
            st["drawer_loading"] = False
            log.info("Project %s loaded: %d x %d cells, %d bins", name, len(p["cols"]), len(p["rows"]), len(bins))
            px, py = partial_widths(p)
            none = T("none")
            proj_info.configure(style="Muted.TLabel", text=T(
                "Drawer {w} x {d} mm, {x} x {y} cells\nPartial cells: X {px}, Y {py}", w=fmt(p["width"]),
                d=fmt(p["depth"]), x=len(p["cols"]), y=len(p["rows"]),
                px=f"{fmt(px)} mm" if px else none, py=f"{fmt(py)} mm" if py else none))
            if dropped:
                save_layout()
        else:
            proj_info.configure(style="Muted.TLabel", text=T("First create a project in the Baseplate tab."))
            st["drawer_loading"] = True
            drawer_var.set("")
            st["drawer_loading"] = False
        w.set_info(info, summary(st["plan"], st["bins"]) if st["plan"] else "")
        update_levels()
        show_height()
        st["hist"], st["redo"] = [], []
        remember()
        redraw()

    def resize_placed(targets, old, t):
        """Placed bins of a type follow its new size (rotated ones turned). Returns how many had no room."""
        failed = 0
        for b in targets:
            turned = (b["ni"], b["nj"]) != (old["nx"], old["ny"]) and (b["ni"], b["nj"]) == (old["ny"], old["nx"])
            ni, nj = (t["ny"], t["nx"]) if turned else (t["nx"], t["ny"])
            if (ni, nj) != (b["ni"], b["nj"]) and resize(st["plan"], st["bins"], b, b["i"], b["j"], ni, nj, apply=True):
                failed += 1
        return failed

    def add_type(t, old=None):
        """Type from the Bin tab: new, or an update of the type with the same name. old: name of the edited
        type if it was renamed in the Bin tab."""
        t = dict(t)
        renamed = next((x for x in st["types"] if old and old != t["name"] and x["name"] == old), None)
        if renamed is not None and not rename_type(renamed, t["name"]):
            return
        same = next((x for x in st["types"] if x["name"] == t["name"]), None)
        if same:   # same name -> update the type, keep its colour and export setting, adjust its placed bins
            t["color"] = same["color"]
            t.pop("export", None)
            if not exported(same):
                t["export"] = False
            k = st["types"].index(same)
            st["types"][k] = t
            targets = [b for b in st["bins"] if b.get("name") == t["name"]]
            changed, kept = change_style(st["plan"], st["bins"], targets, style_of(t), color=t["color"]) \
                if st["plan"] else (0, 0)
            no_room = resize_placed(targets, same, t) if st["plan"] else 0
            log.info("Bin type updated: %s (%s), %d placed changed, %d unchanged, %d without room for the size",
                     t["name"], type_details(t), changed, kept, no_room)
            msg = T("Type '{n}' updated, {c} placed bins adjusted.", n=t["name"], c=changed)
            if kept:
                msg += " " + T("{k} stayed unchanged because the new height would collide with stacked bins.",
                               k=kept)
            if no_room:
                msg += " " + T("{k} kept their old size, there is no room for the new one.", k=no_room)
            status.set(msg)
            save_layout()
        else:
            t["color"] = free_color(st["types"])
            st["types"].append(t)
            k = len(st["types"]) - 1
            log.info("New bin type: %s (%s)", t["name"], type_details(t))
            status.set(T("Type '{n}' added.", n=t["name"]))
        st["sel_bins"] = []
        fill_types_list(select=k)
        redraw()

    def edit_type():
        t = sel_type()
        if t and app:
            app.edit_bin_type(dict(t, **partial_of(t)))

    def partial_of(t):
        """Partial cells of the type as placed in this project (selected bin, else its first placed bin), so
        the Bin tab shows the real size. The Bin tab knows one partial cell per axis, more fall back to whole."""
        b = next((x for x in st["sel_bins"] + st["bins"] if x.get("name") == t["name"]), None)
        if b is None or not st["plan"]:
            return {}
        wx, wy = bin_widths(st["plan"], b)
        if (b["ni"], b["nj"]) != (t["nx"], t["ny"]):   # placed rotated
            wx, wy = wy, wx
        out = {"project": st["name"]}
        for n, p, ws in (("nx", "px", wx), ("ny", "py", wy)):
            parts = [x for x in ws if abs(x - PITCH) > EPS]
            if len(parts) == 1:
                out[n], out[p] = len(ws) - 1, parts[0]
        return out

    def duplicate_type():
        t = sel_type()
        if not t:
            return
        new = dict(t, name=bump_name(t["name"], all_names()), color=free_color(st["types"]))
        st["types"].append(new)
        log.info("Bin type duplicated: %s -> %s", t["name"], new["name"])
        st["sel_bins"] = []
        fill_types_list(select=len(st["types"]) - 1)
        status.set(T("Type '{a}' duplicated as '{b}'.", a=t["name"], b=new["name"]))
        redraw()

    def remove_type():
        t = sel_type()
        if t:
            st["types"].remove(t)
            log.info("Bin type removed: %s", t["name"])
            fill_types_list()
            redraw()

    def start_rename(e):
        """Double-click on a type: edit its name in place (Enter = apply, Esc = cancel).
        On its detail row: size, infill and colour."""
        row = types_list.nearest(e.y)
        k = row_type(row)
        if k is None or k >= len(st["types"]):
            return
        if row % 2:
            return edit_details(k)
        if e.x >= check_x() - 4:   # fast clicks on the export box are no rename
            return "break"
        t = st["types"][k]
        select_type(k)
        types_list.see(type_row(k))   # the name row may be scrolled out when the detail row was clicked
        types_list.update_idletasks()
        box = types_list.bbox(type_row(k))
        if not box:   # row not visible
            return "break"
        x, y, _, hgt = box
        var = tk.StringVar(value=t["name"])
        ent = ttk.Entry(types_list, textvariable=var)
        ent.place(x=x + list_font().measure("  ■  "), y=y - 2, width=check_x() - x - list_font().measure("  ■  ") - 6,
                  height=hgt + 4)
        ent.select_range(0, "end")
        ent.icursor("end")
        ent.focus_set()
        done = {"v": False}

        def finish(apply, keep_open=True):
            if done["v"]:
                return "break"
            if apply and not rename_type(t, var.get().strip()) and keep_open:
                w.mark(ent, True)   # keep the field open so the name can be corrected
                return "break"
            done["v"] = True
            ent.destroy()
            return "break"

        ent.bind("<Return>", lambda _: finish(True))
        ent.bind("<KP_Enter>", lambda _: finish(True))
        ent.bind("<Escape>", lambda _: finish(False))
        ent.bind("<FocusOut>", lambda _: finish(True, keep_open=False))   # clicked elsewhere: invalid = cancel
        return "break"

    def edit_details(k):
        """Small editor over the detail row of type k: cells X x Y, infill (bins) and display colour."""
        t = st["types"][k]
        select_type(k)
        types_list.see(type_row(k) + 1)
        types_list.update_idletasks()
        box = types_list.bbox(type_row(k) + 1)
        if not box or st.get("detail_edit"):
            return "break"
        x, y, _, hgt = box
        bar = tk.Frame(types_list, background="white", highlightthickness=1, highlightbackground=theme.ACCENT)
        bar.place(x=x + 18, y=y - 4, width=types_list.winfo_width() - x - 24, height=hgt + 10)
        st["detail_edit"] = bar
        nx_v, ny_v = tk.StringVar(value=str(t["nx"])), tk.StringVar(value=str(t["ny"]))
        nx_s = w.spinbox(bar, nx_v, 1, 12, 1, width=3)
        nx_s.pack(side="left", padx=(2, 0))
        ttk.Label(bar, text="x", background="white").pack(side="left", padx=2)
        ny_s = w.spinbox(bar, ny_v, 1, 12, 1, width=3)
        ny_s.pack(side="left")
        fills = {T("solid"): "solid", T("hexagon"): "hex"}
        fill_v = tk.StringVar(value=T("hexagon") if t["fill"] == "hex" else T("solid"))
        if not is_plate(t):
            ttk.Combobox(bar, textvariable=fill_v, values=list(fills), state="readonly", width=11).pack(
                side="left", padx=(6, 0))
        color = {"v": t["color"]}
        swatch = tk.Label(bar, background=t["color"], width=3, cursor="hand2", relief="solid", borderwidth=1)
        swatch.pack(side="left", padx=(6, 0), fill="y", pady=2)
        w.tip(swatch, T("Display colour of the type (also the filament colour in the Bambu project)"))

        def pick(_=None):
            got = colorchooser.askcolor(color["v"], parent=root, title=T("Colour of '{n}'", n=t["name"]))
            if got and got[1]:
                color["v"] = got[1]
                swatch.configure(background=got[1])

        swatch.bind("<Button-1>", pick)

        def close(_=None):
            st["detail_edit"] = None
            bar.destroy()
            return "break"

        def apply(_=None):
            sizes = []
            for var, spin in ((nx_v, nx_s), (ny_v, ny_s)):
                try:
                    n = w.number(var)
                    good = 1 <= n <= 12 and abs(n - round(n)) < 1e-9
                except ValueError:
                    good = False
                w.mark(spin, not good)
                sizes.append(int(round(n)) if good else None)
            if None in sizes:
                status.set(T("Size: whole number from 1 to 12."))
                return "break"
            close()
            apply_details(t, sizes[0], sizes[1], fills.get(fill_v.get(), t["fill"]), color["v"])
            return "break"

        ttk.Button(bar, text="✓", width=3, style="Small.TButton", command=apply).pack(side="right", padx=2)
        ttk.Button(bar, text="✕", width=3, style="Small.TButton", command=close).pack(side="right")
        for wd in (bar, nx_s, ny_s):
            wd.bind("<Return>", apply)
            wd.bind("<KP_Enter>", apply)
            wd.bind("<Escape>", close)
        nx_s.focus_set()
        return "break"

    def apply_details(t, nx, ny, fill, color):
        """Size, infill and colour of a type; its placed bins follow."""
        old = dict(t)
        if (nx, ny, fill, color) == (old["nx"], old["ny"], old["fill"], old["color"]):
            return
        t.update(nx=nx, ny=ny, fill=fill, color=color)
        targets = [b for b in st["bins"] if b.get("name") == t["name"]]
        for b in targets:
            b["color"] = color
        changed, kept = change_style(st["plan"], st["bins"], targets, style_of(t), color=color) \
            if st["plan"] else (0, 0)
        no_room = resize_placed(targets, old, t) if st["plan"] else 0
        log.info("Type %s: %dx%d %s %s (%d placed changed, %d without room)", t["name"], nx, ny, fill, color,
                 changed, no_room)
        msg = T("Type '{n}' updated, {c} placed bins adjusted.", n=t["name"], c=len(targets) - no_room)
        if no_room:
            msg += " " + T("{k} kept their old size, there is no room for the new one.", k=no_room)
        status.set(msg)
        fill_types_list(select=st["types"].index(t))
        save_layout()
        redraw()

    def rename_type(t, new):
        """Rename a type and its placed bins in all projects. Returns False if the name is not allowed."""
        old = t["name"]
        if new == old:
            return True
        if not new:
            status.set(T("Name: please enter a name."))
            return False
        if new in all_names():
            status.set(T("Name: '{n}' is already in use.", n=new))
            return False
        t["name"] = new
        for b in st["bins"]:
            if b.get("name") == old:
                b["name"] = new
        others = 0
        for name in projects.list_projects():
            folder = projects.project_dir(name)
            if folder == st["folder"]:
                continue
            try:
                bins = projects.load_layout(folder)
                hits = [b for b in bins if isinstance(b, dict) and b.get("name") == old]
                if hits:
                    for b in hits:
                        b["name"] = new
                    projects.save_layout(folder, bins)
                    others += 1
            except Exception:  # noqa: BLE001 - one broken project must not stop the rename
                log.exception("Rename in project %s failed", name)
        log.info("Bin type renamed: %s -> %s (%d other projects adjusted)", old, new, others)
        fill_types_list(select=st["types"].index(t))
        save_layout()
        status.set(T("Type '{a}' renamed to '{b}'.", a=old, b=new))
        redraw()
        return True

    def type_size(t):
        return (t["ny"], t["nx"]) if rotated.get() else (t["nx"], t["ny"])

    def place(i, j, ni, nj, t):
        p, z = st["plan"], level()
        err = check(p, st["bins"], i, j, ni, nj, z, t["h"])
        if err:
            status.set(T("Not possible: {e}.", e=err))
            return None
        b = {"i": i, "j": j, "ni": ni, "nj": nj, "z": z, "color": t["color"], "name": t["name"],
             "style": style_of(t)}
        st["bins"].append(b)
        log.debug("Placed %s at (%d, %d) %dx%d, level %s", t["name"], i, j, ni, nj, z)
        return b

    def place_new(i, j, ni, nj, t):
        """Dragged area: new type of that size with its own name, based on the selected type's style."""
        err = check(st["plan"], st["bins"], i, j, ni, nj, level(), t["h"])
        if err:
            status.set(T("Not possible: {e}.", e=err))
            return None
        new = dict(style_of(t), nx=ni, ny=nj, name=binlib.next_name(all_names(), t.get("kind")),
                   color=free_color(st["types"]))
        st["types"].append(new)
        fill_types_list(select=len(st["types"]) - 1)
        status.set(T("New bin '{n}' ({x} x {y}) created.", n=new["name"], x=ni, y=nj))
        return place(i, j, ni, nj, new)

    def fill_empty():
        t, p = sel_type(), st["plan"]
        if not t or not p:
            return
        ni, nj = type_size(t)
        n = 0
        for j in range(len(p["rows"])):
            for i in range(len(p["cols"])):
                if check(p, st["bins"], i, j, ni, nj, level(), t["h"]) is None:
                    place(i, j, ni, nj, t)
                    n += 1
        status.set(T("{n} bins added.", n=n))
        save_layout()
        redraw()

    def remove_bin(b):
        lost = remove(st["bins"], b)
        st["sel_bins"] = [x for x in st["sel_bins"] if x in st["bins"]]
        log.debug("Removed %s (%d stacked bins lost their support)", b.get("name"), len(lost))
        if lost:
            status.set(T("Removed. {n} bins stacked on it now have nothing below them (red).", n=len(lost)))
        save_layout()
        show_height()
        redraw()

    def clear_level():
        z = level()
        here = [b for b in st["bins"] if abs(b["z"] - z) < EPS]
        if here and messagebox.askyesno(T("Combined Grid"), T("Remove all {n} bins on level {z} (including bins "
                                                              "stacked on them)?", n=len(here), z=fmt(z))):
            for b in here:   # deliberately removes the stacks too (unlike remove_bin)
                for x in [b] + resting_on(st["bins"], b):
                    if x in st["bins"]:
                        st["bins"].remove(x)
            st["sel_bins"] = []
            save_layout()
            show_height()
            redraw()

    def do_export():
        p = st["plan"]
        if not p or not st["bins"]:
            status.set(T("Place bins first."))
            return
        skip = skipped_types(st["types"])
        if all(b.get("name") in skip for b in st["bins"]) and not base_too.get():
            status.set(T("All placed types are placeholders: tick at least one type for the export."))
            return
        notes = [n for n in [floating_note(st["bins"]), height_note(p, st["bins"], drawer_limit())] if n] + \
            magnet_notes(p, st["bins"])
        if notes:
            log.info("Export hints: %s", " | ".join(notes))
            if not messagebox.askyesno(T("Note"), "\n\n".join(notes) + "\n\n" + T("Export anyway?")):
                return
        try:
            root.configure(cursor="watch")
            root.update()
            out, files, seconds, hints = export(p, st["bins"], projects.output_dir(st["name"]),
                                                with_base=base_too.get(), colors=type_colors.get(), skip=skip,
                                                singles=singles.get(), title=st["name"])
        except Exception as e:  # noqa: BLE001
            log.exception("Export failed")
            messagebox.showerror(T("Error"), T("Export failed: {e}\n\nDetails in the log:\n{l}", e=e,
                                               l=logging_setup.LOG_FILE))
            return
        finally:
            root.configure(cursor="")
        msg = T("{n} files created in:\n{f}\n\nOpen folder?", n=len(files), f=out)
        msg = T("Print time approx. {t} (rough estimate).", t=duration_text(seconds)) + "\n\n" + msg
        if hints:
            log.info("Export notes: %s", " | ".join(hints))
            msg = T("Note") + ": " + "\n\n".join(hints) + "\n\n" + msg
        if messagebox.askyesno(T("Done"), msg):
            os.startfile(out)

    w.tip(ttk.Button(trow, text=T("Remove type"), style="SmallDanger.TButton", command=remove_type),
          T("Deletes the type from the list. Bins already placed stay.")).pack(side="right")
    w.tip(ttk.Button(trow, text=T("Edit"), style="Small.TButton", command=edit_type),
          T("Loads the type into the Bin tab. Change it there and update it here, including all placed bins of "
            "this type.")).pack(side="right", padx=(0, 4))
    w.tip(ttk.Button(trow2, text=T("Duplicate"), style="Small.TButton", command=duplicate_type),
          T("Creates a copy of the selected type with a new name, e.g. to try a different height.")).pack(side="right")
    w.tip(ttk.Button(brow, text=T("Fill empty cells with type"), style="Small.TButton", command=fill_empty),
          T("Fills all free spots of this level with the selected type.")).pack(side="left", fill="x", expand=True)
    w.tip(ttk.Button(brow, text=T("Clear level"), style="SmallDanger.TButton", command=clear_level),
          T("Removes all bins of this level including stacked ones.")).pack(side="left", padx=(4, 0))
    w.tip(ttk.Button(brow, text="↶", width=3, style="Small.TButton", command=undo), T("Undo (Ctrl+Z)")).pack(
        side="left", padx=(4, 0))
    w.tip(ttk.Button(brow, text="↷", width=3, style="Small.TButton", command=redo), T("Redo (Ctrl+Y)")).pack(
        side="left", padx=(2, 0))
    info.pack(anchor="w", fill="both", expand=True, pady=(8, 0))
    drow = ttk.Frame(bottom)
    drow.pack(anchor="w", fill="x", pady=(0, 4))
    drawer_tip = T("Inside height of the drawer in mm. Optional: if set, the highest point turns red when "
                   "something is too high, and the export warns.")
    w.tip(ttk.Label(drow, text=T("Drawer height (mm):")), drawer_tip).pack(side="left")
    drawer_spin = w.tip(w.spinbox(drow, drawer_var, 10, 1000, 1, width=6), drawer_tip)
    drawer_spin.pack(side="left", padx=6)
    ttk.Label(drow, text=T("optional"), style="Muted.TLabel").pack(side="left")
    top_tip = T("Measured from the drawer floor to the top of the highest part, so you can compare it with "
                "the height of your drawer.")
    tbox = tk.Frame(bottom, background="#f3f5f8", highlightthickness=1, highlightbackground="#dde2e9")
    tbox.pack(anchor="w", fill="x", pady=(0, 6))
    trow_top = tk.Frame(tbox, background="#f3f5f8")
    trow_top.pack(anchor="w", fill="x", padx=8, pady=(6, 0))
    w.tip(tk.Label(trow_top, text=T("Highest point"), background="#f3f5f8", foreground=theme.MUTED,
                   font=(theme.FONT, 10)), top_tip).pack(side="left")
    top_value = w.tip(tk.Label(trow_top, text="", background="#f3f5f8", font=(theme.FONT, 14, "bold")), top_tip)
    top_value.pack(side="left", padx=(8, 0))
    info_lines = {}
    for key, bold in (("part", False), ("drawer", True), ("room", False), ("floating", True)):
        info_lines[key] = tk.Label(tbox, text="", background="#f3f5f8", justify="left", anchor="w",
                                   wraplength=w.LEFT_W - 40, font=(theme.FONT, 10, "bold" if bold else "normal"))
    w.tip(ttk.Checkbutton(bottom, text=T("Include baseplates"), variable=base_too),
          T("Also puts the project's baseplates and filler strips on their own print plates.")).pack(anchor="w")
    w.tip(ttk.Checkbutton(bottom, text=T("Type colours as filaments (AMS)"), variable=type_colors),
          T("In the Bambu project every type colour becomes its own filament, e.g. for the AMS. Baseplates use "
            "filament 1. Off: everything in one filament.")).pack(anchor="w")
    w.tip(ttk.Checkbutton(bottom, text=T("Single files"), variable=singles), T("Also writes every part as STL/3MF, the single print plates and a text summary into the folder 'Single files'. Off: only the assembly sheet and the file with all print plates.")).pack(anchor="w")
    w.tip(ttk.Button(bottom, text=T("Export print-ready (STL + 3MF)"), style="Accent.TButton", command=do_export),
          T("Ready-made print plates for your printer (everything lies flat, stacked bins too) and an assembly "
            "sheet (PDF) showing where every part goes. Saved in output/<project>.")).pack(
        fill="x", pady=(6, 0))

    # --- 2D grid -------------------------------------------------------------
    def redraw(*_):
        if view.get() == "3d":
            canvas.pack_forget()
            view3d.pack(fill="both", expand=True, pady=(8, 0))
            schedule_3d()
        else:
            view3d.pack_forget()
            canvas.pack(fill="both", expand=True, pady=(8, 0))
            draw()

    def draw(*_):
        canvas.delete("all")
        p = st["plan"]
        cw, ch = canvas.winfo_width(), canvas.winfo_height()
        if not p or cw < 50:
            canvas.create_text(cw / 2, ch / 2, text=T("No project loaded"), fill=theme.MUTED)
            return
        s = min((cw - 40) / p["width"], (ch - 60) / p["depth"])
        X = lambda x: 20 + x * s
        Y = lambda y: ch - 30 - y * s   # Y upwards
        st["geo"] = (s, X, Y)
        z = level()
        xe, ye = edges(p)
        canvas.create_rectangle(X(0), Y(0), X(p["width"]), Y(p["depth"]), outline="#b8bfca", dash=(4, 3))
        canvas.create_text(X(p["width"] / 2), Y(p["depth"]) - 11, text=T("top"), fill=theme.MUTED)
        canvas.create_text(X(p["width"] / 2), Y(0) + 13, text=T("bottom"), fill=theme.MUTED)
        for f in p["fillers"]:
            (x, y), (sx, sy) = f["pos"], f["size"]
            canvas.create_rectangle(X(x), Y(y), X(x + sx), Y(y + sy), fill="#cbd2db", outline="white")
        for i, wx in enumerate(p["cols"]):
            for j, wy in enumerate(p["rows"]):
                partial = abs(wx - PITCH) > EPS or abs(wy - PITCH) > EPS
                fill_col = "#eceef2" if z > EPS else ("#fdf3dc" if partial else "#f3f5f8")
                canvas.create_rectangle(X(xe[i]), Y(ye[j]), X(xe[i + 1]), Y(ye[j + 1]), fill=fill_col,
                                        outline="#dde2e9")
        for t in p["tiles"]:   # plate borders
            (x, y), (sx, sy) = t["pos"], t["size"]
            canvas.create_rectangle(X(x), Y(y), X(x + sx), Y(y + sy), outline="#a7b0bd", width=2)
        inset = max(1.5, 0.25 * s + 1)
        marked = highlighted()
        loose = floating(st["bins"])
        order = {"below": 0, "above": 1, "surface": 2, "blocked": 3, "current": 4}
        for b in sorted(st["bins"], key=lambda b: order[level_role(b, z)]):
            role = level_role(b, z)
            x0, x1 = X(xe[b["i"]]) + inset, X(xe[b["i"] + b["ni"]]) - inset
            y0, y1 = Y(ye[b["j"] + b["nj"]]) + inset, Y(ye[b["j"]]) - inset
            if role == "current":
                canvas.create_rectangle(x0, y0, x1, y1, fill=tint(b["color"], 0.45) if is_plate(b["style"])
                                        else b["color"], outline="white", width=2)
                if b["style"]["fill"] == "hex":
                    honeycomb(x0 + 4, y0 + 4, x1 - 4, y1 - 4, tint(b["color"], 0.5),
                              max(b["style"].get("hex_size", 7.0) / 2 * s, 6))
                label_bin(b, x0, y0, x1, y1, "white")
                dims(p, b, x0, y0, x1, y1)
            elif role == "blocked":   # solid red with dark hatching: must not look like any type colour
                canvas.create_rectangle(x0, y0, x1, y1, fill=RED, outline=BLOCKED_DARK, width=3)
                hatch(x0, y0, x1, y1, BLOCKED_DARK)
                label_bin(b, x0, y0, x1, y1, "white", T("up to {h} units", h=fmt(top(b))))
            elif role == "surface":
                canvas.create_rectangle(x0, y0, x1, y1, fill=tint(b["color"], 0.7), outline=b["color"], width=2,
                                        dash=(6, 3))
                label_bin(b, x0, y0, x1, y1, b["color"], T("Stacking surface"))
            elif role == "above":
                canvas.create_rectangle(x0, y0, x1, y1, outline=tint(b["color"], 0.4), dash=(2, 4))
            else:
                canvas.create_rectangle(x0, y0, x1, y1, outline="#bcc3cd", dash=(2, 4))
            if any(b is f for f in loose):   # nothing below: red frame, solid on its own level
                canvas.create_rectangle(x0 - 1, y0 - 1, x1 + 1, y1 + 1, outline=RED, width=3,
                                        dash=() if role == "current" else (4, 3))
            if any(b is m for m in marked):
                canvas.create_rectangle(x0 - 2, y0 - 2, x1 + 2, y1 + 2, outline=HIGHLIGHT, width=4)
        for x, y, _ in handles():
            canvas.create_rectangle(x - 4, y - 4, x + 4, y + 4, fill="white", outline="#1f2937", width=1.5)
        draw_ghost()

    def hatch(x0, y0, x1, y1, col, step=10):
        """Diagonal lines (45 degrees) inside a rectangle."""
        w_, h_ = x1 - x0, y1 - y0
        for d in np.arange(step, w_ + h_, step):
            ax, ay = (x0 + d, y0) if d <= w_ else (x1, y0 + d - w_)       # start on top / right edge
            bx, by = (x0, y0 + d) if d <= h_ else (x0 + d - h_, y1)       # end on left / bottom edge
            canvas.create_line(ax, ay, bx, by, fill=col, width=2)

    def honeycomb(x0, y0, x1, y1, col, r):
        """Hexagon outlines (circumradius r px) that fit completely inside a rectangle: marks hex bins."""
        dx, dy = np.sqrt(3) * r, 1.5 * r
        cols = int((x1 - x0 - dx / 2) // dx)   # room for the half-step shift of every second row
        rows = int((y1 - y0 - 2 * r) // dy) + 1
        if cols < 1 or rows < 1:
            return
        ox = x0 + (x1 - x0 - cols * dx - dx / 2) / 2 + dx / 2   # centre the pattern
        oy = y0 + (y1 - y0 - (rows - 1) * dy - 2 * r) / 2 + r
        corners = [(r * np.cos(a), r * np.sin(a)) for a in np.radians(np.arange(30, 390, 60))]
        for row in range(rows):
            for c in range(cols):
                cx, cy = ox + c * dx + (dx / 2 if row % 2 else 0), oy + row * dy
                canvas.create_polygon([v for u, w_ in corners for v in (cx + u, cy + w_)], fill="",
                                      outline=col, width=1)

    def label_bin(b, x0, y0, x1, y1, col, extra=None):
        bw, bh = x1 - x0, y1 - y0
        if min(bw, bh) < 22:
            return
        lines = [b.get("name") or ""] if bh > 44 and bw > 50 else []
        size = T("plate") if is_plate(b["style"]) else f"{fmt(b['style']['h'])} HE"
        lines.append(extra or f"{b['ni']}x{b['nj']}  {size}")
        canvas.create_text((x0 + x1) / 2, (y0 + y1) / 2, fill=col, font=(theme.FONT, 9, "bold"),
                           text="\n".join(x for x in lines if x), justify="center", width=max(bw - 18, 20))

    def dims(p, b, x0, y0, x1, y1):
        """Outer size at the bottom (width) and left (depth)."""
        wx, wy = bin_widths(p, b)
        if x1 - x0 > 40:
            canvas.create_text((x0 + x1) / 2, y1 - 7, text=fmt(sum(wx) - binlib.CLEAR), fill="white",
                               font=(theme.FONT, 7))
        if y1 - y0 > 40:
            canvas.create_text(x0 + 7, (y0 + y1) / 2, text=fmt(sum(wy) - binlib.CLEAR), fill="white",
                               font=(theme.FONT, 7), angle=90)

    def draw_ghost():
        canvas.delete("ghost")
        p, g = st["plan"], st["hover"]
        if p and st["ghosts"] and st["geo"] and view.get() == "2d":   # moving or pasting several
            rects, ok = st["ghosts"]
            _, X, Y = st["geo"]
            xe, ye = edges(p)
            for i, j, ni, nj in rects:
                i0, j0 = max(i, 0), max(j, 0)
                i1, j1 = min(i + ni, len(p["cols"])), min(j + nj, len(p["rows"]))
                if i1 > i0 and j1 > j0:
                    canvas.create_rectangle(X(xe[i0]), Y(ye[j1]), X(xe[i1]), Y(ye[j0]), tags="ghost", width=3,
                                            outline="#16a34a" if ok else theme.ERROR, dash=() if ok else (5, 3))
            return
        if not p or not g or not st["geo"] or view.get() != "2d":
            return
        i, j, ni, nj, h = g
        _, X, Y = st["geo"]
        xe, ye = edges(p)
        i0, j0 = max(i, 0), max(j, 0)
        i1, j1 = min(i + ni, len(p["cols"])), min(j + nj, len(p["rows"]))
        if i1 <= i0 or j1 <= j0:
            return
        if st["grab"]:
            ok = resize(p, st["bins"], st["grab"][0], i, j, ni, nj) is None
        else:
            ok = check(p, st["bins"], i, j, ni, nj, level(), h) is None
        canvas.create_rectangle(X(xe[i0]), Y(ye[j1]), X(xe[i1]), Y(ye[j0]), tags="ghost", width=3,
                                outline="#16a34a" if ok else theme.ERROR, dash=() if ok else (5, 3))

    def cell_at(e):
        p = st["plan"]
        if not p or not st["geo"]:
            return None
        s, X, Y = st["geo"]
        xe, ye = edges(p)
        i = int(np.searchsorted(xe, (e.x - 20) / s) - 1)
        j = int(np.searchsorted(ye, (Y(0) - e.y) / s) - 1)
        if 0 <= i < len(p["cols"]) and 0 <= j < len(p["rows"]):
            return i, j
        return None

    def cell_clamped(e):
        """Cell under the pointer, held inside the grid (for resizing)."""
        p = st["plan"]
        s, X, Y = st["geo"]
        xe, ye = edges(p)
        i = int(np.searchsorted(xe, (e.x - 20) / s) - 1)
        j = int(np.searchsorted(ye, (Y(0) - e.y) / s) - 1)
        return min(max(i, 0), len(p["cols"]) - 1), min(max(j, 0), len(p["rows"]) - 1)

    def handles():
        """(x, y, sides) of the resize handles of the selected bin; sides: l/r = left/right, b/t = bottom/top."""
        p = st["plan"]
        if len(st["sel_bins"]) != 1 or not p or not st["geo"] or view.get() != "2d":
            return []
        b = st["sel_bins"][0]
        _, X, Y = st["geo"]
        xe, ye = edges(p)
        x0, x1 = X(xe[b["i"]]), X(xe[b["i"] + b["ni"]])
        y0, y1 = Y(ye[b["j"]]), Y(ye[b["j"] + b["nj"]])   # y0 = bottom edge on screen
        xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
        return [(x0, y0, "lb"), (x1, y0, "rb"), (x0, y1, "lt"), (x1, y1, "rt"),
                (xm, y0, "b"), (xm, y1, "t"), (x0, ym, "l"), (x1, ym, "r")]

    def handle_at(e):
        return next((sides for x, y, sides in handles() if abs(e.x - x) <= 7 and abs(e.y - y) <= 7), None)

    GRAB_CURSOR = {"lb": "size_ne_sw", "rt": "size_ne_sw", "lt": "size_nw_se", "rb": "size_nw_se",
                   "l": "sb_h_double_arrow", "r": "sb_h_double_arrow", "t": "sb_v_double_arrow",
                   "b": "sb_v_double_arrow"}

    def line_at(e):
        """Nearest grid line (index into the cell edges) in X and Y under the pointer."""
        p = st["plan"]
        s, X, Y = st["geo"]
        xe, ye = edges(p)
        return (int(np.argmin(np.abs(np.asarray(xe) - (e.x - 20) / s))),
                int(np.argmin(np.abs(np.asarray(ye) - (Y(0) - e.y) / s))))

    def grab_span(e):
        """New footprint of the grabbed bin: the dragged sides snap to the nearest grid line, the others stay;
        at least one cell remains."""
        b, sides = st["grab"]
        kx, ky = line_at(e)
        i0, i1 = b["i"], b["i"] + b["ni"]   # edges of the bin
        j0, j1 = b["j"], b["j"] + b["nj"]
        if "l" in sides:
            i0 = min(kx, i1 - 1)
        if "r" in sides:
            i1 = max(kx, i0 + 1)
        if "b" in sides:
            j0 = min(ky, j1 - 1)
        if "t" in sides:
            j1 = max(ky, j0 + 1)
        return i0, j0, i1 - i0, j1 - j0

    def finish_resize(e):
        b = st["grab"][0]
        i, j, ni, nj = grab_span(e)
        st["grab"], st["hover"] = None, None
        if (i, j, ni, nj) == (b["i"], b["j"], b["ni"], b["nj"]):
            draw()
            return
        old_size = (b["ni"], b["nj"])
        err = resize(st["plan"], st["bins"], b, i, j, ni, nj, apply=True)
        if err:
            status.set(T("Not possible: {e}.", e=err))
            draw()
            return
        t = next((x for x in st["types"] if x["name"] == b.get("name")), None)
        if t and not any(x is not b and x.get("name") == t["name"] for x in st["bins"]):
            # only bin of its type here: the type takes the new size (keeping a rotated placement)
            turned = old_size != (t["nx"], t["ny"]) and old_size == (t["ny"], t["nx"])
            t["nx"], t["ny"] = (nj, ni) if turned else (ni, nj)
            msg = T("Type '{n}' resized to {x} x {y}.", n=t["name"], x=ni, y=nj)
        else:   # the other bins of the type keep their size: this one becomes a new type
            name = bump_name(b.get("name") or binlib.next_bin_name(all_names()), all_names())
            t = dict(b["style"], nx=ni, ny=nj, name=name, color=free_color(st["types"]))
            st["types"].append(t)
            b["name"], b["color"] = t["name"], t["color"]
            msg = T("Bin resized to {x} x {y} and saved as new type '{n}'.", x=ni, y=nj, n=name)
        log.info("Resized %s to (%d, %d) %dx%d", b["name"], i, j, ni, nj)
        fill_types_list(select=st["types"].index(t))
        st["sel_bins"] = [b]
        status.set(msg)
        save_layout()
        show_height()
        draw()

    def bin_at(c):
        """Bin of the current level at this cell."""
        if c is None:
            return None
        z = level()
        return next((b for b in st["bins"] if abs(b["z"] - z) < EPS and overlap_xy(b, c[0], c[1], 1, 1)), None)

    def span(a, b):
        (i0, j0), (i1, j1) = a, b
        return min(i0, i1), min(j0, j1), abs(i1 - i0) + 1, abs(j1 - j0) + 1

    def move_preview(di, dj):
        movers = st["move"]["bins"]
        ok = move(st["plan"], st["bins"], movers, di, dj) is None
        st["ghosts"] = ([(b["i"] + di, b["j"] + dj, b["ni"], b["nj"]) for b in movers], ok)
        draw_ghost()

    def finish_move(c):
        m = st["move"]
        st["move"], st["ghosts"] = None, None
        di, dj = c[0] - m["start"][0], c[1] - m["start"][1]
        err = move(st["plan"], st["bins"], m["bins"], di, dj, apply=True)
        if err:
            status.set(T("Not possible: {e}.", e=err))
        else:
            st["sel_bins"] = list(m["bins"])
            log.info("Moved %d bins by (%d, %d)", len(m["bins"]), di, dj)
            status.set(T("Moved.") if len(m["bins"]) == 1 else T("{n} bins moved.", n=len(m["bins"])))
            save_layout()
        show_height()
        draw()

    def copy_bins():
        bs = st["sel_bins"]
        if not bs:
            status.set(T("Select the bins to copy first."))
            return
        i0, j0 = min(b["i"] for b in bs), min(b["j"] for b in bs)
        st["clip"] = [dict(b, i=b["i"] - i0, j=b["j"] - j0, style=dict(b["style"])) for b in bs]
        status.set(T("{n} bins copied. Ctrl+V and click where the copy goes.", n=len(bs)))

    def start_paste():
        if not st["clip"]:
            status.set(T("Nothing copied yet: select bins and press Ctrl+C."))
            return
        st["paste"] = True
        status.set(T("Click where the copy goes (Esc cancels)."))

    def paste_items(c):
        z = level()
        return [dict(x, i=x["i"] + c[0], j=x["j"] + c[1], z=z, style=dict(x["style"])) for x in st["clip"]]

    def paste_error(items):
        placed = []
        for b in items:
            err = check(st["plan"], st["bins"] + placed, b["i"], b["j"], b["ni"], b["nj"], b["z"], b["style"]["h"])
            if err:
                return err
            placed.append(b)
        return None

    def paste_preview(c):
        items = paste_items(c)
        st["ghosts"] = ([(b["i"], b["j"], b["ni"], b["nj"]) for b in items], paste_error(items) is None)
        draw_ghost()

    def finish_paste(c):
        items = paste_items(c)
        err = paste_error(items)
        if err:
            status.set(T("Not possible: {e}.", e=err))
            return
        st["bins"] += items
        st["paste"], st["ghosts"], st["sel_bins"] = False, None, items
        log.info("Pasted %d bins at (%d, %d), level %s", len(items), c[0], c[1], fmt(level()))
        status.set(T("{n} bins added.", n=len(items)))
        save_layout()
        show_height()
        draw()

    def rename_bin(b, new):
        """Rename the double-clicked bin. The only bin of its type: the type is renamed. Other bins share
        the type (e.g. pasted copies): this bin leaves the group as a new type of its own."""
        old = b.get("name") or ""
        t = next((x for x in st["types"] if x["name"] == old), None)
        if t is not None and not any(x is not b and x.get("name") == old for x in st["bins"]):
            return rename_type(t, new)
        if new == old:
            return True
        if not new:
            status.set(T("Name: please enter a name."))
            return False
        if new in all_names():
            status.set(T("Name: '{n}' is already in use.", n=new))
            return False
        own = dict(b["style"], nx=b["ni"], ny=b["nj"], name=new, color=free_color(st["types"]))
        st["types"].append(own)
        b["name"], b["color"] = new, own["color"]
        st["sel_bins"] = [b]
        log.info("Bin %s renamed to %s and made its own type", old, new)
        status.set(T("Bin renamed to '{n}' and saved as its own type.", n=new))
        fill_types_list(select=len(st["types"]) - 1)
        save_layout()
        show_height()
        redraw()
        return True

    def rename_in_grid(e):
        """Double-click on a bin: rename it right there (Enter = apply, Esc = cancel)."""
        b = bin_at(cell_at(e))
        if b is None or st.get("renaming"):
            return
        st["renaming"] = True
        var = tk.StringVar(value=b.get("name") or "")
        ent = ttk.Entry(canvas, textvariable=var)
        win = canvas.create_window(e.x, e.y, window=ent, width=180)
        ent.select_range(0, "end")
        ent.icursor("end")
        ent.focus_set()
        done = {"v": False}

        def finish(apply, keep_open=True):
            if done["v"]:
                return "break"
            if apply and not rename_bin(b, var.get().strip()) and keep_open:
                w.mark(ent, True)
                return "break"
            done["v"] = True
            st["renaming"] = False
            canvas.delete(win)
            ent.destroy()
            canvas.focus_set()
            return "break"

        ent.bind("<Return>", lambda _: finish(True))
        ent.bind("<KP_Enter>", lambda _: finish(True))
        ent.bind("<Escape>", lambda _: finish(False))
        ent.bind("<FocusOut>", lambda _: finish(True, keep_open=False))

    def on_motion(e):
        sides = handle_at(e)
        if sides:
            st["hover"] = None
            canvas.configure(cursor=GRAB_CURSOR[sides])
            draw_ghost()
            return
        c = cell_at(e)
        if st["paste"]:
            if c is not None:
                paste_preview(c)
            canvas.configure(cursor="plus")
            return
        hit = bin_at(c)
        t = sel_type() if c is not None and not hit else None   # no type chosen: no preview
        st["hover"] = None if t is None else (c[0], c[1], *type_size(t), t["h"])
        canvas.configure(cursor="fleur" if hit else ("hand2" if c else ""))
        draw_ghost()

    def on_press(e):
        sides = handle_at(e)
        st["grab"] = (st["sel_bins"][0], sides) if sides else None
        st["press"] = None if sides else cell_at(e)
        st["move"], st["dragged"] = None, False
        b = None if sides or st["paste"] or e.state & 0x0004 else bin_at(st["press"])
        if b is not None:   # a drag from here moves the bin (with the other selected ones)
            st["move"] = {"start": st["press"], "bins": list(st["sel_bins"]) if b in st["sel_bins"] else [b]}

    def on_drag(e):
        if st["grab"]:
            st["hover"] = (*grab_span(e), st["grab"][0]["style"]["h"])
            draw_ghost()
            return
        if st["move"]:
            ci, cj = cell_clamped(e)
            st["hover"] = None
            move_preview(ci - st["move"]["start"][0], cj - st["move"]["start"][1])
            return
        c = cell_at(e)
        if st["press"] and c and (c != st["press"] or st.get("dragged")):
            st["dragged"] = True   # once dragged, going back to the start cell means a 1x1 bin
            st["hover"] = (*span(st["press"], c), draw_type()["h"])
            draw_ghost()

    def on_release(e):
        if st["grab"]:
            finish_resize(e)
            return
        if st["paste"]:
            c = cell_at(e)
            if c is not None:
                finish_paste(c)
            return
        if st["move"] and cell_clamped(e) != st["move"]["start"]:
            st["press"] = None
            finish_move(cell_clamped(e))
            return
        st["move"], st["ghosts"] = None, None
        a, c = st["press"], cell_at(e)
        st["press"] = None
        dragged, st["dragged"] = st.get("dragged") and a is not None and not bin_at(a), False
        t = sel_type()
        if a is None and c is None:   # click beside the grid: deselect
            deselect()
            return
        if a is None or c is None:
            return
        status.set("")
        ctrl = e.state & 0x0004
        if a == c and not dragged and bin_at(c):   # select a single bin, Ctrl+click adds or removes it
            b = bin_at(c)
            if not ctrl:
                st["sel_bins"] = [b]
            elif b in st["sel_bins"]:
                st["sel_bins"].remove(b)
            else:
                st["sel_bins"].append(b)
            k = next((n for n, x in enumerate(st["types"]) if x["name"] == b.get("name")), None)
            if k is not None:
                select_type(k)
            show_height()
            draw()
            return
        if ctrl:   # Ctrl only selects, it never places
            return
        if st["sel_bins"] and a == c and not dragged:   # click into a free cell while bins are selected: only deselect
            clear_selection()
            return
        st["sel_bins"], st["type_focus"] = [], False
        if t is None and a == c and not dragged:   # nothing chosen: a click only clicks
            draw()
            return
        if t is None:   # no type: a dragged area gets the Bin tab settings as a new type
            b = place_new(*span(a, c), free_type())
        else:
            b = place(c[0], c[1], *type_size(t), t) if a == c and not dragged else place_new(*span(a, c), t)
        if b:
            save_layout()
        show_height()
        draw()

    def on_enter(_):
        canvas.focus_set()
        if sel_type() is None and not st["sel_bins"]:
            show_height()   # the Bin tab settings may have changed meanwhile

    def on_right(e):
        b = bin_at(cell_at(e))
        if b:
            remove_bin(b)

    def on_key(e):
        ctrl = e.state & 0x0004
        if ctrl and e.keysym.lower() == "z":
            undo()
        elif ctrl and e.keysym.lower() == "y":
            redo()
        elif ctrl and e.keysym.lower() == "c":
            copy_bins()
        elif ctrl and e.keysym.lower() == "v":
            start_paste()
            on_motion(e)
        elif e.keysym == "Delete" and st["sel_bins"]:
            for b in list(st["sel_bins"]):
                if b in st["bins"]:   # may already be gone as stacked on another selected bin
                    remove_bin(b)
        elif e.char.lower() == "r" and not ctrl:
            rotated.set(not rotated.get())
            on_motion(e)

    def deselect(*_):
        """Click on the right side outside the grid: nothing stays selected."""
        if st["sel_bins"] or st["type_focus"]:
            clear_selection()

    canvas.bind("<Configure>", draw)
    for wd in (right, vbar):   # margins around the grid and the free part of the view bar
        wd.bind("<Button-1>", deselect, add="+")
    canvas.bind("<Motion>", on_motion)
    canvas.bind("<Leave>", lambda e: (st.update(hover=None), draw_ghost()))
    canvas.bind("<Double-Button-1>", rename_in_grid)
    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    canvas.bind("<Button-3>", on_right)
    canvas.bind("<Enter>", on_enter)
    canvas.bind("<Key>", on_key)

    def on_escape(_):
        """Esc anywhere in this tab (rename fields handle their own Esc first)."""
        try:
            shown = canvas.winfo_viewable() or view3d.winfo_viewable()
        except tk.TclError:   # tab rebuilt (language switch): this binding belongs to the old one
            return
        if shown:
            if st["paste"]:
                st["paste"], st["ghosts"] = False, None
                status.set("")
            clear_selection()

    root.bind("<Escape>", on_escape, add="+")
    types_list.bind("<<ListboxSelect>>", on_types_select)
    types_list.bind("<Double-Button-1>", start_rename)
    types_list.bind("<Button-1>", on_check_click)
    types_list.bind("<Configure>", on_list_resize, add="+")
    all_btn.bind("<Button-1>", lambda _: toggle_all())
    for key, fn in (("<Control-z>", undo), ("<Control-y>", redo), ("<Control-Z>", undo), ("<Control-Y>", redo)):
        types_list.bind(key, lambda _, f=fn: f())

    # --- 3D view -------------------------------------------------------------
    def schedule_3d(*_):
        if st["job3d"]:
            root.after_cancel(st["job3d"])
        st["job3d"] = root.after(150, build_3d)

    def build_3d():
        st["job3d"] = None
        p = st["plan"]
        if not p or view.get() != "3d":
            return
        try:
            root.configure(cursor="watch")
            root.update_idletasks()
            v, f, c, segs, lc = st["scene"].build(p, st["bins"], level(), highlight=highlighted(),
                                                   dim_others=dim_levels.get())
            log.debug("3D scene: %d triangles", len(f))
            view3d.set(v, f, c, lines=segs, line_colors=lc)
        except Exception as e:  # noqa: BLE001 - the preview must never block planning
            log.exception("3D view failed")
            status.set(T("3D view failed: {e}", e=e))
        finally:
            root.configure(cursor="")

    def on_level(*_):
        st["hover"] = None
        update_levels()
        if any(abs(b["z"] - level()) > EPS for b in st["sel_bins"]):
            st["sel_bins"] = [b for b in st["sel_bins"] if abs(b["z"] - level()) < EPS]
            show_height()
        redraw()

    level_var.trace_add("write", on_level)
    drawer_var.trace_add("write", on_drawer)
    view.trace_add("write", redraw)
    view.trace_add("write", lambda *_: show_dim_check())
    dim_levels.trace_add("write", redraw)
    search_var.trace_add("write", lambda *_: show_types())

    def show_dim_check():
        if view.get() == "3d":
            dim_check.pack(side="left", padx=(10, 0))
        else:
            dim_check.pack_forget()

    show_dim_check()

    def get_state():
        s = types_list.curselection()
        return {"project": plist.get(), "level": level_var.get(), "rotated": rotated.get(), "view": view.get(),
                "dim_levels": dim_levels.get(),
                "type": row_type(s[0]) if s else None, "base_too": base_too.get(), "type_colors": type_colors.get(),
                "singles": singles.get()}

    fill_types_list(select=state.get("type", 0))
    names = projects.list_projects()
    plist.current = state.get("project") if state.get("project") in names else None
    plist.set_items(names, keep=True)
    if plist.get() and st["plan"] is None:
        open_project(plist.get())
    redraw()
    return SimpleNamespace(refresh=refresh, add_type=add_type, select_project=select_project,
                           type_names=type_names, get_state=get_state)
