"""
Stackable Gridfinity bins in any grid size and height.

The geometry follows gridfinity-rebuilt-openscad by kennetek (MIT license, see
THIRD_PARTY_LICENSES.md), which implements the Gridfinity specification by Zack Freedman:
    grid 42 mm, base top 41.5 mm with corner radius 3.75 (src/core/standard.scad)
    base profile 0.8 / 1.8 / 2.15 mm, base height 7 mm
    height h * 7 mm, stacking lip 0.7 / 1.8 / 1.9 mm (4.4 mm nominal) with a 0.6 mm fillet on top
    and a 1.2 mm support below it (src/core/wall.scad)

Base styles:
    lite      -> hollow feet like gridfinity-rebuilt-lite (thin shell, open from the inside)
    standard  -> solid feet and a solid bridge up to 7 mm like gridfinity-rebuilt-bins

Infill:
    solid  -> closed walls
    hex    -> walls with hexagon cut-outs (optionally the floor too, lite base only)

Options (own design, no copied geometry):
    dividers  -> div_x / div_y compartments, 1.2 mm walls up to 0.5 mm below the stacking zone
    label     -> 12 mm shelf at the back wall with a 45 degree underside (prints without support)
    scoop     -> quarter-round ramp at the front of every compartment row
    'front' turns label and scoop by quarter turns (0 = -Y, 1 = +X, 2 = +Y, 3 = -X) so the planner
    can keep them at the drawer front when a part is placed rotated.

Plates (kind "plate"): the normal feet with a flat 2 mm top. In the baseplate they close cells; on a
bin with stacking lip they are a lid. 'lip' makes them stackable (1 unit, stacking lip on top),
'grip' adds a finger hole or a slot.

Magnet holes (optional): 6.5 x 2.4 mm, four per cell, 8 mm from the cell edge
(MAGNET_HOLE_RADIUS, MAGNET_HOLE_DEPTH, d_hole_from_side in src/core/standard.scad). In lite bins
each hole gets a solid ring of wall thickness around it, like gridfinity_base_lite.

Partial cells: shortened baseplate cells keep the normal profile at their edges, so a foot of
(partial width - 0.5 mm) fits exactly.
"""

import math
import os
import re

import numpy as np

from . import logging_setup, mesh_io, paths, printers
from .grid import PITCH, fmt, safe_file_name, widths_text
from .i18n import T

log = logging_setup.get("bins")

try:
    import manifold3d as m3
except ImportError as e:  # pragma: no cover - hint for the user
    raise ImportError("Missing package: run 'pip install -r requirements.txt'.") from e

CLEAR = 0.5      # a bin is 0.5 mm smaller than the grid per axis (BASE_GAP_MM)
RADIUS = 3.75    # outer corner radius (BASE_TOP_RADIUS)
UNIT_H = 7.0     # one height unit
FLOOR = 0.8      # floor thickness inside a hollow foot (bottom_layer of the lite bins)
BASE_H = 7.0     # base incl. bridge (BASE_HEIGHT); the inside starts here for standard bases
LIP_SUPPORT = 1.2                                    # STACKING_LIP_SUPPORT_HEIGHT
LIP_FILLET = 0.6                                     # STACKING_LIP_FILLET_RADIUS
LIP_NOMINAL = 4.4                                    # STACKING_LIP_HEIGHT without fillet
_LIP_C = LIP_NOMINAL - LIP_FILLET - LIP_FILLET * math.sqrt(2)   # fillet centre above h * 7 mm
LIP_TOP = _LIP_C + LIP_FILLET                        # real lip height above h * 7 mm (~3.55)
SEG = 8          # segments per quarter circle
DENSITY = 1.24   # PLA in g/cm^3 (weight estimate only)
MIN_PARTIAL = 12.0
BASES = ("lite", "standard")
STYLE_KEYS = ("h", "fill", "lip", "wall", "hex_size", "hex_web", "hex_floor", "base", "magnets", "kind", "grip",
              "div_x", "div_y", "label", "scoop", "flat")
STYLE_DEFAULTS = {"kind": "bin", "grip": "none", "div_x": 1, "div_y": 1, "label": False, "scoop": False,
                  "flat": True}
