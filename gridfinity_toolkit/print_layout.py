"""
Print plates: arrange parts (baseplates, filler strips, bins) on the bed of the selected
printer and write ready-to-print 3MF files.

- Everything lies flat on the bed (z = 0), nothing overlaps, minimum gap GAP.
- Keep-out zones of the printer (e.g. the purge area at the front left of X1/P1) stay free.
- Parts may be rotated by 90 degrees if that fits better.
- Output: one 3MF per print plate (correct position in any slicer) and a Bambu Studio
  project with all plates (plates side by side, as Bambu lays them out).
- Optionally every part colour becomes its own filament in the Bambu project (e.g. for the AMS).
  The printer template has one filament; for n filaments every per-filament list is repeated n
  times, as Bambu Studio itself stores multi-filament projects (checked against P1S projects
  of Bambu Studio 02.07).

Parts are arranged with the MaxRects algorithm (free rectangles, "best short side fit").
"""

import json
import os
from xml.sax.saxutils import escape

import numpy as np

from . import logging_setup, mesh_io, printers
from .grid import safe_file_name
from .i18n import T

log = logging_setup.get("print_layout")

# per-filament lists without the "filament_" prefix (all "filament_..." lists are per filament too)
FILAMENT_LISTS = {
    "activate_air_filtration", "additional_cooling_fan_speed", "additional_fan_full_speed_layer",
    "chamber_temperatures", "circle_compensation_speed", "close_additional_fan_first_x_layers",
    "close_fan_the_first_x_layers", "complete_print_exhaust_fan_speed", "cool_plate_temp",
    "cool_plate_temp_initial_layer", "cooling_perimeter_transition_distance", "cooling_slowdown_logic",
    "counter_coef_1", "counter_coef_2", "counter_coef_3", "counter_limit_max", "counter_limit_min",
    "default_filament_colour", "diameter_limit", "during_print_exhaust_fan_speed", "enable_overhang_bridge_fan",
    "enable_pressure_advance", "eng_plate_temp", "eng_plate_temp_initial_layer", "fan_cooling_layer_time",
    "fan_max_speed", "fan_min_speed", "first_x_layer_fan_speed", "first_x_layer_part_fan_speed",
    "flush_volumes_vector", "full_fan_speed_layer", "hole_coef_1", "hole_coef_2", "hole_coef_3", "hole_limit_max",
    "hole_limit_min", "hot_plate_temp", "hot_plate_temp_initial_layer", "impact_strength_z", "ironing_fan_speed",
    "long_retractions_when_ec", "no_slow_down_for_cooling_on_outwalls", "nozzle_temperature",
    "nozzle_temperature_initial_layer", "nozzle_temperature_range_high", "nozzle_temperature_range_low",
    "overhang_fan_speed", "overhang_fan_threshold", "overhang_threshold_participating_cooling",
    "override_process_overhang_speed", "pre_start_fan_time", "pressure_advance", "reduce_fan_stop_start_freq",
    "required_nozzle_HRC", "retraction_distances_when_ec", "slow_down_for_layer_cooling", "slow_down_layer_time",
    "slow_down_min_speed", "supertack_plate_temp", "supertack_plate_temp_initial_layer", "temperature_vitrification",
    "textured_plate_temp", "textured_plate_temp_initial_layer", "volumetric_speed_coefficients"}
FLUSH_VOLUME = "280"   # purge volume between two filaments until Bambu Studio recalculates it

# rough print time: seconds per mm3 volume, per mm2 surface and per mm height of a part, plus a fixed
# amount per print plate. Fitted to Bambu Studio 02.07 (P1S, 0.4 nozzle, 0.2 mm standard profile,
# PLA) on 12 bins and plates: mean deviation 14 %, small parts are overestimated.
TIME_V, TIME_S, TIME_H, TIME_PLATE = 0.0389, 0.0212, 0.88, 467.0


def estimate_seconds(v, f):
    """Rough print time of one mesh in seconds (without the fixed amount per plate)."""
    tri = v[f]
    cross = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    surface = 0.5 * np.linalg.norm(cross, axis=1).sum()
    volume = abs(np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum()) / 6
    return TIME_V * volume + TIME_S * surface + TIME_H * (v[:, 2].max() - v[:, 2].min())


def duration_text(seconds):
    m = int(round(seconds / 60))
    return f"{m // 60} h {m % 60:02d} min" if m >= 60 else f"{m} min"

