"""Bin tab: design a single bin with 3D preview, save it or send it to the planner."""

import math
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from types import SimpleNamespace

from .. import bins as binlib
from .. import logging_setup, paths, projects
from ..grid import PITCH, bump_name, fmt
from ..i18n import T
from ..planner import partial_widths
from . import widgets as w
from .viewer import View3D

log = logging_setup.get("bin_tab")


def build(parent, app=None, state=None):
    """Build the tab. Returns an object with refresh(), get_state() and load_type()."""
    root = parent.winfo_toplevel()
    state = state or {}
    vars_ = {k: tk.StringVar(value=state.get(k, d)) for k, d in (
        ("nx", "2"), ("ny", "1"), ("h", "6"), ("px", "0"), ("py", "0"),
        ("wall", "0.8"), ("hs", "7"), ("hw", "3"), ("dx", "1"), ("dy", "1"),
        ("out", os.path.normpath(paths.BIN_OUTPUT)))}
    taken = app.planner_type_names() if app else []
    kind = tk.StringVar(value=state.get("kind", "bin") if state.get("kind") in binlib.KINDS else "bin")
    grip = tk.StringVar(value=state.get("grip", "none") if state.get("grip") in binlib.GRIPS else "none")
    name = tk.StringVar(value=state.get("name") or binlib.next_name(taken, kind.get()))
    fill = tk.StringVar(value=state.get("fill", "solid"))
    lip = tk.BooleanVar(value=state.get("lip", True))
    floor_holes = tk.BooleanVar(value=state.get("floor", False))
    magnets = tk.BooleanVar(value=state.get("magnets", False))
    flat = tk.BooleanVar(value=state.get("flat", True))
    label_shelf = tk.BooleanVar(value=state.get("label", False))
    scoop = tk.BooleanVar(value=state.get("scoop", False))
    base_names = {binlib.base_label(k): k for k in binlib.BASES}
    base = tk.StringVar(value=binlib.base_label(state.get("base") if state.get("base") in binlib.BASES else "lite"))
    st = {"body": None, "info": None, "job": None, "edit": state.get("edit"), "sent": None, "loading": False,
          "syncing": False}

    frm, bottom, right = w.tab_layout(parent)
    frm.columnconfigure(1, weight=1)
    fields, labels = {}, {}

    def field(key, label, widget):
        fields[key], labels[key] = widget, label
        return widget

    def lab(r, text, tiptext, col=0, **kw):
        lbl = w.tip(ttk.Label(frm, text=text, **kw), tiptext)
        lbl.grid(row=r, column=col, sticky="w", pady=3, padx=(0, 10))
        return lbl

    # banner while editing a type from the planner
    banner = tk.Frame(frm, background="#fff7e0", highlightthickness=1, highlightbackground="#f2cf72")
    banner_lbl = tk.Label(banner, background="#fff7e0", foreground="#5b4500", justify="left", anchor="w",
                          wraplength=w.LEFT_W - 70)
    banner_lbl.pack(side="top", fill="x", padx=8, pady=(6, 0))

    def end_edit():
        """Stop editing and go back to the planner; changes made meanwhile are applied first."""
        if st.get("loaded") != snapshot() and current() is not None:
            do_send()
            return
        log.info("Editing of %s ended without changes", st["edit"])
        st["edit"] = None
        name.set(binlib.next_name(app.planner_type_names() if app else [], kind.get()))
        show_banner()
        if app:
            app.show_planner()

    w.tip(ttk.Button(banner, text=T("Stop editing"), style="Small.TButton", command=end_edit),
          T("Ends editing. Changes made meanwhile are applied to the type in the Combined Grid (Ctrl+Z there "
            "undoes them).")).pack(side="top", anchor="e", padx=8, pady=6)

    def show_banner():
        if st["edit"]:
            banner_lbl.configure(text=T("You are editing type '{n}' from the Combined Grid. 'Update type' applies "
                                        "the changes.", n=st["edit"]))
            banner.grid(row=0, column=0, columnspan=3, sticky="we", pady=(0, 8))
            send_btn.configure(text=T("Update type '{n}'", n=st["edit"]))
            if app:   # the banner makes the panel taller: grow the window if there is room
                root.after(100, app.fit_window)
        else:
            banner.grid_remove()
            send_btn.configure(text=T("Send to Combined Grid"))

    kind_tip = T("Bin: stackable box. Plate: flat plate on the feet, closes cells or is a lid on a bin.")
    lab(1, T("Kind"), kind_tip)
    krow = ttk.Frame(frm)
    krow.grid(row=1, column=1, columnspan=2, sticky="w", pady=3)
    for val, txt in (("bin", T("Bin")), ("plate", T("Plate"))):
        w.tip(ttk.Radiobutton(krow, text=txt, value=val, variable=kind), kind_tip).pack(side="left", padx=(0, 14))
    name_tip = T("Name of the bin. Shown in the Combined Grid and in the file name.")
    lab(2, T("Name"), name_tip)
    w.tip(field("name", T("Name"), w.entry(frm, name, 26)), name_tip).grid(row=2, column=1, columnspan=2,
                                                                          sticky="we", pady=3)
    w.heading(frm, T("Size")).grid(row=3, column=0, sticky="w", pady=(12, 4))
    part_tip = T("Additional shortened cell in mm (12 to 41), e.g. an edge strip. 0 = none.")
    lab(3, T("+ partial cell mm"), part_tip, col=2, style="Muted.TLabel").grid(pady=(12, 4))
    cell_tip = T("Size in grid cells of 42 mm. Half cells like 1.5 can be typed in.")
    for r, (k, pk, text) in enumerate((("nx", "px", T("Width X (cells)")), ("ny", "py", T("Depth Y (cells)"))), 4):
        lab(r, text, cell_tip)
        w.tip(field(k, text, w.spinbox(frm, vars_[k], 0, 6, 1)), cell_tip).grid(row=r, column=1, sticky="w", pady=3)
        w.tip(field(pk, f"{text} {T('partial cell')}", w.entry(frm, vars_[pk], 7)), part_tip).grid(
            row=r, column=2, sticky="w", pady=3)
    mm_tip = T("Height in mm without stacking lip, e.g. what you measured. The next larger height in units "
               "(steps of 3.5 mm) is used.")
    h_tip = T("Height in Gridfinity units (1 unit = 7 mm), without stacking lip. Sets the mm field to match.")
    lab(6, T("Height (mm)"), mm_tip)
    mm_var = tk.StringVar()
    mm_spin = w.tip(w.spinbox(frm, mm_var, 14, 280, 1), mm_tip)
    mm_spin.grid(row=6, column=1, sticky="w", pady=3)
    hbox = ttk.Frame(frm)
    hbox.grid(row=6, column=2, sticky="w", pady=3)
    w.tip(field("h", T("Height"), w.spinbox(hbox, vars_["h"], 2, 25, 0.5, width=5)), h_tip).pack(side="left")
    w.tip(ttk.Label(hbox, text=T("units")), h_tip).pack(side="left", padx=(4, 0))
    h_real = ttk.Label(hbox, text="", style="Muted.TLabel")
    h_real.pack(side="left", padx=(6, 0))
    w.tip(ttk.Checkbutton(frm, text=T("Stacking lip (stackable)"), variable=lip),
          T("Top rim the next bin locks into. Without it the bin is not stackable.")).grid(
        row=7, column=0, columnspan=2, sticky="w", pady=(4, 0))
    base_tip = T("Bottom of the bin (from gridfinity-rebuilt). 'lite' has hollow feet and needs the least "
                 "material; 'standard' is solid.")
    w.tip(ttk.Combobox(frm, textvariable=base, state="readonly", values=list(base_names), width=24),
          base_tip).grid(row=7, column=2, sticky="w", pady=(4, 0))

    # grids from the Baseplate tab: add their partial cells to the current bin
    proj_tip = T("Grids you sent from the Baseplate tab. Use them to take over their partial cells.")
    w.heading(frm, T("Grid from baseplate"), proj_tip).grid(row=8, column=0, columnspan=3, sticky="w", pady=(14, 4))
    plist = w.ProjectList(frm, lambda n: on_project(n), lambda n: app.projects_changed() if app else refresh(),
                          proj_tip)
    plist.grid(row=9, column=0, columnspan=3, sticky="we")
    zs_info = ttk.Label(frm, text="", style="Muted.TLabel")
    zs_info.grid(row=10, column=0, columnspan=3, sticky="w", pady=(4, 0))
    zs_btns = ttk.Frame(frm)
    zs_btns.grid(row=11, column=0, columnspan=3, sticky="we")
    zs_btns.columnconfigure(0, weight=1)

    def show_real():
        """Show the real height next to the units when the typed mm differ from it."""
        try:
            h, mm = w.number(vars_["h"]), w.number(mm_var)
        except ValueError:
            h_real.configure(text="")
            return
        real = h * binlib.UNIT_H
        h_real.configure(text=f"= {fmt(real)} mm" if abs(real - mm) > 1e-6 else "")

    def on_mm(*_):
        """mm typed: take the next larger half unit, leave the typed mm as they are."""
        if st["syncing"]:
            return
        try:
            mm = w.number(mm_var)
            ok = mm > 0
        except ValueError:
            ok = False
        w.mark(mm_spin, not ok)
        if ok:
            st["syncing"] = True
            try:
                vars_["h"].set(fmt(math.ceil(mm / (binlib.UNIT_H / 2) - 1e-6) / 2))
            finally:
                st["syncing"] = False
        show_real()

    def on_h(*_):
        """Units changed: set the mm field to that height."""
        if st["syncing"]:
            return
        try:
            h = w.number(vars_["h"])
        except ValueError:
            show_real()
            return
        st["syncing"] = True
        try:
            mm_var.set(fmt(h * binlib.UNIT_H))
        finally:
            st["syncing"] = False
        w.mark(mm_spin, False)
        show_real()

    def set_vals(**kw):
        for k, val in kw.items():
            vars_[k].set(fmt(val))

    def refresh():
        plist.set_items(projects.list_projects())
        # advance the default name if the planner already uses it
        taken = app.planner_type_names() if app else []
        if not st["edit"] and binlib.is_default_bin_name(name.get()) and name.get() in taken:
            name.set(binlib.next_name(taken, kind.get()))
        if st["body"] is not None:   # e.g. another printer: check the bed again
            schedule()

    def on_project(pname):
        for child in zs_btns.winfo_children():
            child.destroy()
        if not pname:
            zs_info.configure(text="")
            return
        try:
            p = projects.load_project(projects.project_dir(pname))
        except Exception as e:  # noqa: BLE001
            log.exception("Project %s could not be loaded", pname)
            zs_info.configure(text=T("Error: {e}", e=e), style="Error.TLabel")
            return
        px, py = partial_widths(p)
        none = T("none")
        zs_info.configure(style="Muted.TLabel", text=T("Grid {x} x {y} mm, partial cells: X {px}, Y {py}",
                                                       x=fmt(p["grid"][0]), y=fmt(p["grid"][1]),
                                                       px=f"{fmt(px)} mm" if px else none,
                                                       py=f"{fmt(py)} mm" if py else none))
        add_tip = T("Adds the partial cell to your current bin, making it larger. Click again to remove it.")
        one_tip = T("Makes a separate bin from this partial cell only (length stays adjustable).")
        st["toggles"] = []
        r = 0
        # (shown, which fields the partial cell occupies, labels for add/remove, values for 'single')
        for show, keys, add_text, remove_text, single in (
                (px, {"px": px}, T("+ Add edge strip X ({w} mm)", w=fmt(px)),
                 T("− Remove edge strip X ({w} mm)", w=fmt(px)), dict(nx=0, px=px, py=0)),
                (py, {"py": py}, T("+ Add edge strip Y ({w} mm)", w=fmt(py)),
                 T("− Remove edge strip Y ({w} mm)", w=fmt(py)), dict(ny=0, py=py, px=0)),
                (px and py, {"px": px, "py": py}, T("+ Add corner cell {x} x {y} mm", x=fmt(px), y=fmt(py)),
                 T("− Remove corner cell {x} x {y} mm", x=fmt(px), y=fmt(py)), dict(nx=0, px=px, ny=0, py=py))):
            if not show:
                continue
            b = w.tip(ttk.Button(zs_btns, text=add_text, style="Small.TButton",
                                 command=lambda k=keys: toggle_partial(k)), add_tip)
            b.grid(row=r, column=0, sticky="we", pady=2)
            st["toggles"].append((b, keys, add_text, remove_text))
            w.tip(ttk.Button(zs_btns, text=T("single"), style="Small.TButton", width=8,
                             command=lambda s=single: set_vals(**s)), one_tip).grid(row=r, column=1, sticky="we",
                                                                                   padx=(4, 0), pady=2)
            r += 1
        if r:
            w.tip(ttk.Button(zs_btns, text=T("Remove partial cells"), style="Small.TButton",
                             command=lambda: set_vals(px=0, py=0)),
                  T("Removes all partial cells from the current bin.")).grid(row=r, column=0, columnspan=2,
                                                                            sticky="we", pady=(2, 0))
        update_toggles()

    def current_partial(key):
        try:
            return w.number(vars_[key])
        except ValueError:
            return None

    def is_attached(keys):
        return all(current_partial(k) is not None and abs(current_partial(k) - v) < 1e-6 for k, v in keys.items())

    def toggle_partial(keys):
        """First click attaches the partial cell(s), the next click removes them again."""
        set_vals(**({k: 0 for k in keys} if is_attached(keys) else keys))

    def update_toggles(*_):
        for b, keys, add_text, remove_text in st.get("toggles", []):
            try:
                b.configure(text=remove_text if is_attached(keys) else add_text)
            except tk.TclError:   # button already replaced by another project
                pass

    w.heading(frm, T("Infill")).grid(row=12, column=0, sticky="w", pady=(14, 4))
    w.tip(ttk.Radiobutton(frm, text=T("Solid"), value="solid", variable=fill),
          T("Solid walls.")).grid(row=13, column=0, columnspan=2, sticky="w")
    w.tip(ttk.Radiobutton(frm, text=T("Hexagon cut-outs"), value="hex", variable=fill),
          T("Walls with hexagon holes: saves material and weight.")).grid(row=14, column=0, columnspan=2, sticky="w")
    hexw = []
    for i, (lbl, k, lo, hi, step, tp) in enumerate((
            (T("Hole size (mm)"), "hs", 3, 20, 0.5, T("Width across flats of the hexagons in mm.")),
            (T("Web (mm)"), "hw", 1, 10, 0.5, T("Material width between two holes in mm.")))):
        a = lab(15 + i, "    " + lbl, tp)
        b = w.tip(field(k, lbl, w.spinbox(frm, vars_[k], lo, hi, step)), tp)
        b.grid(row=15 + i, column=1, sticky="w", pady=3)
        hexw += [a, b]
    cb = w.tip(ttk.Checkbutton(frm, text=T("Also perforate floor"), variable=floor_holes),
               T("The floor gets hexagon holes too."))
    cb.grid(row=17, column=0, columnspan=2, sticky="w", padx=(20, 0))
    hexw.append(cb)

    w.heading(frm, T("Compartments and access")).grid(row=18, column=0, columnspan=3, sticky="w", pady=(14, 4))
    div_tip = T("Divides the bin into compartments: number in X and in Y (1 = no divider).")
    lab(19, T("Compartments X x Y"), div_tip)
    drow = ttk.Frame(frm)
    drow.grid(row=19, column=1, columnspan=2, sticky="w", pady=3)
    w.tip(field("dx", T("Compartments X"), w.spinbox(drow, vars_["dx"], 1, 8, 1, width=4)), div_tip).pack(side="left")
    ttk.Label(drow, text=" x ").pack(side="left")
    w.tip(field("dy", T("Compartments Y"), w.spinbox(drow, vars_["dy"], 1, 8, 1, width=4)), div_tip).pack(side="left")
    arow = ttk.Frame(frm)
    arow.grid(row=20, column=0, columnspan=3, sticky="w")
    w.tip(ttk.Checkbutton(arow, text=T("Label shelf"), variable=label_shelf),
          T("Shelf at the back for a label. The 45 degree underside prints without support.")).pack(side="left")
    w.tip(ttk.Checkbutton(arow, text=T("Scoop"), variable=scoop),
          T("Rounded ramp at the front of every compartment, so small parts slide out easily.")).pack(
        side="left", padx=(12, 0))

    w.heading(frm, T("Advanced")).grid(row=21, column=0, sticky="w", pady=(14, 4))
    wall_tip = T("Wall thickness. 0.8 mm = 2 lines with a 0.4 nozzle.")
    lab(22, T("Wall thickness (mm)"), wall_tip)
    w.tip(field("wall", T("Wall thickness"), w.spinbox(frm, vars_["wall"], 0.4, 1.8, 0.1)), wall_tip).grid(
        row=22, column=1, sticky="w", pady=3)
    mrow = ttk.Frame(frm)
    mrow.grid(row=23, column=0, columnspan=3, sticky="w", pady=(4, 0))
    flat_cb = w.tip(ttk.Checkbutton(mrow, text=T("Smooth floor"), variable=flat),
                    T("Closes the hollow feet at the top, so the inside floor is flat (lite base)."))
    flat_cb.pack(side="left")
    w.tip(ttk.Checkbutton(mrow, text=T("Magnet holes (6 x 2 mm)"), variable=magnets),
          T("Four holes per whole cell in the bottom for 6 x 2 mm magnets. Matches the 'skeletonized' and "
            "'weighted' baseplates.")).pack(side="left", padx=(12, 0))
    # plates: no height, infill, compartments or magnets, but a grip instead
    bin_only = [wd for r in (6, 12, 13, 14, 15, 16, 17, 18, 19, 20, 23) for wd in frm.grid_slaves(row=r)]
    grip_tip = T("Finger hole in the middle or a slot at the front to lift the plate.")
    plate_only = [w.heading(frm, T("Grip"), grip_tip)]
    plate_only[0].grid(row=12, column=0, sticky="w", pady=(14, 4))
    for i, g in enumerate(binlib.GRIPS):
        rb = w.tip(ttk.Radiobutton(frm, text=binlib.grip_label(g), value=g, variable=grip), grip_tip)
        rb.grid(row=13 + i, column=0, columnspan=2, sticky="w")
        plate_only.append(rb)

    def show_kind(*_):
        plate = kind.get() == "plate"
        for wd in bin_only:
            wd.grid_remove() if plate else wd.grid()
        for wd in plate_only:
            wd.grid() if plate else wd.grid_remove()
        if not st["loading"] and st.get("kind_shown") not in (None, kind.get()):
            lip.set(not plate)   # plates are flat unless asked for, bins stackable
        st["kind_shown"] = kind.get()
        nm = name.get()
        if binlib.is_default_bin_name(nm) and not st["edit"]:   # default names follow the kind
            new = binlib.next_name(app.planner_type_names() if app else [], kind.get())
            if (T("Plate {n}").split("{n}")[0] in nm) != plate:
                name.set(new)

    out_tip = T("The single bin is saved here.")
    lab(24, T("Output folder"), out_tip)
    orow = ttk.Frame(frm)
    orow.grid(row=25, column=0, columnspan=3, sticky="we")

    def pick_out():
        d = filedialog.askdirectory()
        if d:
            vars_["out"].set(os.path.normpath(d))

    w.tip(w.entry(orow, vars_["out"], 30), out_tip).pack(side="left", fill="x", expand=True)
    ttk.Button(orow, text="…", width=3, style="Small.TButton", command=pick_out).pack(side="left", padx=(4, 0))

    info = w.info_text(frm, 11)
    info.grid(row=26, column=0, columnspan=3, sticky="we", pady=(14, 0))

    view = View3D(right)
    view.pack(fill="both", expand=True)

    def validate():
        """Check the inputs. Returns (parameters or None, error messages); marks fields red."""
        errs, v = {}, {}
        plate = kind.get() == "plate"
        bin_keys = ("h", "hs", "hw", "dx", "dy")   # hidden for plates
        for k in ("nx", "ny", "px", "py", "wall") + (() if plate else bin_keys):
            try:
                v[k] = w.number(vars_[k])
            except ValueError as e:
                errs[k] = str(e)
        if plate:
            v.update(h=binlib.PLATE_H, hs=7.0, hw=3.0, dx=1, dy=1)
        for k in ("dx", "dy"):
            if k in v and not (1 <= v[k] <= 8 and abs(v[k] - round(v[k])) < 1e-9):
                errs[k] = T("Whole number from 1 to 8.")
        for nk, pk in (("nx", "px"), ("ny", "py")):
            n, p = v.get(nk), v.get(pk)
            if n is not None:
                if n < 0:
                    errs[nk] = T("Must not be negative.")
                elif abs(n * 2 - round(n * 2)) > 1e-6:
                    errs[nk] = T("Whole or half cells only (e.g. 1 or 1.5).")
                elif n > 12:
                    errs[nk] = T("At most 12 cells.")
            if p is not None:
                if p < 0:
                    errs[pk] = T("Must not be negative.")
                elif 0 < p < binlib.MIN_PARTIAL:
                    errs[pk] = T("Partial cell at least {m} mm (or 0 for none).", m=fmt(binlib.MIN_PARTIAL))
                elif p >= PITCH:
                    errs[pk] = T("Partial cell must be smaller than {m} mm, otherwise use whole cells.", m=fmt(PITCH))
            if n is not None and p is not None and nk not in errs and pk not in errs and n < 0.5 and p == 0:
                errs[nk] = T("Enter at least 0.5 cells or a partial cell.")
        if "wall" in v and not 0.4 <= v["wall"] <= 1.8:
            errs["wall"] = T("Please between 0.4 and 1.8 mm.")
        if not plate and "h" in v and "wall" in v and "wall" not in errs:
            hmin = binlib.min_height(lip.get(), v["wall"])
            if v["h"] < hmin:
                errs["h"] = T("At least {h} units.", h=fmt(hmin))
            elif v["h"] > 40:
                errs["h"] = T("At most 40 units.")
            elif abs(v["h"] * 2 - round(v["h"] * 2)) > 1e-6:
                errs["h"] = T("Whole or half units only.")
        if fill.get() == "hex" and not plate:
            if "hs" in v and not 3 <= v["hs"] <= 20:
                errs["hs"] = T("Please between 3 and 20 mm.")
            if "hw" in v and not 1 <= v["hw"] <= 10:
                errs["hw"] = T("Please between 1 and 10 mm.")
        if not name.get().strip():
            errs["name"] = T("Please enter a name.")
        for k, wid in fields.items():
            w.mark(wid, k in errs)
        msgs = [f"{labels[k].strip()}: {m}" for k, m in errs.items()]
        if errs:
            return None, msgs
        if plate:
            return dict(nx=v["nx"], ny=v["ny"], px=v["px"], py=v["py"], h=binlib.PLATE_H, fill="solid",
                        lip=lip.get(), wall=v["wall"], hex_size=7.0, hex_web=3.0, hex_floor=False,
                        base=base_names.get(base.get(), "lite"), magnets=False, kind="plate", grip=grip.get(),
                        div_x=1, div_y=1, label=False, scoop=False, flat=True), msgs
        return dict(nx=v["nx"], ny=v["ny"], px=v["px"], py=v["py"], h=v["h"], fill=fill.get(), lip=lip.get(),
                    wall=v["wall"], hex_size=v["hs"], hex_web=v["hw"], hex_floor=floor_holes.get(),
                    base=base_names.get(base.get(), "lite"), magnets=magnets.get(), kind="bin", grip="none",
                    div_x=int(round(v["dx"])), div_y=int(round(v["dy"])), label=label_shelf.get(),
                    scoop=scoop.get(), flat=flat.get()), msgs

    def rebuild():
        st["job"] = None
        lite = base_names.get(base.get(), "lite") == "lite"
        for wid in hexw:
            if wid.winfo_class() in ("TLabel",):
                wid.configure(style="TLabel" if fill.get() == "hex" else "Muted.TLabel")
            else:   # a smooth floor has no holes
                on = fill.get() == "hex" and (wid is not cb or (lite and not flat.get()))
                wid.state(["!disabled"] if on else ["disabled"])
        flat_cb.state(["!disabled"] if lite else ["disabled"])   # standard is always flat
        p, msgs = validate()
        if p is None:
            st["body"] = None
            w.set_info(info, errors=msgs)
            return
        try:
            root.configure(cursor="watch")
            root.update_idletasks()
            body, inf = binlib.build_bin(**p)
        except ValueError as e:   # a rule validate() does not know
            log.debug("Invalid bin: %s", e)
            st["body"] = None
            w.set_info(info, errors=[str(e)])
            return
        except Exception as e:  # noqa: BLE001 - a real error: log and show
            log.exception("Building the bin failed with %s", p)
            st["body"] = None
            w.set_info(info, errors=[T("Error: {e}", e=e)])
            return
        finally:
            root.configure(cursor="")
        st["body"], st["info"] = body, inf
        w.set_info(info, binlib.summary(inf))
        v, f = binlib.mesh_arrays(body)
        segs, cols = binlib.grid_lines(*inf["widths"])
        view.set(v, f, lines=segs, line_colors=cols)

    def snapshot():
        d = {k: vars_[k].get() for k in vars_ if k != "out"}
        d.update(fill=fill.get(), lip=lip.get(), floor=floor_holes.get(), base=base.get(), magnets=magnets.get(),
                 label=label_shelf.get(), scoop=scoop.get(), kind=kind.get(), grip=grip.get(), flat=flat.get())
        return d

    def schedule(*_):
        # after sending to the planner, any further change gets a new name
        if not st["loading"] and not st["edit"] and st["sent"] and name.get() == st["sent"][0] \
                and snapshot() != st["sent"][1]:
            name.set(bump_name(name.get(), app.planner_type_names() if app else []))
            st["sent"] = None
        if st["job"]:
            root.after_cancel(st["job"])
        st["job"] = root.after(300, rebuild)

    def current():
        if st["job"]:
            root.after_cancel(st["job"])
            rebuild()
        return st["body"]

    def do_save():
        if current() is None:
            messagebox.showwarning(T("Note"), T("Please fix the fields marked in red first."))
            return
        try:
            files = binlib.export(st["body"], st["info"], vars_["out"].get(), name.get())
        except Exception as e:  # noqa: BLE001
            log.exception("Saving failed")
            messagebox.showerror(T("Error"), T("Saving failed: {e}\n\nDetails in the log:\n{l}",
                                               e=e, l=logging_setup.LOG_FILE))
            return
        if messagebox.askyesno(T("Done"), T("Saved:\n{f}\n\nin {d}\n\nOpen folder?",
                                            f="\n".join(os.path.basename(x) for x in files),
                                            d=os.path.dirname(files[-1]))):
            os.startfile(os.path.dirname(files[-1]))

    def do_send():
        """Send the current settings as a bin type to the planner (or update the edited type)."""
        if current() is None or app is None:
            if st["body"] is None:
                messagebox.showwarning(T("Note"), T("Please fix the fields marked in red first."))
            return
        p, _ = validate()
        # in the planner a partial cell counts as one cell; its width comes from the grid
        nx = math.ceil(p["nx"] - 1e-9) + (1 if p["px"] > 0 else 0)
        ny = math.ceil(p["ny"] - 1e-9) + (1 if p["py"] > 0 else 0)
        if nx != p["nx"] + (1 if p["px"] > 0 else 0) or ny != p["ny"] + (1 if p["py"] > 0 else 0):
            messagebox.showinfo(T("Note"), T("The Combined Grid has no half cells, the type is taken over as "
                                             "{x} x {y} cells.", x=nx, y=ny))
        style = {k: p[k] for k in binlib.STYLE_KEYS}
        nm = name.get().strip()
        app.add_bin_type(dict(style, nx=nx, ny=ny, name=nm), st["edit"])
        st["edit"] = None
        st["sent"] = (nm, snapshot())
        show_banner()

    def load_type(t):
        """Load a type from the planner for editing."""
        st["loading"] = True
        try:
            set_vals(nx=t["nx"], ny=t["ny"], px=t.get("px", 0), py=t.get("py", 0), h=t["h"], wall=t["wall"],
                     hs=t["hex_size"], hw=t["hex_web"], dx=t.get("div_x", 1), dy=t.get("div_y", 1))
            label_shelf.set(t.get("label", False))
            scoop.set(t.get("scoop", False))
            kind.set(t.get("kind", "bin"))
            grip.set(t.get("grip", "none"))
            if t.get("px") or t.get("py"):   # show the grid the partial cell comes from
                plist.select(t["project"])
            fill.set(t["fill"])
            lip.set(t["lip"])
            base.set(binlib.base_label(t.get("base", "lite")))
            magnets.set(t.get("magnets", False))
            flat.set(t.get("flat", True))
            floor_holes.set(t["hex_floor"])
            name.set(t["name"])
            st["edit"], st["sent"] = t["name"], None
        finally:
            st["loading"] = False
        st["loaded"] = snapshot()   # "Stop editing" applies changes made after this
        show_banner()
        schedule()
        log.info("Type %s loaded for editing", t["name"])

    def current_style():
        """Style of the current settings for the planner, None while fields are invalid."""
        p, _ = validate()
        return {k: p[k] for k in binlib.STYLE_KEYS} if p else None

    send_btn = w.tip(ttk.Button(bottom, text=T("Send to Combined Grid"), command=do_send),
                     T("Adds the bin as a type to the Combined Grid. Settings changed afterwards automatically get "
                       "a new name."))
    send_btn.pack(fill="x")
    w.tip(ttk.Button(bottom, text=T("Save (STL + 3MF)"), style="Accent.TButton", command=do_save),
          T("Saves this one bin as STL and 3MF.")).pack(fill="x", pady=(6, 0))

    def get_state():
        d = {k: v.get() for k, v in vars_.items()}
        d.update(name=name.get(), fill=fill.get(), lip=lip.get(), floor=floor_holes.get(), edit=st["edit"],
                 base=base_names.get(base.get(), "lite"), magnets=magnets.get(), label=label_shelf.get(),
                 scoop=scoop.get(), kind=kind.get(), grip=grip.get(), flat=flat.get())
        return d

    for k in ("nx", "ny", "px", "py", "h", "wall", "hs", "hw", "dx", "dy"):
        vars_[k].trace_add("write", schedule)
    for k in ("px", "py"):
        vars_[k].trace_add("write", update_toggles)
    for v_ in (fill, lip, floor_holes, base, magnets, label_shelf, scoop, kind, grip, flat):
        v_.trace_add("write", schedule)
    kind.trace_add("write", show_kind)
    show_kind()
    name.trace_add("write", lambda *_: validate())
    vars_["h"].trace_add("write", on_h)
    mm_var.trace_add("write", on_mm)
    on_h()
    show_banner()
    refresh()
    root.after(100, rebuild)
    return SimpleNamespace(refresh=refresh, get_state=get_state, load_type=load_type, current_style=current_style)
