"""
Drawer planner ("Combined Grid"): plan bins directly on the cell grid of a baseplate project.

A bin occupies whole grid cells; placed on a partial cell it automatically gets that cell's
width. Bins can be stacked: the level is the height of the bin bottom in units. On level L a
bin stands on bins below with a stacking lip whose top is exactly L; every cell of its footprint
needs such a bin under it (one bin or several, e.g. a 2x1 on two 1x1 bins), and stacking lips must
grip it on two opposite sides (so a 1x1 cannot stand on a 3x3). Bins sticking through the current level are shown in red.

Data model
    bin type: {"name", "color", "nx", "ny", <style keys>}
    placed bin: {"i", "j", "ni", "nj", "z", "name", "color", "style": {<style keys>}}
"""

import os

import numpy as np

from . import bins as binlib
from . import logging_setup, mesh_io, printers, projects
from .baseplate import plate_height, print_parts, seat_height
from .grid import EPS, PITCH, canonical, fmt, hex_rgb, place_matrix, safe_file_name, widths_text
from .i18n import T
from .print_layout import Part, clean_export, detail_dirs, duration_text, export_plates, free_path

log = logging_setup.get("planner")

STYLE_KEYS = binlib.STYLE_KEYS
TYPE_COLORS = ["#2563eb", "#f59e0b", "#16a34a", "#9333ea", "#0d9488", "#db2777", "#a16207",
               "#475569", "#65a30d", "#ea580c"]
RED = "#dc2626"
DIM_GREY = "#d9dde3"   # 3D view: bins on other levels
DIM_ALPHA = 0.2        # their opacity, so the bins below/inside stay visible
DEFAULT_STYLE = {"h": 6.0, "fill": "solid", "lip": True, "wall": 0.8, "hex_size": 7.0, "hex_web": 3.0,
                 "hex_floor": False, "base": "lite", "magnets": False, **binlib.STYLE_DEFAULTS}
PART_KEYS = STYLE_KEYS + ("front",)   # what makes two parts identical (front: see bins.build_bin_cells)


def is_plate(style):
    return style.get("kind") == "plate"


def plate_style(lip=False, grip="none", base="lite"):
    return dict(DEFAULT_STYLE, kind="plate", h=binlib.PLATE_H, lip=lip, grip=grip, base=base)


def features_text(style, sep):
    """Plate and bin options as text, joined by sep."""
    if is_plate(style):
        out = [T("plate")] + ([T("stackable")] if style["lip"] else [])
        out += [] if style.get("grip", "none") == "none" else [binlib.grip_label(style["grip"])]
        return sep.join(out + ([] if style.get("base", "lite") == "lite" else [T("standard base")]))
    out = [T("hexagon") if style["fill"] == "hex" else T("solid")]
    out += [] if style.get("base", "lite") == "lite" else [T("standard base")]
    out += [] if style.get("flat", True) or style.get("base", "lite") != "lite" else [T("open floor")]
    out += [T("magnets")] if style.get("magnets") else []
    if (style.get("div_x", 1), style.get("div_y", 1)) != (1, 1):
        out.append(T("{x}x{y} compartments", x=style["div_x"], y=style["div_y"]))
    out += [T("label shelf")] if style.get("label") else []
    out += [T("scoop")] if style.get("scoop") else []
    return sep.join(out + ([] if style["lip"] else [T("no lip")]))


def part_style(style, k):
    """Style of the canonical part for a bin turned by k quarter turns: dividers swap with an odd
    turn, label/scoop/grip slot are turned back so they stay at the drawer front (-Y)."""
    s = {key: style[key] for key in STYLE_KEYS}
    if k % 2:
        s["div_x"], s["div_y"] = s["div_y"], s["div_x"]
    sided = s.get("label") or s.get("scoop") or s.get("grip") == "slot"
    s["front"] = (-k) % 4 if sided else 0
    return s


# ---------------------------------------------------------------------------
# Bin types
# ---------------------------------------------------------------------------