GAP = 4.0           # gap between parts
MARGIN = 3.0        # gap to the bed edge
PLATE_STRIDE = 1.2  # Bambu places plate n at a distance of 1.2 x bed size
BAMBU_NS = ' xmlns:BambuStudio="http://schemas.bambulab.com/package/2021"'


class Part:
    """A part to print: mesh moved so its bottom is at z = 0. color: "#rrggbb" or None."""

    def __init__(self, name, v, f, color=None):
        v = np.asarray(v, dtype=np.float64)
        self.v = v - [0, 0, v[:, 2].min()]
        self.f = np.asarray(f, dtype=np.int64)
        self.name = name
        self.color = color
        self.seconds = estimate_seconds(self.v, self.f)
        lo, hi = self.v.min(0), self.v.max(0)
        self.lo, self.size = lo[:2], (hi - lo)[:2]


# ---------------------------------------------------------------------------
# MaxRects
# ---------------------------------------------------------------------------

def _split(free, r):
    """Shrink the free rectangles around the occupied rectangle r (MaxRects)."""
    out = []
    rx0, ry0, rx1, ry1 = r
    for fx0, fy0, fx1, fy1 in free:
        if rx0 >= fx1 or rx1 <= fx0 or ry0 >= fy1 or ry1 <= fy0:
            out.append((fx0, fy0, fx1, fy1))
            continue
        if rx0 > fx0:
            out.append((fx0, fy0, rx0, fy1))
        if rx1 < fx1:
            out.append((rx1, fy0, fx1, fy1))
        if ry0 > fy0:
            out.append((fx0, fy0, fx1, ry0))
        if ry1 < fy1:
            out.append((fx0, ry1, fx1, fy1))
    # drop rectangles contained in others
    out = [a for a in out if a[2] - a[0] > 1e-6 and a[3] - a[1] > 1e-6]
    keep = []
    for i, a in enumerate(out):
        if not any(j != i and b[0] <= a[0] and b[1] <= a[1] and b[2] >= a[2] and b[3] >= a[3]
                   and (b != a or j < i) for j, b in enumerate(out)):
            keep.append(a)
    return keep


class Bed:
    def __init__(self, bx, by, keep_out):
        # GAP is added to the right/top of every part, so the last part may reach GAP
        # beyond the usable area
        self.free = [(MARGIN, MARGIN, bx - MARGIN + GAP, by - MARGIN + GAP)]
        for ex in keep_out:
            self.free = _split(self.free, (ex[0] - GAP, ex[1] - GAP, ex[2] + MARGIN, ex[3] + MARGIN))
        self.items = []

    def best(self, w, h):
        best = None
        for fx0, fy0, fx1, fy1 in self.free:
            for rot, (iw, ih) in ((False, (w, h)), (True, (h, w))):
                iw, ih = iw + GAP, ih + GAP
                fw, fh = fx1 - fx0, fy1 - fy0
                if iw <= fw + 1e-6 and ih <= fh + 1e-6:
                    score = (min(fw - iw, fh - ih), max(fw - iw, fh - ih), fy0, fx0)
                    if best is None or score < best[0]:
                        best = (score, fx0, fy0, rot, iw, ih)
        return best

    def place(self, idx, b):
        _, x, y, rot, iw, ih = b
        self.items.append((idx, x, y, rot))
        self.free = _split(self.free, (x, y, x + iw, y + ih))


def pack(parts, bed=None, keep_out=None):
    """Distribute parts over print plates. Returns plates, each a list of (part, x, y, rotated)."""
    bx, by = bed or printers.bed_size()
    if keep_out is None:
        keep_out = printers.keep_out()
    order = sorted(range(len(parts)), key=lambda i: -parts[i].size[0] * parts[i].size[1])
    beds = []
    for i in order:
        w, h = parts[i].size
        if not ((w <= bx - 2 * MARGIN and h <= by - 2 * MARGIN) or (h <= bx - 2 * MARGIN and w <= by - 2 * MARGIN)):
            raise ValueError(T("{n} ({w} x {d} mm) does not fit the print bed ({x} x {y} mm).",
                               n=parts[i].name, w=f"{w:.1f}", d=f"{h:.1f}", x=f"{bx:g}", y=f"{by:g}"))
        cand = [(b.best(w, h), b) for b in beds]
        cand = [(c, b) for c, b in cand if c is not None]
        if cand:
            c, b = min(cand, key=lambda cb: cb[0][0])
        else:
            b = Bed(bx, by, keep_out)
            beds.append(b)
            c = b.best(w, h)
            if c is None:   # only the keep-out zone is in the way
                b = Bed(bx, by, [])
                beds[-1] = b
                c = b.best(w, h)
        b.place(i, c)
    plates = [[(parts[i], x, y, rot) for i, x, y, rot in b.items] for b in beds]
    log.info("%d parts on %d print plate(s) (bed %g x %g)", len(parts), len(plates), bx, by)
    return plates