KINDS = ("bin", "plate")
GRIPS = ("none", "hole", "slot")
PLATE_T = 2.0      # top of a flat plate above the feet
PLATE_H = 1.0      # a plate takes one height unit in the planner
DIV_T = 1.2        # divider thickness
LABEL_D = 12.0     # depth of the label shelf
SCOOP_R = 15.0     # largest scoop radius
MAGNET_R, MAGNET_DEPTH = 6.5 / 2, 2.0 + 2 * 0.2   # MAGNET_HOLE_RADIUS, MAGNET_HOLE_DEPTH
HOLE_FROM_SIDE = 8.0                              # d_hole_from_side

# outer profile of a foot: (z, inset from the foot edge) = BASE_PROFILE
FOOT_OUT = [(0.0, 2.95), (0.8, 2.15), (2.6, 2.15), (4.75, 0.0)]
FOOT_TOP = 4.75


# ---------------------------------------------------------------------------
# Geometry primitives
# ---------------------------------------------------------------------------

def rrect(w, d, off, z=None, radius=RADIUS):
    """Rounded rectangle w x d with corner radius 'radius', inset by 'off' (negative = enlarged)."""
    r = max(radius - off, 0.2)
    hx, hy = w / 2 - off - r, d / 2 - off - r
    pts = []
    for cx, cy, a0 in ((hx, hy, 0), (-hx, hy, 90), (-hx, -hy, 180), (hx, -hy, 270)):
        for i in range(SEG + 1):
            a = math.radians(a0 + 90 * i / SEG)
            p = (cx + r * math.cos(a), cy + r * math.sin(a))
            pts.append(p if z is None else (*p, z))
    return pts


def union(parts):
    parts = [p for p in parts if not p.is_empty()]
    if not parts:
        return m3.Manifold()
    return parts[0] if len(parts) == 1 else m3.Manifold.batch_boolean(parts, m3.OpType.Add)


def loft(w, d, levels, cx=0.0, cy=0.0, radius=RADIUS):
    """Solid of stacked rounded rectangles [(z, inset), ...]. Each section is convex and
    built as its own hull."""
    parts = []
    for (z0, o0), (z1, o1) in zip(levels, levels[1:]):
        pts = np.array(rrect(w, d, o0, z0, radius) + rrect(w, d, o1, z1, radius))
        parts.append(m3.Manifold.hull_points(pts))
    return union(parts).translate((cx, cy, 0.0))


def axis_cells(n, extra=0.0):
    """Cell widths of one axis: whole cells of 42 mm, a remaining 0.5 -> one half cell of
    21 mm, plus an optional partial cell of 'extra' mm."""
    full = int(math.floor(n + 1e-9))
    half = (n - full) > 0.25
    return [PITCH] * full + ([PITCH / 2] if half else []) + ([extra] if extra > 0 else [])


def hex_poly(cu, cv, s):
    """Hexagon with width across flats s, points left/right, flat sides top/bottom."""
    r = s / math.sqrt(3)
    return [(cu + r * math.cos(math.radians(60 * k)), cv + r * math.sin(math.radians(60 * k))) for k in range(6)]


def hex_centers(half_u, v_lo, v_hi, s, web):
    """Centres of whole hexagons within |u| <= half_u, v_lo..v_hi.
    Tries four offsets of the pattern and keeps the one with the most holes."""
    if s <= 0 or v_hi - v_lo < s or half_u * 2 < 2 * s / math.sqrt(3):
        return []
    p = s + web
    dx = math.sqrt(3) / 2 * p
    r = s / math.sqrt(3)
    vc = (v_lo + v_hi) / 2
    ncol = int(half_u / dx) + 2
    nrow = int((v_hi - v_lo) / p) + 2
    best = []
    for u0 in (0.0, dx / 2):
        for v0 in (0.0, p / 2):
            pts = []
            for c in range(-ncol, ncol + 1):
                u = u0 + c * dx
                if abs(u) + r > half_u + 1e-6:
                    continue
                for k in range(-nrow, nrow + 1):
                    v = vc + v0 + (k + 0.5 * (c % 2)) * p
                    if v - s / 2 >= v_lo - 1e-6 and v + s / 2 <= v_hi + 1e-6:
                        pts.append((u, v))
            if len(pts) > len(best):
                best = pts
    return best