def type_details(t):
    if is_plate(t):
        return f"{t['nx']}x{t['ny']}  " + features_text(t, "  ")
    return f"{t['nx']}x{t['ny']}  {fmt(t['h'])} HE  " + features_text(t, "  ")


def default_types():
    return [dict(DEFAULT_STYLE, nx=1, ny=1, color=TYPE_COLORS[0], name=binlib.default_bin_name(1)),
            dict(DEFAULT_STYLE, nx=2, ny=1, color=TYPE_COLORS[1], name=binlib.default_bin_name(2))]


def load_types():
    types = projects.load_bin_types()
    if not types:
        return default_types()
    taken = []
    for t in types:   # older types without a name
        if not t.get("name"):
            t["name"] = binlib.next_bin_name(taken + [x.get("name") for x in types])
        taken.append(t["name"])
    return types


def skipped_types(types):
    """Names of the types that are only placeholders and are not exported."""
    return {t["name"] for t in types if not t.get("export", True)}


def free_color(types):
    used = {t.get("color") for t in types}
    return next((c for c in TYPE_COLORS if c not in used), TYPE_COLORS[len(types) % len(TYPE_COLORS)])


def style_of(t):
    return {k: t[k] for k in STYLE_KEYS}


# ---------------------------------------------------------------------------
# Grid, levels, checks
# ---------------------------------------------------------------------------

def edges(p):
    """Cell borders in X and Y (mm, drawer coordinates)."""
    x0, y0 = p["origin"]
    return (x0 + np.concatenate([[0.0], np.cumsum(p["cols"])]),
            y0 + np.concatenate([[0.0], np.cumsum(p["rows"])]))


def bin_widths(p, b):
    return tuple(p["cols"][b["i"]:b["i"] + b["ni"]]), tuple(p["rows"][b["j"]:b["j"] + b["nj"]])


def top(b):
    return b["z"] + b["style"]["h"]


def overlap_xy(b, i, j, ni, nj):
    return i < b["i"] + b["ni"] and b["i"] < i + ni and j < b["j"] + b["nj"] and b["j"] < j + nj


def contains_xy(b, i, j, ni, nj):
    return b["i"] <= i and i + ni <= b["i"] + b["ni"] and b["j"] <= j and j + nj <= b["j"] + b["nj"]


def check(p, bins, i, j, ni, nj, z=0.0, h=6.0, ignore=None):
    """Error message if a bin does not fit there, otherwise None."""
    if i < 0 or j < 0 or i + ni > len(p["cols"]) or j + nj > len(p["rows"]):
        return T("extends beyond the grid")
    w = sum(p["cols"][i:i + ni]) - binlib.CLEAR
    d = sum(p["rows"][j:j + nj]) - binlib.CLEAR
    if not printers.fits_bed(w, d):
        return T("too large for the print bed ({w} x {d} mm, {p})", w=fmt(w), d=fmt(d), p=printers.printer_label())
    others = [b for b in bins if b is not ignore]
    if z > EPS and not covered(others, i, j, ni, nj, z):
        return T("no stacking surface below (needed: bins with stacking lip and top at {z} units "
                 "under every cell)", z=fmt(z))
    if z > EPS and not held(others, i, j, ni, nj, z):
        return T("not held: needs stacking lips on two opposite sides (left and right or front and back)")
    for b in others:
        if overlap_xy(b, i, j, ni, nj) and b["z"] < z + h - EPS and z < top(b) - EPS:
            return T("overlaps {n}", n=b.get("name") or T("another bin"))
    return None


def covered(supports, i, j, ni, nj, z, lip=True):
    """True if every cell of the footprint lies on a bin from 'supports' whose top is at z
    (with stacking lip unless lip=False). Several bins may share the load."""
    tops = [b for b in supports if abs(top(b) - z) < EPS and (b["style"]["lip"] or not lip)]
    return all(any(contains_xy(b, ci, cj, 1, 1) for b in tops)
               for ci in range(i, i + ni) for cj in range(j, j + nj))


