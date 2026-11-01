"""
Baseplates cut to any drawer size.

The geometry follows gridfinity-rebuilt-openscad by kennetek (MIT license, see
THIRD_PARTY_LICENSES.md), src/core/gridfinity-baseplate.scad and gridfinity-rebuilt-baseplate.scad:
every cell is a block with corner radius 4 mm minus the baseplate cutter (profile 0.7 / 1.8 /
2.15 mm plus 0.35 mm clearance, 5 mm high). A partial cell simply gets a narrower cutter, so it
keeps the full profile at its edges and a foot of (partial width - 0.5 mm) fits exactly.

Styles (style_plate in kennetek's script):
    thin          -> outline only, 5 mm high, lightest (default)
    skeletonized  -> thick bottom with magnet holes, centre cut out
    weighted      -> thick bottom with magnet holes and the cut-outs for a weight
"""

import math
import os
import time

from . import bins as binlib
from . import logging_setup, mesh_io, paths
from .grid import PITCH, canonical, cells_text, fmt, place_matrix, safe_folder_name
from .i18n import T

log = logging_setup.get("baseplate")

try:
    import manifold3d as m3
except ImportError as e:  # pragma: no cover - hint for the user
    raise ImportError("Missing package: run 'pip install -r requirements.txt'.") from e

STYLES = ("thin", "skeletonized", "weighted")
PLATE_H = 5.0          # BASEPLATE_HEIGHT
OUTER_R = 4.0          # BASEPLATE_OUTER_RADIUS
# cutter profile per cell: (z, inset from the cell edge), clearance 0.35 mm at the bottom
PROFILE = [(0.0, 2.85), (0.35, 2.85), (1.05, 2.15), (2.85, 2.15), (5.0, 0.0)]
MAGNET_R, MAGNET_DEPTH = binlib.MAGNET_R, binlib.MAGNET_DEPTH
SKEL_R, SKEL_MIN = 2.0, 1.0                        # r_skel, h_skel
D_SCREW = 3.35                                     # d_screw (part of the skeletonized height)
EXTRA_H = {"thin": 0.0, "weighted": 6.4, "skeletonized": SKEL_MIN + MAGNET_DEPTH + D_SCREW}
EPS = 1e-4
MIN_PARTIAL_LIMIT = 2 * OUTER_R   # the cutter needs at least the outer corner diameter


def plate_height(style="thin"):
    return PLATE_H + EXTRA_H.get(style, 0.0)


def seat_height(style="thin"):
    """Height of a bin's bottom above the drawer floor when it sits in the baseplate."""
    return plate_height(style) - binlib.FOOT_TOP


def style_label(style):
    return {"thin": T("thin (lightest)"),
            "skeletonized": T("skeletonized (magnets)"),
            "weighted": T("weighted (magnets, weight)")}.get(style, style)


# ---------------------------------------------------------------------------
# Plate geometry
# ---------------------------------------------------------------------------

def _rect(w, d, r):
    """2D rounded rectangle (centred)."""
    return m3.CrossSection([binlib.rrect(w, d, 0.0, radius=r)])


def _skeleton(w, d):
    """2D cut-out of a skeletonized cell (profile_skeleton): the inner area without the
    corners around the magnet holes, rounded by r_skel."""
    lx, ly = w - 2 * 2.85, d - 2 * 2.85
    if min(lx, ly) <= 2 * SKEL_R + 1.0:
        return None
    cs = m3.CrossSection.square((lx - 2 * SKEL_R, ly - 2 * SKEL_R), True)
    keep = MAGNET_R + SKEL_R + 2.0
    for x, y in binlib.magnet_spots(w, d):
        corner = m3.CrossSection.square((lx, ly)).translate((x if x > 0 else x - lx, y if y > 0 else y - ly))
        cs = cs - corner.offset(keep, m3.JoinType.Round, circular_segments=32)
    if cs.is_empty():
        return None
    return cs.offset(SKEL_R, m3.JoinType.Round, circular_segments=32)


def _weight_cutter(w, d):
    """Cut-outs for a weight from below (cutter_weight); only in whole cells."""
    if min(w, d) < PITCH - EPS:
        return None
    parts = [m3.Manifold.cube((21.4, 21.4, 4.0), True).translate((0, 0, 2.0 - 0.01))]
    slot = m3.CrossSection.square((8.5, 4.25), True) + m3.CrossSection.circle(8.5 / 2, 32).translate((0, 4.25 / 2))
    for k in range(4):
        parts.append(slot.translate((0, 10)).extrude(2.01).translate((0, 0, -0.01)).rotate((0, 0, 90 * k)))
    return binlib.union(parts)