# ---------------------------------------------------------------------------
# Bins
# ---------------------------------------------------------------------------

def min_height(lip=True, wall=0.8):
    """Smallest height in units (half steps): base plus 1 mm inside and, if any, the lip support."""
    need = BASE_H + 1.0 + (LIP_SUPPORT + 2.6 - wall if lip else 0.0)
    return math.ceil(need / UNIT_H * 2 - 1e-9) / 2


def build_bin(nx, ny, h, fill="solid", lip=True, wall=0.8, hex_size=7.0, hex_web=3.0, hex_floor=False,
              px=0.0, py=0.0, base="lite", magnets=False, **options):
    """Build a bin. nx, ny in cells (half steps), h in height units,
    px, py: additional partial cell per axis in mm (grid size, 0 = none),
    options: kind, grip, div_x, div_y, label, scoop, flat, front (see build_bin_cells).
    Returns (Manifold, info dict)."""
    for n, p, ax in ((nx, px, T("Width")), (ny, py, T("Depth"))):
        if p < 0 or n < 0:
            raise ValueError(T("Negative values are not allowed."))
        if 0 < p < MIN_PARTIAL:
            raise ValueError(T("{ax}: partial cell must be at least {m} mm.", ax=ax, m=fmt(MIN_PARTIAL)))
        if p >= PITCH:
            raise ValueError(T("{ax}: partial cell must be smaller than {m} mm (use whole cells otherwise).",
                               ax=ax, m=fmt(PITCH)))
        if n < 0.5 and p == 0:
            raise ValueError(T("{ax}: enter at least 0.5 cells or a partial cell.", ax=ax))
    return build_bin_cells(axis_cells(nx, px), axis_cells(ny, py), h, fill, lip, wall, hex_size, hex_web, hex_floor,
                           base, magnets, **options)


def feet_of(cx, cy):
    """Centre and size of every foot for the cell widths per axis."""
    gx, gy = sum(cx), sum(cy)
    feet = []
    x0 = -gx / 2
    for sx in cx:
        y0 = -gy / 2
        for sy in cy:
            feet.append((x0 + sx / 2, y0 + sy / 2, sx - CLEAR, sy - CLEAR))
            y0 += sy
        x0 += sx
    return feet


def check_cells(cx, cy, wall, base):
    if not 0.4 <= wall <= 1.8:
        raise ValueError(T("Wall thickness must be between 0.4 and 1.8 mm."))
    for c in (cx, cy):
        if not c or min(c) < MIN_PARTIAL - 1e-6 or max(c) > PITCH + 1e-6:
            raise ValueError(T("Invalid cell widths {c} (allowed {a} to {b} mm).", c=c, a=fmt(MIN_PARTIAL),
                               b=fmt(PITCH)))
    if base not in BASES:
        raise ValueError(T("Unknown base style: {b}", b=base))


def lip_arc(H, angles):
    """Points (z, inset) of the 0.6 mm fillet on top of the stacking lip."""
    return [(H + _LIP_C + LIP_FILLET * math.sin(math.radians(a)), LIP_FILLET * (1 - math.cos(math.radians(a))))
            for a in angles]


def lip_inside(H, z_from, inset_from):
    """Inner profile from (z_from, inset_from) through lip support, lip and fillet (STACKING_LIP)."""
    k = LIP_FILLET / math.sqrt(2)
    start = [(z_from, inset_from)] if z_from < H - LIP_SUPPORT - 1e-6 else []
    return (start + [(H - LIP_SUPPORT, 2.6), (H, 2.6), (H + 0.7, 1.9), (H + 2.5, 1.9),
             (H + _LIP_C + k, LIP_FILLET + k)] + lip_arc(H, range(135, 89, -15))[1:] + [(H + LIP_TOP + 0.5, LIP_FILLET)])


def hollow_feet(feet, wall):
    """Cavities of the lite feet: the base profile moved inwards by 'wall' (base_outer_shell)."""
    foot_in = [(FLOOR, 2.15 + wall), (2.6, 2.15 + wall), (FOOT_TOP, wall), (FOOT_TOP + 0.01, wall)]
    return [loft(fw, fd, foot_in, fx, fy) for fx, fy, fw, fd in feet]