def held(supports, i, j, ni, nj, z):
    """True if the footprint lies on stacking surfaces at z (every cell, see covered) and stacking
    lips grip it on two opposite sides (every row left+right, or every column front+back), so it is clamped
    between them. A 1x1 on a 3x3 bin is not: it would only touch the lip on one or two adjacent sides."""
    if not covered(supports, i, j, ni, nj, z):
        return False
    tops = [b for b in supports if abs(top(b) - z) < EPS and b["style"]["lip"]]
    # every row is gripped left and right, or every column front and back
    x_pair = all(any(b["i"] == i and b["j"] <= r < b["j"] + b["nj"] for b in tops) and
                 any(b["i"] + b["ni"] == i + ni and b["j"] <= r < b["j"] + b["nj"] for b in tops)
                 for r in range(j, j + nj))
    y_pair = all(any(b["j"] == j and b["i"] <= c < b["i"] + b["ni"] for b in tops) and
                 any(b["j"] + b["nj"] == j + nj and b["i"] <= c < b["i"] + b["ni"] for b in tops)
                 for c in range(i, i + ni))
    return x_pair or y_pair


def on_top(bins, base):
    """Bins standing directly on 'base', fully or only with some of their cells."""
    return [b for b in bins if b is not base and abs(b["z"] - top(base)) < EPS and
            overlap_xy(base, b["i"], b["j"], b["ni"], b["nj"])]


def resting_on(bins, base):
    """All bins standing (directly or indirectly) only on 'base' (a bin or a list of bins), i.e.
    bins that move with it. A bin bridging to another support does not belong to it."""
    group = list(base) if isinstance(base, (list, tuple)) else [base]
    out = []
    grew = True
    while grew:
        grew = False
        for b in bins:
            if any(b is g for g in group) or b["z"] <= EPS:
                continue
            if covered(group, b["i"], b["j"], b["ni"], b["nj"], b["z"], lip=False):
                group.append(b)
                out.append(b)
                grew = True
    return out


def supported(bins, b):
    """True if bin b stands on the baseplate or is held by stacking surfaces (see held)."""
    return b["z"] <= EPS or held([x for x in bins if x is not b], b["i"], b["j"], b["ni"], b["nj"], b["z"])


def floating(bins):
    """Bins without anything below them (e.g. after removing their support). They stay where they
    are, are shown in red and only cause a hint before the export."""
    return [b for b in bins if not supported(bins, b)]


def remove(bins, b):
    """Remove only bin b; bins stacked on it stay at their level. Returns the bins that lost
    their support because of it."""
    above = on_top(bins, b)
    bins.remove(b)
    return [x for x in above if not supported(bins, x)]


def floating_note(bins):
    """Hint before the export if bins have nothing below them, otherwise None."""
    fl = floating(bins)
    if not fl:
        return None
    return T("{n} bins have nothing below them ({names}); they would float in the drawer.", n=len(fl),
             names=", ".join(sorted({b.get("name") or "?" for b in fl})))


def resize(p, bins, b, i, j, ni, nj, apply=False):
    """Error message if bin b cannot get the new footprint (bins stacked on it must stay supported),
    otherwise None. apply=True keeps the new footprint."""
    above = resting_on(bins, b)
    above += [x for x in on_top(bins, b) if not any(x is a for a in above)]   # bridging bins too
    old = {k: b[k] for k in ("i", "j", "ni", "nj")}
    b.update(i=i, j=j, ni=ni, nj=nj)
    err = None
    for x in [b] + above:
        err = check(p, bins, x["i"], x["j"], x["ni"], x["nj"], x["z"], x["style"]["h"], ignore=x)
        if err:
            break
    if err or not apply:
        b.update(old)
    return err


def move(p, bins, movers, di, dj, apply=False):
    """Error message if the bins 'movers' (with everything stacked on them) cannot be shifted by
    di, dj cells, otherwise None. apply=True moves them."""
    group = []
    for b in list(movers) + resting_on(bins, list(movers)):
        if not any(b is g for g in group):
            group.append(b)
    rest = [b for b in bins if not any(b is g for g in group)]
    placed = []
    for b in sorted(group, key=lambda x: x["z"]):   # supports first
        moved = dict(b, i=b["i"] + di, j=b["j"] + dj)
        err = check(p, rest + placed, moved["i"], moved["j"], b["ni"], b["nj"], b["z"], b["style"]["h"])
        if err:
            return err
        placed.append(moved)
    if apply:
        for b in group:
            b["i"], b["j"] = b["i"] + di, b["j"] + dj
    return None