def make_plate(wx, wy, style="thin"):
    """Baseplate with cell widths wx (X) and wy (Y); partial cells may be anywhere.
    Returns the triangles (n, 3, 3) with the lower left corner at the origin."""
    if not wx or not wy:
        raise ValueError("Plate without cells")
    if style not in STYLES:
        raise ValueError(T("Unknown baseplate style: {s}", s=style))
    extra = EXTRA_H[style]
    height = PLATE_H + extra
    gx, gy = sum(wx), sum(wy)
    plate = _rect(gx, gy, OUTER_R).extrude(height)
    # profile shifted to the top of the plate; at the top it opens a little beyond the cell
    # so neighbouring cutters meet cleanly
    levels = [(extra + z, o) for z, o in PROFILE] + [(height + 0.01, -0.01)]
    if style == "thin":   # outline only: the cutter goes all the way through
        levels[0] = (-0.01, PROFILE[0][1])
    cutters = []
    x0 = 0.0
    for w in wx:
        y0 = 0.0
        for d in wy:
            cx, cy = x0 + w / 2 - gx / 2, y0 + d / 2 - gy / 2
            cutters.append(binlib.loft(w, d, levels, cx, cy, radius=OUTER_R))
            if style != "thin":
                for hx, hy in binlib.magnet_spots(w, d):
                    cutters.append(m3.Manifold.cylinder(MAGNET_DEPTH + 0.01, MAGNET_R, MAGNET_R, 48)
                                   .translate((cx + hx, cy + hy, extra - MAGNET_DEPTH)))
            if style == "skeletonized":
                sk = _skeleton(w, d)
                if sk is not None:
                    cutters.append(sk.extrude(extra + 0.02).translate((cx, cy, -0.01)))
            elif style == "weighted":
                wc = _weight_cutter(w, d)
                if wc is not None:
                    cutters.append(wc.translate((cx, cy, 0.0)))
            y0 += d
        x0 += w
    body = plate - binlib.union(cutters)
    v, f = binlib.mesh_arrays(body.translate((gx / 2, gy / 2, 0.0)))
    return v[f]


class PlateMaker:
    """Builds baseplates of one style."""

    def __init__(self, style="thin"):
        self.style = style if style in STYLES else "thin"
        self.height = plate_height(self.style)

    def make(self, wx, wy):
        return make_plate(list(wx), list(wy), self.style)


# ---------------------------------------------------------------------------
# Splitting the drawer
# ---------------------------------------------------------------------------

def plan_axis(length, max_len, min_partial):
    """Split one axis into plates.

    Returns ([(whole cells, partial cell mm)], remainder mm for a filler strip).
    The partial cell always sits in the last plate at the end of the axis."""
    if max_len < PITCH:
        raise ValueError(T("Max. plate size must be at least {m} mm.", m=fmt(PITCH)))
    full = int(math.floor((length + 1e-6) / PITCH))
    r = length - full * PITCH
    partial = r if r >= min_partial - 1e-6 else 0.0
    rest = r - partial
    if full == 0 and partial == 0:
        return [], rest
    n = 1
    while True:
        base, extra = divmod(full, n)
        counts = [base + 1] * extra + [base] * (n - extra)
        lens = [c * PITCH for c in counts]
        lens[-1] += partial
        valid = all(c > 0 for c in counts[:-1]) and (counts[-1] > 0 or partial > 0)
        if valid and max(lens) <= max_len + 1e-6:
            return [(c, 0.0) for c in counts[:-1]] + [(counts[-1], partial)], rest
        n += 1
        if n > full + 2:
            raise ValueError(T("No valid split found."))


def axis_tiles(tiles, at_start):
    """(whole cells, partial) per plate -> cell widths per plate along the axis.
    at_start: put the partial cell at the start of the axis (left/bottom) instead of the end."""
    out = [tuple([PITCH] * n + ([round(p, 2)] if p > 0 else [])) for n, p in tiles]
    if at_start:
        out = [w[::-1] for w in out[::-1]]
    return out