def prism(poly, length):
    """2D polygon in (y, z) extruded along X over 'length', centred."""
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))
    cs = m3.CrossSection([poly if area > 0 else poly[::-1]])
    return cs.extrude(length).transform(np.array([[0, 0, 1, -length / 2], [1, 0, 0, 0], [0, 1, 0, 0]], dtype=float))


def compartment_fronts(D, wall, n):
    """Front y of every compartment row (front = -Y) for n rows, and the row depth."""
    inner = D - 2 * wall
    step = inner / n
    return [-D / 2 + wall + k * step + (DIV_T / 2 if k else 0.0) for k in range(n)], step - (DIV_T if n > 1 else 0)


def build_bin_cells(cx, cy, h, fill="solid", lip=True, wall=0.8, hex_size=7.0, hex_web=3.0, hex_floor=False,
                    base="lite", magnets=False, kind="bin", grip="none", div_x=1, div_y=1, label=False, scoop=False,
                    flat=True, front=0):
    """Build a bin (or with kind="plate" a plate) from the cell widths per axis (grid size in mm,
    e.g. (42, 42, 27)). The order decides where the feet sit. flat: with the lite base the hollow feet
    are closed at the top, so the inside floor is smooth instead of showing the grid.
    Returns (Manifold, info dict)."""
    if kind == "plate":
        return build_plate_cells(cx, cy, lip, wall, base, grip, front)
    if not 0.4 <= wall <= 1.8:
        raise ValueError(T("Wall thickness must be between 0.4 and 1.8 mm."))
    for c in (cx, cy):
        if not c or min(c) < MIN_PARTIAL - 1e-6 or max(c) > PITCH + 1e-6:
            raise ValueError(T("Invalid cell widths {c} (allowed {a} to {b} mm).", c=c, a=fmt(MIN_PARTIAL),
                               b=fmt(PITCH)))
    if h < min_height(lip, wall) - 1e-9:
        raise ValueError(T("Height too small: at least {h} units.", h=fmt(min_height(lip, wall))))
    if base not in BASES:
        raise ValueError(T("Unknown base style: {b}", b=base))
    div_x, div_y = max(1, int(div_x)), max(1, int(div_y))
    gx, gy = sum(cx), sum(cy)
    W, D = gx - CLEAR, gy - CLEAR
    H = h * UNIT_H
    top = H + (LIP_TOP if lip else 0.0)
    lip_start = H - LIP_SUPPORT - (2.6 - wall)   # from here the lip support thickens inwards
    feet = feet_of(cx, cy)

    # outer body: feet + tub up to the top; with lip the top edge gets the 0.6 mm fillet
    if lip:
        arc = [(H + _LIP_C + LIP_FILLET * math.sin(math.radians(a)), LIP_FILLET * (1 - math.cos(math.radians(a))))
               for a in range(15, 91, 15)]
        shell = [(FOOT_TOP, 0.0), (H + _LIP_C, 0.0)] + arc
    else:
        shell = [(FOOT_TOP, 0.0), (top, 0.0)]
    outer = union([loft(fw, fd, FOOT_OUT, fx, fy) for fx, fy, fw, fd in feet] + [loft(W, D, shell)])

    cavities = []
    open_floor = base == "lite" and not flat
    z_in = BASE_H - (0.01 if open_floor else 0.0)   # bottom of the tub (overlaps the lite bridge)
    if base == "lite":
        cavities += hollow_feet(feet, wall)   # flat: closed on top by the solid bridge layer
    if open_floor:
        # bridge: one opening per cell, chamfered from 'wall' to 0 (_lite_bridge_chamfer)
        bridge = union([loft(fw, fd, [(FOOT_TOP, wall), (BASE_H, 0.0)], fx, fy) for fx, fy, fw, fd in feet])
        cavities.append(bridge ^ loft(W, D, [(FOOT_TOP, wall), (BASE_H + 0.01, wall)]))
    # inside of the tub; with lip: support, lip profile and the fillet (STACKING_LIP)
    if lip:
        k = LIP_FILLET / math.sqrt(2)
        arc = [(H + _LIP_C + LIP_FILLET * math.sin(math.radians(a)), LIP_FILLET * (1 - math.cos(math.radians(a))))
               for a in range(135, 89, -15)]
        levels = [(z_in, wall), (lip_start, wall), (H - LIP_SUPPORT, 2.6), (H, 2.6), (H + 0.7, 1.9),
                  (H + 2.5, 1.9), (H + _LIP_C + k, LIP_FILLET + k)] + arc[1:] + [(top + 0.5, LIP_FILLET)]
    else:
        levels = [(z_in, wall), (top + 0.5, wall)]
    cavities.append(loft(W, D, levels))
    body = outer - union(cavities)

    holes = 0
    if fill == "hex":
        cutters = []
        v_lo, v_hi = BASE_H + 1.0, (lip_start if lip else H) - 1.0
        for length, dist, rot in ((D, W / 2, 0), (W, D / 2, 90), (D, W / 2, 180), (W, D / 2, 270)):
            pts = hex_centers(length / 2 - RADIUS - 1.0, v_lo, v_hi, hex_size, hex_web)
            if not pts:
                continue
            holes += len(pts)
            cs = m3.CrossSection([hex_poly(u, v, hex_size) for u, v in pts])
            # 2D (u, v) lies in XY and is extruded along Z -> turn it onto the wall at +X
            c = cs.extrude(wall + 0.6).transform(np.array(
                [[0, 0, 1, dist - wall - 0.3], [1, 0, 0, 0], [0, 1, 0, 0]], dtype=float))
            cutters.append(c.rotate((0, 0, rot)))
        if hex_floor and open_floor:
            polys = []
            for fx, fy, fw, fd in feet:
                margin = 2.15 + wall + 0.3 + 1.0
                pts = hex_centers(fw / 2 - margin, -(fd / 2 - margin), fd / 2 - margin, hex_size, hex_web)
                polys += [hex_poly(fx + u, fy + v, hex_size) for u, v in pts]
                holes += len(pts)
            if polys:
                cutters.append(m3.CrossSection(polys).extrude(FLOOR + 0.4).translate((0, 0, -0.2)))
        if cutters:
            body = body - union(cutters)

    mags = 0
    if magnets:
        spots = [(fx + x, fy + y) for fx, fy, fw, fd in feet for x, y in magnet_spots(fw + CLEAR, fd + CLEAR)]
        mags = len(spots)
        if spots:
            seg = 48
            if base == "lite":   # solid ring around every hole, closed by a floor-thick cap
                ring = MAGNET_R + wall
                body = body + (union([m3.Manifold.cylinder(MAGNET_DEPTH + FLOOR, ring, ring, seg).translate((x, y, 0.0))
                                      for x, y in spots]) ^ outer)
            body = body - union([m3.Manifold.cylinder(MAGNET_DEPTH + 0.01, MAGNET_R, MAGNET_R, seg)
                                 .translate((x, y, -0.01)) for x, y in spots])

    body = body + inner_parts(outer, W, D, H, lip, lip_start, wall, div_x, div_y, label, scoop, front)
    info = {"cells": (widths_text(cx), widths_text(cy)), "widths": (tuple(cx), tuple(cy)), "h": h,
            "size": (W, D, top), "holes": holes, "volume": body.volume(),
            "weight": body.volume() / 1000 * DENSITY, "tris": body.num_tri(), "fill": fill, "lip": lip,
            "wall": wall, "base": base, "magnets": mags, "kind": "bin", "div": (div_x, div_y), "label": label,
            "scoop": scoop, "flat": not open_floor}
    return body, info