def level_role(b, level):
    """How a bin appears on the selected level."""
    if abs(b["z"] - level) < EPS:
        return "current"
    if b["z"] < level - EPS < top(b) - 2 * EPS:
        return "blocked"          # sticks through the level
    if abs(top(b) - level) < EPS and b["style"]["lip"]:
        return "surface"          # stacking surface for this level
    if b["z"] > level:
        return "above"
    return "below"


def stack_levels(bins):
    return sorted({round(top(b), 3) for b in bins if b["style"]["lip"]})


def change_style(p, bins, targets, style, color=None, name=None):
    """Apply a style (e.g. a new height) to the target bins. Bins stacked on a target move
    with its new top; if anything would collide or lose its support, that target stays unchanged.
    Targets at the same level and height are tried together first, so a bin bridging two of
    them moves along. Returns (changed, kept)."""
    groups = {}
    for b in targets:
        groups.setdefault((round(b["z"], 3), round(b["style"]["h"], 3)), []).append(b)
    changed = kept = 0
    for group in groups.values():
        if _change_group(p, bins, group, style, color, name):
            changed += len(group)
            continue
        for b in group if len(group) > 1 else ():
            if _change_group(p, bins, [b], style, color, name):
                changed += 1
            else:
                kept += 1
        if len(group) == 1:
            kept += 1
    return changed, kept


def _change_group(p, bins, group, style, color, name):
    """change_style for bins of equal level and height; True if applied, else everything is reverted."""
    old = [(b["style"], b["color"], b.get("name")) for b in group]
    above = resting_on(bins, group)   # determined with the old height
    bridging = [x for b in group for x in on_top(bins, b) if not any(x is a for a in above)]
    dz = style["h"] - group[0]["style"]["h"]
    for b in group:
        b["style"] = dict(style)
        if color:
            b["color"] = color
        if name:
            b["name"] = name
    for x in above:
        x["z"] += dz
    ok = (style["lip"] or not (above or bridging)) and all(
        check(p, bins, x["i"], x["j"], x["ni"], x["nj"], x["z"], x["style"]["h"], ignore=x) is None
        for x in group + above + bridging)
    if not ok:
        for b, (st, col, nm) in zip(group, old):
            b["style"], b["color"], b["name"] = st, col, nm
        for x in above:
            x["z"] -= dz
    return ok


# ---------------------------------------------------------------------------
# Parts, summary, export
# ---------------------------------------------------------------------------

def part_groups(p, bins):
    """Group identical bins (same cell widths up to rotation, same style).
    Returns a list of (key, canonical widths, style, [(bin, k), ...])."""
    groups = {}
    for b in bins:
        key_w, k = canonical(*bin_widths(p, b))
        style = part_style(b["style"], k)
        key = (key_w, tuple(style[s] for s in PART_KEYS))
        groups.setdefault(key, [key_w, style, []])[2].append((b, k))
    out = [(key, *g) for key, g in groups.items()]
    out.sort(key=lambda g: (-len(g[3]), -sum(g[1][0]) * sum(g[1][1])))
    return out


def part_text(widths, style):
    name = f"{widths_text(widths[0])} x {widths_text(widths[1])}, "
    return name + ("" if is_plate(style) else f"{fmt(style['h'])} HE, ") + features_text(style, ", ")