def transform(part, x, y, rot, dx=0.0, dy=0.0):
    """3MF transform (12 values): optionally rotate, move the lower left corner to (x, y)."""
    lx, ly = part.lo
    w, h = part.size
    if not rot:
        return [1, 0, 0, 0, 1, 0, 0, 0, 1, x - lx + dx, y - ly + dy, 0]
    # 90 degrees: (u, v) -> (-v, u); the corner then lies at (-(ly + h), lx)
    return [0, 1, 0, -1, 0, 0, 0, 0, 1, x + ly + h + dx, y - lx + dy, 0]


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_plate(path, placed):
    """One print plate as 3MF; positions in bed coordinates."""
    objects, items = [], []
    for n, (part, x, y, rot) in enumerate(placed, 1):
        objects.append(mesh_io.mesh_xml(n, part.name, part.v, part.f))
        items.append((n, transform(part, x, y, rot)))
    mesh_io.write_3mf(path, mesh_io.model_xml(objects, items, {"Application": "Gridfinity-Toolkit"}))


def filament_settings(settings, colors):
    """Printer settings (JSON bytes with one filament) extended to one filament per colour."""
    d = json.loads(settings)
    if len(colors) < 2 or len(d.get("filament_colour", [])) != 1:
        return settings
    n = len(colors)
    block = len(d.get("filament_self_index", ["1"]))
    for k, v in d.items():
        if isinstance(v, list) and (k.startswith("filament_") or k in FILAMENT_LISTS):
            d[k] = v * n
    d["filament_colour"] = d["filament_multi_colour"] = [c.upper() for c in colors]
    d["filament_self_index"] = [str(i + 1) for i in range(n) for _ in range(block)]
    d["flush_volumes_matrix"] = ["0" if r == c else FLUSH_VOLUME for r in range(n) for c in range(n)]
    dst = d.get("different_settings_to_system")
    if isinstance(dst, list) and len(dst) == 3:   # [process, filament, printer]
        d["different_settings_to_system"] = dst[:1] + dst[1:2] * n + dst[2:]
    return json.dumps(d, indent=4).encode("utf-8")


def part_colors(plates):
    """Distinct part colours in order of appearance (parts without colour use filament 1)."""
    out = []
    for placed in plates:
        for part, *_ in placed:
            if part.color and part.color.upper() not in out:
                out.append(part.color.upper())
    return out