def inner_parts(outer, W, D, H, lip, lip_start, wall, div_x, div_y, label, scoop, front):
    """Dividers, label shelf and scoops, clipped to the bin's outer shape."""
    parts = []
    z_top = H - 0.5 if lip else H   # stacked feet start at H
    span_x, span_y = W - 2 * wall + 0.2, D - 2 * wall + 0.2
    for n, along_x in ((div_x, True), (div_y, False)):
        length = W if along_x else D
        for k in range(1, n):
            pos = -length / 2 + wall + k * (length - 2 * wall) / n
            if along_x:   # divider wall across Y at x = pos
                parts.append(m3.Manifold.cube((DIV_T, span_y, z_top), True).translate((pos, 0, z_top / 2)))
            else:
                parts.append(m3.Manifold.cube((span_x, DIV_T, z_top), True).translate((0, pos, z_top / 2)))
    turned = []   # built with the front at -Y, then turned to 'front'
    Wf, Df = (W, D) if front % 2 == 0 else (D, W)
    rows = div_y if front % 2 == 0 else div_x
    inner_w = Wf - 2 * wall + 0.2
    if label:
        zt = (lip_start if lip else H) - 0.3
        yb = Df / 2 - wall + 0.1
        turned.append(prism([(yb, zt), (yb - LABEL_D, zt), (yb - LABEL_D, zt - 1.2), (yb, zt - 1.2 - LABEL_D)],
                            inner_w))
    if scoop:
        fronts, depth = compartment_fronts(Df, wall, rows)
        r = max(0.0, min(SCOOP_R, depth / 2, z_top - BASE_H - 2.0))
        if r >= 3.0:
            for y0 in fronts:
                arc = [(y0 + r - r * math.sin(math.radians(a)), BASE_H + r - r * math.cos(math.radians(a)))
                       for a in range(0, 91, 10)]
                turned.append(prism([(y0 - 0.1, 0.0), (y0 + r, 0.0)] + arc + [(y0 - 0.1, BASE_H + r)], inner_w))
    if turned:
        parts.append(union(turned).rotate((0, 0, 90 * (front % 4))))
    if not parts:
        return m3.Manifold()
    return union(parts) ^ outer