def summary(p, bins):
    if not bins:
        return T("No bins placed yet.")
    groups = part_groups(p, bins)
    used = sum(b["ni"] * b["nj"] for b in bins if b["z"] < EPS)
    levels = sorted({b["z"] for b in bins})
    lines = [T("{n} bins, {k} different parts", n=len(bins), k=len(groups)),
             T("Used on level 0: {u} of {t} cells", u=used, t=len(p["cols"]) * len(p["rows"])),
             T("Levels (bottom): {v} units", v=", ".join(fmt(z) for z in levels)), ""]
    for n, (_, widths, style, members) in enumerate(groups, 1):
        names = sorted({b.get("name") for b, _ in members} - {"", None})
        lines.append(f"K{n}: {len(members)}x  {', '.join(names)}".rstrip())
        lines.append(f"      {part_text(widths, style)}")
    return "\n".join(lines)


def export(p, bins, out, with_base=True, colors=False, skip=(), singles=False, title=""):
    """Print-ready output into the folder 'out' (normally output/<project>): print plates for the
    selected printer with everything lying flat (stacked bins too), optionally with the
    baseplates and filler strips, plus the assembly sheet. singles: also every part once
    (STL + 3MF with count), the single print plates and a text summary in the single-files folder.
    skip: type names that are placeholders only (they stay on the assembly sheet but get no files).
    Returns (export folder, files, estimated print seconds, notes for the user, e.g. that an open
    PDF could not be replaced)."""
    os.makedirs(out, exist_ok=True)
    locked = clean_export(out, (T("Print_plate"), T("Assembly_sheet")))   # replace the previous export
    notes = []
    detail, stl_dir = detail_dirs(out)
    if singles:
        os.makedirs(stl_dir, exist_ok=True)
    rel = lambda path: os.path.relpath(path, out)
    files, weight, bin_parts = [], 0.0, []
    all_bins, bins = bins, [b for b in bins if b.get("name") not in skip]
    groups = part_groups(p, bins)
    log.info("Planner export %s: %d bins (%d placeholders skipped), %d parts, printer %s", out, len(bins),
             len(all_bins) - len(bins), len(groups), printers.printer_label())
    for n, (_, widths, style, members) in enumerate(groups, 1):
        body, info = binlib.build_bin_cells(widths[0], widths[1], **style)
        v, f = binlib.mesh_arrays(body)
        names = sorted({safe_file_name(b.get("name") or "") for b, _ in members} - {""})
        stem = f"K{n}_{names[0] + '_' if len(names) == 1 else ''}{binlib.file_stem(info)}_{len(members)}x"
        if singles:
            mesh_io.save_stl_mesh(os.path.join(stl_dir, stem + ".stl"), v, f, stem)
            mesh_io.save_3mf_single(os.path.join(detail, stem + ".3mf"), v, f, stem)
            files += [rel(os.path.join(stl_dir, stem + ".stl")), rel(os.path.join(detail, stem + ".3mf"))]
        weight += info["weight"] * len(members)
        for b, _ in members:
            bin_parts.append(Part(f"K{n} {b.get('name') or ''} {part_text(widths, style)}".replace("  ", " "), v, f,
                                  b.get("color")))
    groups_out = {}
    if with_base:
        groups_out[T("Baseplate")] = print_parts(p)
    if colors:   # one colour per print plate, otherwise the printer changes filament on every layer
        by_color = {}
        for part in bin_parts:
            by_color.setdefault((part.color or "").upper(), []).append(part)
        for col, parts in by_color.items():
            names = sorted({b.get("name") or "?" for b in bins if (b.get("color") or "").upper() == col})
            label = ", ".join(names)
            groups_out[f"{T('Bins')} {label[:30] + ('…' if len(label) > 30 else '')}"] = parts
    else:
        groups_out[T("Bins")] = bin_parts
    times = []
    plate_files = export_plates(groups_out, out, T("Print_plate"), colors=colors, times=times, singles=singles)
    total = sum(s for _, s in times)
    files += plate_files
    summary_name = T("Bins_summary") + ".txt"
    with (open(os.path.join(detail, summary_name), "w", encoding="utf-8") if singles else
          open(os.devnull, "w", encoding="utf-8")) as fh:
        fh.write("\n".join(
            [T("Drawer {w} x {d} mm", w=fmt(p["width"]), d=fmt(p["depth"])), "", summary(p, bins), "",
             T("Material bins: approx. {g} g PLA", g=f"{weight:.0f}"),
             T("Print time: approx. {t} in total (rough estimate for the 0.2 mm standard profile, +-20 %)",
               t=duration_text(total))]
            + ([T("Not exported (placeholders): {n} bins of the types {t}", n=len(all_bins) - len(bins),
                  t=", ".join(sorted({b.get("name") for b in all_bins} & set(skip))))]
               if len(all_bins) > len(bins) else [])
            + [f"  {name}: {duration_text(s)}" for name, s in times]
            + ["",
             T("Print plates for {p}:", p=printers.printer_label())]
            + [f"  {f}" for f in plate_files]
            + ["", T("The file '..._Bambu_all_plates.3mf' contains all plates in one Bambu Studio project. "
                     "The single '..._Plate_n.3mf' files work in any slicer."), ""]))
    if singles:
        files.append(rel(os.path.join(detail, summary_name)))
    # assembly sheet: where every part goes, one page per level
    from .layout_sheet import layout_sheet
    sheet = os.path.join(out, T("Assembly_sheet") + ".pdf")
    if sheet in locked:   # still open in a PDF viewer: write a new one next to it
        sheet = free_path(sheet)
        log.warning("Old assembly sheet is locked, writing %s instead", sheet)
        notes.append(T("The old assembly sheet is still open in another program and could not be replaced. "
                       "The new one is '{f}'. Close the old PDF before the next export.",
                       f=os.path.basename(sheet)))
    try:
        files += [rel(x) for x in layout_sheet(p, all_bins, groups, sheet,
                                               title or os.path.basename(os.path.normpath(out)),
                                               png_dir=detail, png=singles)]
    except Exception as e:  # noqa: BLE001 - the printable files are already written
        log.exception("Assembly sheet failed")
        notes.append(T("The assembly sheet could not be created: {e}", e=e))
    others = [x for x in locked if not x.lower().endswith(".pdf")]
    if others:
        notes.append(T("{n} old files are open in another program and were kept: {f}", n=len(others),
                       f=", ".join(os.path.basename(x) for x in others[:5]) + (" …" if len(others) > 5 else "")))
    log.info("Export done: %d files, approx. %.0f g of bins", len(files), weight)
    return out, files, total, notes