def plan(width, depth, tol=1.0, max_len=250.0, min_partial=12.0, filler_min=3.0,
         x_start=False, y_start=False, style="thin"):
    """Compute the plate layout. Returns a dict with plates, part types and filler strips.
    x_start / y_start: partial cells and filler strips left/bottom instead of right/top.
    style: baseplate style (see STYLES)."""
    if style not in STYLES:
        style = "thin"
    wx, wy = width - tol, depth - tol
    tx, rx = plan_axis(wx, max_len, min_partial)
    ty, ry = plan_axis(wy, max_len, min_partial)
    if not tx or not ty:
        raise ValueError(T("Drawer is too small for a plate."))
    cols, rows = axis_tiles(tx, x_start), axis_tiles(ty, y_start)
    grid_x = sum(sum(w) for w in cols)
    grid_y = sum(sum(w) for w in rows)
    use_rx, use_ry = rx >= filler_min, ry >= filler_min
    # with the filler strip on the left/bottom the grid starts behind it
    x0 = rx if (x_start and use_rx) else 0.0
    y0 = ry if (y_start and use_ry) else 0.0

    types = {}   # canonical key -> type info
    tiles = []   # individual plates in the drawer
    oy = y0
    for cy in rows:
        ox = x0
        for cx in cols:
            key, k = canonical(cx, cy)
            if key not in types:
                types[key] = {"key": key, "count": 0, "size": (sum(key[0]), sum(key[1]))}
            types[key]["count"] += 1
            tiles.append({"key": key, "pos": (ox, oy), "size": (sum(cx), sum(cy)), "rot": k, "cells": (cx, cy)})
            ox += sum(cx)
        oy += sum(cy)
    # label the types by size
    for i, t in enumerate(sorted(types.values(), key=lambda t: -t["size"][0] * t["size"][1])):
        t["label"] = chr(ord("A") + i) if i < 26 else f"T{i}"

    fillers = []   # strips split into equal pieces <= max_len

    def strip(total, along_x, fixed, width, start):
        n = max(1, math.ceil(total / max_len - 1e-9))
        ln = total / n
        for i in range(n):
            if along_x:
                fillers.append({"pos": (start + i * ln, fixed), "size": (ln, width)})
            else:
                fillers.append({"pos": (fixed, start + i * ln), "size": (width, ln)})

    if use_rx:   # strip right/left (runs along Y)
        strip(grid_y, False, 0.0 if x_start else grid_x, rx, y0)
    if use_ry:   # strip top/bottom (runs along X), including the corner
        strip(grid_x + (rx if use_rx else 0.0), True, 0.0 if y_start else grid_y, ry, 0.0)
    return {"width": width, "depth": depth, "tol": tol, "usable": (wx, wy),
            "grid": (grid_x, grid_y), "rest": (rx, ry), "start": (x_start, y_start),
            "params": {"width": width, "depth": depth, "tol": tol, "max_len": max_len,
                       "min_partial": min_partial, "filler_min": filler_min,
                       "x_start": x_start, "y_start": y_start, "style": style},
            "style": style,
            # cell grid of the whole drawer (used by the planner)
            "cols": [w for c in cols for w in c], "rows": [w for r in rows for w in r],
            "origin": (x0, y0),
            "types": types, "tiles": tiles, "fillers": fillers}


def filler_groups(p):
    """Filler strips grouped by size: [((length, width), [strip, ...]), ...]."""
    groups = {}
    for f in p["fillers"]:
        sx, sy = f["size"]
        key = (round(max(sx, sy), 2), round(min(sx, sy), 2))
        groups.setdefault(key, []).append(f)
    return sorted(groups.items(), reverse=True)


def side_note(p):
    xs, ys = p["start"]
    x = T("left (-X)") if xs else T("right (+X)")
    y = T("bottom (-Y)") if ys else T("top (+Y)")
    return T("Partial cells and filler strips are at the {x} and {y}.", x=x, y=y)


def summary(p):
    lines = [T("Drawer:    {w} x {d} mm (usable after {t} mm tolerance: {uw} x {ud} mm)",
               w=fmt(p["width"]), d=fmt(p["depth"]), t=fmt(p["tol"]),
               uw=fmt(p["usable"][0]), ud=fmt(p["usable"][1])),
             T("Grid:      {x} x {y} mm", x=fmt(p["grid"][0]), y=fmt(p["grid"][1])),
             T("Style:     {s}, {h} mm high", s=style_label(p.get("style", "thin")),
               h=fmt(plate_height(p.get("style", "thin"))))]
    rx, ry = p["rest"]
    if rx > 0.05 or ry > 0.05:
        lines.append(T("Remainder: {x} mm (X) / {y} mm (Y)", x=fmt(rx), y=fmt(ry))
                     + (T("  -> filler strips") if p["fillers"] else T("  -> left empty")))
    lines.append("")
    lines.append(T("To print ({n} plate(s)):", n=len(p["tiles"])))
    for t in sorted(p["types"].values(), key=lambda t: t["label"]):
        cells = f"{cells_text(t['key'][0])} x {cells_text(t['key'][1])}"
        lines.append(T("  {l}: {n}x  {sx} x {sy} mm  (cells {c})", l=t["label"], n=t["count"],
                       sx=fmt(t["size"][0]), sy=fmt(t["size"][1]), c=cells))
    for (sx, sy), group in filler_groups(p):
        lines.append(T("  Filler strip: {n}x  {a} x {b} mm", n=len(group), a=fmt(sx), b=fmt(sy)))
    return "\n".join(lines)