def build_plate_cells(cx, cy, lip=False, wall=0.8, base="lite", grip="none", front=0):
    """Flat plate on the normal feet: closes cells in the baseplate or is a lid on a bin. lip=True
    makes it one unit high with a stacking lip on top. grip: "none", "hole" or "slot"."""
    check_cells(cx, cy, wall, base)
    gx, gy = sum(cx), sum(cy)
    W, D = gx - CLEAR, gy - CLEAR
    feet = feet_of(cx, cy)
    H = PLATE_H * UNIT_H
    if lip:
        top = H + LIP_TOP
        shell = [(FOOT_TOP, 0.0), (H + _LIP_C, 0.0)] + lip_arc(H, range(15, 91, 15))
    else:
        top = FOOT_TOP + PLATE_T
        shell = [(FOOT_TOP, 0.0), (top, 0.0)]
    body = union([loft(fw, fd, FOOT_OUT, fx, fy) for fx, fy, fw, fd in feet] + [loft(W, D, shell)])
    cavities = hollow_feet(feet, wall) if base == "lite" else []
    if lip:
        cavities.append(loft(W, D, lip_inside(H, FOOT_TOP + 1.05, 2.6)))
    if cavities:
        body = body - union(cavities)
    if grip == "hole" and min(W, D) >= 30:
        body = body - m3.Manifold.cylinder(top + 2, 10.0, 10.0, 48).translate((0, 0, -1))
    elif grip == "slot":
        Wf, Df = (W, D) if front % 2 == 0 else (D, W)
        if Wf >= 36 and Df >= 26:
            y = -Df / 2 + 11.0
            slot = (m3.Manifold.cylinder(top + 2, 7.0, 7.0, 32).translate((-7, y, -1)) +
                    m3.Manifold.cylinder(top + 2, 7.0, 7.0, 32).translate((7, y, -1))).hull()
            body = body - slot.rotate((0, 0, 90 * (front % 4)))
    info = {"cells": (widths_text(cx), widths_text(cy)), "widths": (tuple(cx), tuple(cy)), "h": PLATE_H,
            "size": (W, D, top), "holes": 0, "volume": body.volume(), "weight": body.volume() / 1000 * DENSITY,
            "tris": body.num_tri(), "fill": "solid", "lip": lip, "wall": wall, "base": base, "magnets": 0,
            "kind": "plate", "grip": grip, "div": (1, 1), "label": False, "scoop": False}
    return body, info


def part_top(style):
    """Height of a part above its own bottom in mm (lip included)."""
    if style.get("kind") == "plate" and not style["lip"]:
        return FOOT_TOP + PLATE_T
    return style["h"] * UNIT_H + (LIP_TOP if style["lip"] else 0.0)