# ---------------------------------------------------------------------------
# 3D scene
# ---------------------------------------------------------------------------

def merge(parts):
    vs, fs, cs, off = [], [], [], 0
    for v, f, c in parts:
        vs.append(v)
        fs.append(f + off)
        cs.append(c)
        off += len(v)
    return np.concatenate(vs), np.concatenate(fs), np.concatenate(cs)


class Scene:
    """Builds the 3D mesh of the whole drawer; bin meshes are cached."""

    def __init__(self):
        self.cache = {}

    def part(self, widths, style):
        key = (widths, tuple(style[s] for s in PART_KEYS))
        if key not in self.cache:
            body, _ = binlib.build_bin_cells(widths[0], widths[1], **style)
            v, f = binlib.mesh_arrays(body)
            self.cache[key] = (v + [sum(widths[0]) / 2, sum(widths[1]) / 2, 0], f)
        return self.cache[key]

    def build(self, p, bins, level, highlight=(), dim_others=False):
        """Returns (v, f, colour per triangle, line segments, line colours).
        highlight: bins drawn in a lighter colour (selection).
        dim_others: bins not starting on 'level' are greyed out and see-through (warnings stay faintly
        red); the colours then get a 4th column with the opacity 0..1."""
        parts = []

        def add(v, f, col, alpha=1.0):
            rgb = hex_rgb(col, log) + ([alpha] if dim_others else [])
            parts.append((v, f, np.tile(np.array(rgb, dtype=float), (len(f), 1))))

        xe, ye = edges(p)
        ph, seat = plate_height(p.get("style", "thin")), seat_height(p.get("style", "thin"))
        for t in p["tiles"]:
            (x, y), (sx, sy) = t["pos"], t["size"]
            add(*mesh_io.box_mesh(x + 0.3, y + 0.3, 0, sx - 0.6, sy - 0.6, ph - 0.6), "#cbd2db")
        for fl in p["fillers"]:
            (x, y), (sx, sy) = fl["pos"], fl["size"]
            add(*mesh_io.box_mesh(x, y, 0, sx, sy, ph), "#a9b2bd")
        for b in bins:
            key_w, k = canonical(*bin_widths(p, b))
            size = (sum(key_w[0]), sum(key_w[1]))
            m = np.array(place_matrix(k, size, (xe[b["i"]], ye[b["j"]])), dtype=float).reshape(4, 3)
            m[3, 2] = b["z"] * binlib.UNIT_H + seat
            col = RED if level_role(b, level) == "blocked" or not supported(bins, b) else b["color"]
            if any(b is h for h in highlight):
                col = "#facc15"
            dim = dim_others and abs(b["z"] - level) > EPS and not any(b is h for h in highlight)
            if dim:
                col = mix(col, DIM_GREY, 0.55 if col == RED else 0.8)
            v, f = self.part(key_w, part_style(b["style"], k))
            add(v @ m[:3] + m[3], f, col, DIM_ALPHA if dim else 1.0)
        # grid of the current level; above the floor at the height of the lip top
        zl = seat + level * binlib.UNIT_H + (binlib.FOOT_TOP + 0.05 if level < EPS else binlib.LIP_TOP + 0.05)
        segs = [[[x, ye[0], zl], [x, ye[-1], zl]] for x in xe] + [[[xe[0], y, zl], [xe[-1], y, zl]] for y in ye]
        v, f, c = merge(parts)
        return v, f, c, np.array(segs), np.tile([22, 163, 74], (len(segs), 1))