def default_name(p):
    return T("Drawer_{w}x{d}", w=fmt(p["width"]), d=fmt(p["depth"]))


def print_parts(p, src=None):
    """All plates and filler strips of the plan as printable parts (for the print plates)."""
    from .print_layout import Part
    src = src or PlateMaker(p.get("style", "thin"))
    parts = []
    for t in sorted(p["types"].values(), key=lambda t: t["label"]):
        v, f = mesh_io.weld(src.make(*t["key"]))
        for _ in range(t["count"]):
            parts.append(Part(f"{T('Baseplate')} {t['label']} {fmt(t['size'][0])}x{fmt(t['size'][1])}", v, f))
    for (ln, wd), group in filler_groups(p):
        v, f = mesh_io.weld(mesh_io.box(ln, wd, src.height))
        for _ in group:
            parts.append(Part(f"{T('Filler')} {fmt(ln)}x{fmt(wd)}", v, f))
    return parts


def generate(p, out_dir, name=None, singles=False):
    """Save the project (projects/<name>) and write ready-to-print baseplate plates for the selected
    printer into out_dir/<name>. singles: also one STL per plate type, the filler strips and a 3MF
    with the drawer layout (own single-files sub folder). Returns (folder, file names)."""
    from . import print_layout, projects
    t0 = time.time()
    src = PlateMaker(p.get("style", "thin"))
    name = safe_folder_name(name or "") or default_name(p)
    log.info("Generating project %s (%s x %s mm, %d plates, style %s)", name, fmt(p["width"]), fmt(p["depth"]),
             len(p["tiles"]), src.style)
    folder = os.path.join(out_dir, name)
    os.makedirs(folder, exist_ok=True)
    objects, items, files, meshes = {}, [], [], {}
    # the output folder keeps only the file with all print plates; everything else is optional
    # and goes into its own single-files sub folder (the planner export lives next to it)
    prefix = sub = T("Baseplates")
    print_layout.clean_export(folder, (prefix,), sub, (".stl", ".3mf"))
    detail, stl_dir = print_layout.detail_dirs(folder, sub)
    if singles:
        os.makedirs(stl_dir, exist_ok=True)
    rel = lambda path: os.path.relpath(path, folder)
    oid = 1
    for t in sorted(p["types"].values(), key=lambda t: t["label"]):
        tris = src.make(*t["key"])
        bad = mesh_io.open_edges(tris)
        if bad:
            log.warning("Plate %s has %d open edges", t["label"], bad)
        fn = f"{t['label']}_{fmt(t['size'][0])}x{fmt(t['size'][1])}mm_{t['count']}x.stl"
        if singles:
            mesh_io.save_stl(os.path.join(stl_dir, fn), tris, fn)
            files.append(rel(os.path.join(stl_dir, fn)))
        objects[oid] = (f"{t['label']} {fmt(t['size'][0])}x{fmt(t['size'][1])}", tris)
        meshes[t["key"]] = (oid, t["size"])
        oid += 1
    for tile in p["tiles"]:
        mid, size = meshes[tile["key"]]
        items.append((mid, place_matrix(tile["rot"], size, tile["pos"])))
    for (ln, wd), group in filler_groups(p):
        tris = mesh_io.box(ln, wd, src.height)
        fn = f"{T('Filler')}_{fmt(ln)}x{fmt(wd)}mm_{len(group)}x.stl"
        if singles:
            mesh_io.save_stl(os.path.join(stl_dir, fn), tris, fn)
            files.append(rel(os.path.join(stl_dir, fn)))
        objects[oid] = (f"{T('Filler')} {fmt(ln)}x{fmt(wd)}", tris)
        for f in group:
            x, y = f["pos"]
            if f["size"][0] < f["size"][1]:   # strip runs along Y -> rotate
                items.append((oid, [0, 1, 0, -1, 0, 0, 0, 0, 1, x + wd, y, 0]))
            else:
                items.append((oid, [1, 0, 0, 0, 1, 0, 0, 0, 1, x, y, 0]))
        oid += 1
    if singles:
        fn3 = f"{name}_{T('all_parts')}.3mf"
        mesh_io.save_3mf_objects(os.path.join(detail, fn3), objects, items)
        files.append(rel(os.path.join(detail, fn3)))
    files += print_layout.export_plates({T("Baseplate"): print_parts(p, src)}, folder, prefix,
                                        singles=singles, sub=sub)
    projects.save_project(p, paths.PROJECTS, name)
    log.info("Project %s done: %d files in %.1f s", name, len(files), time.time() - t0)
    return folder, files