def write_bambu_project(path, plates, template, bed=None, plate_names=None, colors=False):
    """All print plates in one Bambu Studio project (plates side by side).
    template: complete project_settings.config of the printer.
    colors: every part colour becomes its own filament."""
    with open(template, "rb") as fh:
        settings = fh.read()
    version = json.loads(settings).get("version", "02.07.00.55")
    palette = part_colors(plates) if colors else []
    if len(palette) > 1:
        settings = filament_settings(settings, palette)
        log.info("Bambu project with %d filaments: %s", len(palette), ", ".join(palette))
    bx, by = bed or printers.bed_size()
    cols = max(1, int(np.ceil(np.sqrt(len(plates)))))
    objects, items, cfg_obj, cfg_plates = [], [], [], []
    oid = 0

    def filament(part):
        c = (part.color or "").upper()
        return palette.index(c) + 1 if len(palette) > 1 and c in palette else 1

    for pi, placed in enumerate(plates):
        dx = (pi % cols) * bx * PLATE_STRIDE
        dy = -(pi // cols) * by * PLATE_STRIDE
        inst = []
        for part, x, y, rot in placed:
            oid += 1
            objects.append(mesh_io.mesh_xml(oid, part.name, part.v, part.f))
            items.append((oid, transform(part, x, y, rot, dx, dy)))
            cfg_obj.append(f'  <object id="{oid}">\n    <metadata key="name" value="{escape(part.name)}"/>\n'
                           f'    <metadata key="extruder" value="{filament(part)}"/>\n  </object>')
            inst.append(f'    <model_instance>\n      <metadata key="object_id" value="{oid}"/>\n'
                        f'      <metadata key="instance_id" value="0"/>\n'
                        f'      <metadata key="identify_id" value="{1000 + oid}"/>\n    </model_instance>')
        pname = plate_names[pi] if plate_names else f"{pi + 1}"
        cfg_plates.append(f'  <plate>\n    <metadata key="plater_id" value="{pi + 1}"/>\n'
                          f'    <metadata key="plater_name" value="{escape(pname)}"/>\n'
                          f'    <metadata key="locked" value="false"/>\n' + "\n".join(inst) + '\n  </plate>')
    cfg = '<?xml version="1.0" encoding="UTF-8"?>\n<config>\n' + "\n".join(cfg_obj + cfg_plates) + '\n</config>\n'
    # Bambu Studio only reads the plate layout and printer settings from files marked as its
    # own project format
    meta = {"BambuStudio:3mfVersion": "1", "Application": f"BambuStudio-{version}"}
    mesh_io.write_3mf(path, mesh_io.model_xml(objects, items, meta, BAMBU_NS),
                      {"Metadata/model_settings.config": cfg, "Metadata/project_settings.config": settings})


def detail_dirs(out_dir, sub=None):
    """(folder for single files, its STL sub folder). The export folder itself only keeps the
    file with all print plates and the assembly sheet; single files are optional.
    sub: own sub folder (the Baseplate tab uses one, so it does not touch the planner's files)."""
    detail = os.path.join(out_dir, T("Single_files"))
    if sub:
        detail = os.path.join(detail, sub)
    return detail, os.path.join(detail, "STL")


def clean_export(out_dir, prefixes, sub=None, extensions=(".stl", ".3mf", ".txt", ".pdf", ".png")):
    """Remove generated files of a previous export: files in out_dir starting with one of
    'prefixes' and everything in the single-files folder (detail_dirs(out_dir, sub)).
    Empty folders are removed. Files that cannot be removed (e.g. a PDF open in a viewer) stay;
    returns their paths."""
    detail, stl = detail_dirs(out_dir, sub)
    locked = []

    def rm(path):
        try:
            os.remove(path)
        except OSError as e:
            log.warning("Could not remove old export file %s: %s", path, e)
            locked.append(path)

    if os.path.isdir(out_dir):
        for fn in os.listdir(out_dir):
            if fn.lower().endswith(extensions) and fn.startswith(tuple(prefixes)):
                rm(os.path.join(out_dir, fn))
    for d in (stl, detail):
        if os.path.isdir(d):
            for fn in os.listdir(d):
                if fn.lower().endswith(extensions):
                    rm(os.path.join(d, fn))
    for d in (stl, detail, os.path.dirname(detail) if sub else None):
        if d and os.path.isdir(d) and not os.listdir(d):
            os.rmdir(d)
    return locked


def free_path(path):
    """path itself if no file is there, otherwise the first free 'name_2.ext', 'name_3.ext', ...
    (used when an old file is still open in another program)."""
    stem, ext = os.path.splitext(path)
    n = 2
    while os.path.exists(path):
        path = f"{stem}_{n}{ext}"
        n += 1
    return path


def export_plates(groups, out_dir, prefix, colors=False, times=None, singles=False, sub=None):
    """groups: {group name: [Part, ...]} -> separate print plates per group.
    With a Bambu template the file with all plates (<prefix>_Bambu_all_plates.3mf) goes into
    out_dir and, if 'singles', the single plates (<prefix>_<group>_Plate_<n>.3mf) into the
    single-files folder; without a template the single plates are the result and stay in out_dir.
    times: list that gets (plate name, estimated seconds) per print plate.
    Returns the written file names relative to out_dir."""
    template = printers.bambu_template()
    single_dir = detail_dirs(out_dir, sub)[0] if template else out_dir
    write_singles = singles or not template
    files, all_plates, names = [], [], []
    for gname, parts in groups.items():
        if not parts:
            continue
        for n, placed in enumerate(pack(parts), 1):
            if write_singles:
                path = os.path.join(single_dir, f"{prefix}_{safe_file_name(gname)}_{T('Plate')}_{n}.3mf")
                os.makedirs(single_dir, exist_ok=True)
                write_plate(path, placed)
                files.append(os.path.relpath(path, out_dir))
            all_plates.append(placed)
            names.append(f"{gname} {n}")
            if times is not None:
                times.append((f"{gname} {n}", TIME_PLATE + sum(part.seconds for part, *_ in placed)))
    if all_plates and template:
        fn = f"{prefix}_Bambu_{T('all_plates')}.3mf"
        os.makedirs(out_dir, exist_ok=True)
        write_bambu_project(os.path.join(out_dir, fn), all_plates, template, plate_names=names, colors=colors)
        files.append(fn)
    elif all_plates:
        log.info("No Bambu template for %s, writing single plate files only", printers.printer_label())
    return files