def mesh_arrays(body):
    mesh = body.to_mesh()
    return (np.asarray(mesh.vert_properties, dtype=np.float64)[:, :3],
            np.asarray(mesh.tri_verts, dtype=np.int64))


def nozzle_hint(wall):
    """Which nozzle prints the wall in whole lines."""
    out = []
    for d in (0.4, 0.6, 0.8):
        k = wall / d
        if abs(k - round(k)) > 0.15 or round(k) < 1:
            out.append(T("{d} no", d=fmt(d)))
        elif round(k) == 1:
            out.append(T("{d} 1 line", d=fmt(d)))
        else:
            out.append(T("{d} {n} lines", d=fmt(d), n=round(k)))
    return " | ".join(out)


def magnet_spots(w, d):
    """Magnet hole centres of a cell (grid size w x d) relative to its centre; none if they don't fit."""
    hx, hy = w / 2 - HOLE_FROM_SIDE, d / 2 - HOLE_FROM_SIDE
    if min(hx, hy) < MAGNET_R + 3.0:
        return []
    return [(sx * hx, sy * hy) for sx in (-1, 1) for sy in (-1, 1)]


def base_label(base):
    return {"lite": T("lite (hollow, lightest)"), "standard": T("standard (solid)")}.get(base, base)


def grip_label(grip):
    return {"none": T("no grip"), "hole": T("finger hole"), "slot": T("grip slot")}.get(grip, grip)


def summary(info):
    W, D, H = info["size"]
    tx, ty = info["cells"]
    if info.get("kind") == "plate":
        return "\n".join([T("Plate:       {x} x {y} cells", x=tx, y=ty),
                          T("Outer size:  {w} x {d} mm, height {t} mm", w=fmt(W), d=fmt(D), t=fmt(H)),
                          T("Stackable:   {v}", v=T("yes") if info["lip"] else T("no")),
                          T("Grip:        {v}", v=grip_label(info.get("grip", "none"))),
                          T("Material:    approx. {g} g PLA ({c} cm3)", g=f"{info['weight']:.0f}",
                            c=f"{info['volume'] / 1000:.1f}")])
    hexa = info["fill"] == "hex"
    lines = [T("Grid:        {x} x {y} cells, {h} units", x=tx, y=ty, h=fmt(info["h"])),
             T("Outer size:  {w} x {d} mm, height {t} mm", w=fmt(W), d=fmt(D), t=fmt(H)),
             T("Stack lip:   {v}", v=T("yes") if info["lip"] else T("no")),
             T("Base:        {v}", v=base_label(info.get("base", "lite"))),
             T("Floor:       {v}", v=T("smooth") if info.get("flat", True) else T("open grid")),
             T("Magnets:     {v}", v=T("{n} holes for 6 x 2 mm", n=info["magnets"]) if info.get("magnets")
               else T("no")),
             T("Infill:      {v}", v=T("Hexagon cut-outs") if hexa else T("solid"))
             + (T(" ({n} holes)", n=info["holes"]) if hexa else ""),
             T("Wall:        {w} mm", w=fmt(info["wall"])),
             T("Compartments: {x} x {y}", x=info.get("div", (1, 1))[0], y=info.get("div", (1, 1))[1]),
             T("Label shelf: {v}", v=T("yes") if info.get("label") else T("no")),
             T("Scoop:       {v}", v=T("yes") if info.get("scoop") else T("no")),
             T("Material:    approx. {g} g PLA ({c} cm3)", g=f"{info['weight']:.0f}", c=f"{info['volume'] / 1000:.1f}"),
             T("Triangles:   {n}", n=info["tris"]),
             "",
             T("Printing:    height units do not depend on nozzle/layer"),
             T("Nozzle:      {v}", v=nozzle_hint(info["wall"]))]
    if not printers.fits_bed(W, D):
        bx, by = printers.bed_size()
        lines.append(T("WARNING: does not fit the print bed ({p}, {x} x {y} mm)!", p=printers.printer_label(),
                       x=fmt(bx), y=fmt(by)))
    return "\n".join(lines)


