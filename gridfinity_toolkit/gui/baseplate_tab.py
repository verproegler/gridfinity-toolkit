"""Baseplate tab: cut baseplates to a drawer and send the grid to the other tabs."""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from types import SimpleNamespace

from .. import i18n, logging_setup, paths, printers, projects
from ..baseplate import MIN_PARTIAL_LIMIT, STYLES, default_name, generate, plan, style_label, summary
from ..grid import PITCH, fmt, is_partial, safe_folder_name, tint
from ..i18n import T
from . import theme, widgets as w

log = logging_setup.get("baseplate_tab")

TILE_COLORS = ["#3b82f6", "#f59e0b", "#22c55e", "#ef4444", "#a855f7", "#14b8a6", "#ec4899", "#a16207"]


def build(parent, app=None, state=None):
    """Build the tab. Returns an object with get_state()."""
    root = parent.winfo_toplevel()
    state = state or {}
    vars_ = {k: tk.StringVar(value=state.get(k, d)) for k, d in (
        ("width", "500"), ("depth", "380"), ("tol", "1"), ("minp", "12"), ("out", os.path.normpath(paths.OUTPUT)))}
    pr_name, pr_custom = printers.printer_choice()
    custom_txt = T("Custom")
    printer = tk.StringVar(value=custom_txt if pr_name == printers.CUSTOM else pr_name)
    custom = tk.StringVar(value=state.get("custom", fmt(pr_custom)))
    name = tk.StringVar(value=state.get("name", ""))
    filler = tk.BooleanVar(value=state.get("filler", True))
    singles = tk.BooleanVar(value=state.get("singles", False))
    side_x = tk.StringVar(value=state.get("side_x", "end"))   # end = right, start = left
    side_y = tk.StringVar(value=state.get("side_y", "end"))   # end = top,   start = bottom
    auto = {"name": state.get("auto_name", "")}
    style_names = {style_label(k): k for k in STYLES}
    style = tk.StringVar(value=style_label(state.get("style", "thin") if state.get("style") in STYLES else "thin"))

    frm, bottom, right = w.tab_layout(parent)
    frm.columnconfigure(1, weight=1)
    fields, labels = {}, {}

    def row(r, key, text, tiptext, widget, pady=3):
        lbl = w.tip(ttk.Label(frm, text=text), tiptext)
        lbl.grid(row=r, column=0, sticky="w", pady=pady, padx=(0, 10))
        widget.grid(row=r, column=1, sticky="we", pady=pady)
        w.tip(widget, tiptext)
        fields[key], labels[key] = widget, text
        return widget

    w.heading(frm, T("Drawer")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
    row(1, "name", T("Name"), T("Project name. Used as folder name and shown in the Bin and Combined Grid tabs."),
        w.entry(frm, name, 28))
    row(2, "width", T("Width X (mm)"), T("Inner size of the drawer from left to right."), w.entry(frm, vars_["width"]))
    row(3, "depth", T("Depth Y (mm)"), T("Inner size of the drawer from bottom to top (in the picture)."),
        w.entry(frm, vars_["depth"]))
    row(4, "tol", T("Total tolerance (mm)"), T("Subtracted from width and depth so the plates don't jam. "
                                               "1 mm is a good value."), w.entry(frm, vars_["tol"]))
    row(5, "minp", T("Min. partial cell (mm)"), T("Narrower remainders become a filler strip or stay empty instead "
                                                   "of a shortened cell. At least 8 mm."), w.entry(frm, vars_["minp"]))
    row(6, "style", T("Baseplate style"), T("Shape of the plates (from gridfinity-rebuilt). 'thin' needs the least "
                                            "material; the thick styles hold magnets."),
        ttk.Combobox(frm, textvariable=style, state="readonly", values=list(style_names)))

    w.heading(frm, T("Printer")).grid(row=7, column=0, columnspan=2, sticky="w", pady=(14, 6))
    pbox = ttk.Combobox(frm, textvariable=printer, state="readonly",
                        values=[n for n, _, _ in printers.PRINTERS] + [custom_txt])
    row(8, "printer", T("Printer"), T("Your printer determines the maximum size of a plate."), pbox)
    cust_entry = row(9, "custom", T("Custom plate size (mm)"),
                     T("Longest edge of a plate in mm. Only active when 'Custom' is selected as printer."),
                     w.entry(frm, custom))
    plate_info = ttk.Label(frm, text="", style="Muted.TLabel")
    plate_info.grid(row=10, column=0, columnspan=2, sticky="w")

    w.heading(frm, T("Partial cells")).grid(row=11, column=0, columnspan=2, sticky="w", pady=(14, 6))
    chk = w.tip(ttk.Checkbutton(frm, text=T("Remainder from 3 mm as filler strip"), variable=filler),
                T("Remainders between 3 mm and the minimum partial cell are printed as a flat strip so the "
                  "plates don't slide."))
    chk.grid(row=12, column=0, columnspan=2, sticky="w")
    sides = ttk.Frame(frm)
    sides.grid(row=13, column=0, columnspan=2, sticky="w", pady=(6, 0))
    side_tip = T("Which side the shortened cells (and filler strips) are on.")
    w.tip(ttk.Label(sides, text=T("Partial cells in X:")), side_tip).grid(row=0, column=0, sticky="w", padx=(0, 8))
    w.tip(ttk.Label(sides, text=T("Partial cells in Y:")), side_tip).grid(row=1, column=0, sticky="w", padx=(0, 8))
    for col, (val, txt) in enumerate((("start", T("left")), ("end", T("right"))), 1):
        ttk.Radiobutton(sides, text=txt, value=val, variable=side_x).grid(row=0, column=col, sticky="w", padx=4)
    for col, (val, txt) in enumerate((("start", T("bottom")), ("end", T("top"))), 1):
        ttk.Radiobutton(sides, text=txt, value=val, variable=side_y).grid(row=1, column=col, sticky="w", padx=4)

    def pick_out():
        d = filedialog.askdirectory()
        if d:
            vars_["out"].set(os.path.normpath(d))

    out_tip = T("The plate files are written here.")
    w.heading(frm, T("Output folder"), out_tip).grid(row=15, column=0, columnspan=2, sticky="w", pady=(14, 6))
    orow = ttk.Frame(frm)
    orow.grid(row=16, column=0, columnspan=2, sticky="we")
    w.tip(w.entry(orow, vars_["out"], 30), out_tip).pack(side="left", fill="x", expand=True)
    ttk.Button(orow, text="…", width=3, style="Small.TButton", command=pick_out).pack(side="left", padx=(4, 0))

    info = w.info_text(frm, 12)
    info.grid(row=17, column=0, columnspan=2, sticky="we", pady=(14, 0))

    canvas = theme.canvas(right)
    canvas.pack(fill="both", expand=True)

    st = {"plan": None, "hits": []}

    def printer_name():
        return printers.CUSTOM if printer.get() == custom_txt else printer.get()

    def get_plan():
        """Validate the inputs and mark errors red. Returns (plan or None, messages)."""
        errs, vals = {}, {}
        for k in ("width", "depth", "tol", "minp"):
            try:
                vals[k] = w.number(vars_[k])
            except ValueError as e:
                errs[k] = str(e)
        for k in ("width", "depth"):
            if k in vals and vals[k] <= 0:
                errs[k] = T("Must be greater than 0.")
        if "tol" in vals and not 0 <= vals["tol"] < 20:
            errs["tol"] = T("Please between 0 and 20 mm.")
        if "minp" in vals and not MIN_PARTIAL_LIMIT <= vals["minp"] < PITCH:
            errs["minp"] = T("Please between {a} and {b} mm.", a=fmt(MIN_PARTIAL_LIMIT), b=fmt(PITCH - 1))
        pn = printer_name()
        cust_entry.configure(state="normal" if pn == printers.CUSTOM else "disabled")
        try:
            cval = w.number(custom)
            if pn == printers.CUSTOM and cval < PITCH:
                errs["custom"] = T("At least {m} mm (one cell).", m=fmt(PITCH))
        except ValueError as e:
            cval = 250.0
            if pn == printers.CUSTOM:
                errs["custom"] = str(e)
        max_len = printers.max_plate(pn, cval)
        bx, by = printers.bed_size_of(pn, cval)
        plate_info.configure(text=T("Largest plate: {m} mm (print bed {x} x {y} mm)", m=fmt(max_len),
                                    x=fmt(bx), y=fmt(by)))
        p = None
        if not errs:
            try:
                p = plan(vals["width"], vals["depth"], tol=vals["tol"], max_len=max_len, min_partial=vals["minp"],
                         filler_min=3.0 if filler.get() else 1e9,
                         x_start=side_x.get() == "start", y_start=side_y.get() == "start",
                         style=style_names.get(style.get(), "thin"))
            except ValueError as e:
                errs["width"] = errs["depth"] = str(e)
        for k, wid in fields.items():
            w.mark(wid, k in errs)
        msgs = []
        for k, m in errs.items():
            line = f"{labels[k].strip()}: {m}"
            if line not in msgs:
                msgs.append(line)
        return p, msgs

    def draw(*_):
        canvas.delete("all")
        p, msgs = get_plan()
        st["plan"] = p
        if p is None:
            w.set_info(info, errors=msgs)
            return
        # keep the default name in sync until the user changes it
        dn = default_name(p)
        if not name.get().strip() or name.get() == auto["name"]:
            name.set(dn)
        auto["name"] = dn
        w.set_info(info, summary(p))
        cw, ch = canvas.winfo_width(), canvas.winfo_height()
        if cw < 50:
            return
        s = min((cw - 40) / p["width"], (ch - 60) / p["depth"])
        X = lambda x: 20 + x * s
        Y = lambda y: ch - 24 - y * s   # Y upwards
        canvas.create_rectangle(X(0), Y(0), X(p["width"]), Y(p["depth"]), outline="#b8bfca", dash=(4, 3))
        canvas.create_text(X(p["width"] / 2), Y(p["depth"]) - 11, text=T("top"), fill=theme.MUTED)
        canvas.create_text(X(p["width"] / 2), Y(0) + 12, text=T("bottom"), fill=theme.MUTED)
        labels_ = {t["key"]: t["label"] for t in p["types"].values()}
        order = sorted(labels_.values())
        st["hits"] = []
        for tile in p["tiles"]:
            (x, y), (sx, sy) = tile["pos"], tile["size"]
            lab = labels_[tile["key"]]
            col = TILE_COLORS[order.index(lab) % len(TILE_COLORS)]
            cx = x
            for wx in tile["cells"][0]:   # every cell on its own, partial cells lighter
                cy = y
                for wy in tile["cells"][1]:
                    px, py = is_partial(wx), is_partial(wy)
                    canvas.create_rectangle(X(cx), Y(cy), X(cx + wx), Y(cy + wy),
                                            fill=tint(col) if (px or py) else col, outline="white")
                    if px or py:
                        st["hits"].append(((X(cx), Y(cy + wy), X(cx + wx), Y(cy)), px, py))
                    cy += wy
                cx += wx
            canvas.create_rectangle(X(x), Y(y), X(x + sx), Y(y + sy), outline="white", width=3)
            canvas.create_text(X(x + sx / 2), Y(y + sy / 2), text=lab, fill="white",
                               font=(theme.FONT, max(9, int(min(sx, sy) * s / 5)), "bold"))
        for f in p["fillers"]:
            (x, y), (sx, sy) = f["pos"], f["size"]
            canvas.create_rectangle(X(x), Y(y), X(x + sx), Y(y + sy), fill="#c3c9d2", outline="white")

    def on_printer(*_):
        pn = printer_name()
        try:
            cval = w.number(custom)
        except ValueError:
            cval = None
        i18n.save_settings(printer=pn, **({"plate_custom": cval} if cval else {}))
        log.info("Printer: %s", pn)
        draw()
        if app:
            app.printer_changed()

    def project_name():
        return safe_folder_name(name.get()) or default_name(st["plan"])

    def do_generate():
        draw()
        p = st["plan"]
        if not p:
            messagebox.showwarning(T("Note"), T("Please fix the fields marked in red first."))
            return
        try:
            root.configure(cursor="watch")
            root.update()
            folder, files = generate(p, vars_["out"].get(), project_name(), singles=singles.get())
        except Exception as e:  # noqa: BLE001
            log.exception("Generating the plates failed")
            messagebox.showerror(T("Error"), T("Generating failed: {e}\n\nDetails in the log:\n{l}",
                                               e=e, l=logging_setup.LOG_FILE))
            return
        finally:
            root.configure(cursor="")
        if app:
            app.projects_changed()
        if messagebox.askyesno(T("Done"), T("{n} files created in:\n{f}\n\nOpen folder?", n=len(files), f=folder)):
            os.startfile(folder)

    def do_send():
        """Save the project (without generating plates) and offer it to the Bin and Planner tabs."""
        draw()
        p = st["plan"]
        if not p:
            messagebox.showwarning(T("Note"), T("Please fix the fields marked in red first."))
            return
        try:
            projects.save_project(p, paths.PROJECTS, project_name())
        except OSError as e:
            log.exception("Saving the project failed")
            messagebox.showerror(T("Error"), T("Project could not be saved: {e}", e=e))
            return
        log.info("Project %s sent to Bin and Combined Grid", project_name())
        if app:
            app.projects_changed()
            app.open_project(project_name())

    w.tip(ttk.Button(bottom, text=T("Send to Bin & Combined Grid"), command=do_send),
          T("Saves the grid as a project (without generating plates). It is then available in the Bin tab for "
            "partial cells and in the Combined Grid for planning.")).pack(fill="x")
    w.tip(ttk.Checkbutton(bottom, text=T("Single files"), variable=singles),
          T("Also writes every plate as STL and a 3MF with the drawer layout into the folder 'Single files'. "
            "Off: only the file with all print plates.")).pack(anchor="w", pady=(6, 0))
    w.tip(ttk.Button(bottom, text=T("Generate files"), style="Accent.TButton", command=do_generate),
          T("Saves the project and generates ready-made print plates for your printer.")).pack(fill="x", pady=(6, 0))

    def on_click(e):
        """A click on a shortened cell moves the partial cells of that axis to the other side."""
        for (x0, y0, x1, y1), px, py in st["hits"]:
            if x0 <= e.x <= x1 and y0 <= e.y <= y1:
                if px:
                    side_x.set("end" if side_x.get() == "start" else "start")
                if py:
                    side_y.set("end" if side_y.get() == "start" else "start")
                return

    def on_motion(e):
        over = any(x0 <= e.x <= x1 and y0 <= e.y <= y1 for (x0, y0, x1, y1), _, _ in st["hits"])
        canvas.configure(cursor="hand2" if over else "")

    def get_state():
        d = {k: v.get() for k, v in vars_.items()}
        d.update(name=name.get(), auto_name=auto["name"], filler=filler.get(), custom=custom.get(),
                 side_x=side_x.get(), side_y=side_y.get(), style=style_names.get(style.get(), "thin"),
                 singles=singles.get())
        return d

    for v in list(vars_.values()) + [filler, side_x, side_y, style]:
        v.trace_add("write", draw)
    printer.trace_add("write", on_printer)
    custom.trace_add("write", on_printer)
    canvas.bind("<Configure>", draw)
    canvas.bind("<Button-1>", on_click)
    canvas.bind("<Motion>", on_motion)
    return SimpleNamespace(get_state=get_state)