def mix(col, other, t):
    """Blend colour 'col' towards 'other' by t (0..1), as '#rrggbb'."""
    a, b = hex_rgb(col, log), hex_rgb(other, log)
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def top_mm(p, b):
    """Highest point of a bin above the drawer floor in mm (baseplate, stacking and lip included)."""
    return seat_height(p.get("style", "thin")) + b["z"] * binlib.UNIT_H + binlib.part_top(b["style"])


def highest(p, bins):
    """(height in mm, bin or None) of the highest part; without bins the baseplate itself."""
    if not bins:
        return plate_height(p.get("style", "thin")), None
    b = max(bins, key=lambda x: top_mm(p, x))
    return top_mm(p, b), b


def height_note(p, bins, limit):
    """Hint before the export if the highest part does not fit under the drawer height (None = no limit)."""
    mm, b = highest(p, bins)
    if not limit or mm <= limit + EPS:
        return None
    return T("The highest part ({n}) reaches {h} mm, but the drawer is only {m} mm high.",
             n=b.get("name") or "?" if b else T("Baseplate"), h=f"{mm:.1f}", m=fmt(limit))


def magnet_notes(p, bins):
    """Hints before the export: magnet holes that have nothing to hold on to."""
    names = lambda bs: ", ".join(sorted({b.get("name") or "?" for b in bs}))
    mag = [b for b in bins if b["style"].get("magnets")]
    stacked = [b for b in mag if b["z"] > EPS]
    floor = [b for b in mag if b["z"] <= EPS]
    notes = []
    if stacked:
        notes.append(T("{n} stacked bins have magnet holes ({names}). The stacking lip below has no magnets, "
                       "so they hold nothing there.", n=len(stacked), names=names(stacked)))
    if floor and p.get("style", "thin") == "thin":
        notes.append(T("{n} bins with magnet holes stand on the 'thin' baseplate ({names}). It has no magnet "
                       "holes; choose 'skeletonized' or 'weighted' in the Baseplate tab.",
                       n=len(floor), names=names(floor)))
    return notes


def partial_widths(p):
    """(partial width in X or 0, partial width in Y or 0) of a project."""
    part = lambda ws: next((w for w in ws if abs(w - PITCH) > EPS), 0.0)
    return part(p["cols"]), part(p["rows"])