def file_stem(info):
    tx, ty = info["cells"]
    if info.get("kind") == "plate":
        name = f"Plate_{tx}x{ty}" + ("_stack" if info["lip"] else "")
        name += "" if info.get("grip", "none") == "none" else "_" + info["grip"]
        return name + ("" if info.get("base", "lite") == "lite" else "_" + info["base"])
    name = f"Bin_{tx}x{ty}x{fmt(info['h'])}"
    if info.get("base", "lite") != "lite":
        name += "_" + info["base"]
    if not info.get("flat", True):
        name += "_open"
    if info["fill"] == "hex":
        name += T("_hex")
    if not info["lip"]:
        name += T("_nolip")
    if info.get("magnets"):
        name += "_mag"
    if info.get("div", (1, 1)) != (1, 1):
        name += "_div{}x{}".format(*info["div"])
    if info.get("label"):
        name += "_label"
    if info.get("scoop"):
        name += "_scoop"
    return name


def export(body, info, out_dir=paths.BIN_OUTPUT, name=None):
    """Save a single bin as STL and 3MF. Returns the file paths."""
    os.makedirs(out_dir, exist_ok=True)
    v, f = mesh_arrays(body)
    stem = file_stem(info)
    if name and safe_file_name(name):
        stem = f"{safe_file_name(name)}_{stem}"
    os.makedirs(os.path.join(out_dir, mesh_io.STL_DIR), exist_ok=True)
    files = [os.path.join(out_dir, mesh_io.STL_DIR, stem + ".stl"), os.path.join(out_dir, stem + ".3mf")]
    mesh_io.save_stl_mesh(files[0], v, f, stem)
    mesh_io.save_3mf_single(files[1], v, f, stem)
    log.info("Bin saved: %s (%d triangles)", files[1], len(f))
    return files


def grid_lines(cx, cy, ring=1):
    """Grid lines below a bin: its own cells (including partial cells) and a ring of normal
    cells around it. Returns (segments, colours)."""
    xs = -sum(cx) / 2 + np.concatenate([[0.0], np.cumsum(cx)])
    ys = -sum(cy) / 2 + np.concatenate([[0.0], np.cumsum(cy)])
    ox = np.concatenate([xs[0] - PITCH * np.arange(ring, 0, -1), xs, xs[-1] + PITCH * np.arange(1, ring + 1)])
    oy = np.concatenate([ys[0] - PITCH * np.arange(ring, 0, -1), ys, ys[-1] + PITCH * np.arange(1, ring + 1)])
    segs, cols = [], []
    z = 0.05
    for x in ox:
        segs.append([[x, oy[0], z], [x, oy[-1], z]])
        cols.append([185, 190, 198])
    for y in oy:
        segs.append([[ox[0], y, z], [ox[-1], y, z]])
        cols.append([185, 190, 198])
    for x in xs:   # the bin's own cells stand out
        segs.append([[x, ys[0], z + 0.02], [x, ys[-1], z + 0.02]])
        cols.append([46, 158, 68])
    for y in ys:
        segs.append([[xs[0], y, z + 0.02], [xs[-1], y, z + 0.02]])
        cols.append([46, 158, 68])
    return np.array(segs), np.array(cols)


# ---------------------------------------------------------------------------
# Default names
# ---------------------------------------------------------------------------

def default_bin_name(n):
    return T("Bin {n}", n=n)


def next_bin_name(taken):
    """First free default name (Bin 1, Bin 2, ...)."""
    n = 1
    while default_bin_name(n) in taken:
        n += 1
    return default_bin_name(n)


def is_default_bin_name(name):
    """Default name of a bin or a plate (Bin 3, Plate 2)."""
    for pattern in (T("Bin {n}"), T("Plate {n}")):
        pre, post = pattern.split("{n}")
        if re.fullmatch(re.escape(pre) + r"\d+" + re.escape(post), name):
            return True
    return False


def next_name(taken, kind="bin"):
    """First free default name for a bin or (kind "plate") a plate."""
    pattern = T("Plate {n}") if kind == "plate" else T("Bin {n}")
    n = 1
    while pattern.format(n=n) in taken:
        n += 1
    return pattern.format(n=n)
