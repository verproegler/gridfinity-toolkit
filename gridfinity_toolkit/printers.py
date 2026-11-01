"""Printer presets: bed size, largest baseplate, keep-out zones and Bambu project templates."""

import os
import re

from . import paths
from .i18n import T, load_settings

# Bed width x depth in mm. The largest plate is the shorter side minus a margin.
PRINTERS = [
    ("Bambu Lab A1 mini", 180, 180),
    ("Bambu Lab A1", 256, 256),
    ("Bambu Lab P1P / P1S", 256, 256),
    ("Bambu Lab X1C / X1E", 256, 256),
    ("Bambu Lab H2D", 325, 320),
    ("Prusa MINI+", 180, 180),
    ("Prusa MK4 / MK4S", 250, 210),
    ("Prusa CORE One", 250, 220),
    ("Creality Ender-3 V3", 220, 220),
    ("Creality K1 / K1C", 220, 220),
    ("Creality K1 Max", 300, 300),
    ("Elegoo Neptune 4 Pro", 225, 225),
    ("Voron 2.4 (350)", 350, 350),
]
DEFAULT_PRINTER = "Bambu Lab P1P / P1S"
CUSTOM = "custom"
BED_MARGIN = 6.0   # room for skirt/brim, subtracted from the largest plate

# Keep-out zones on the bed (x0, y0, x1, y1), e.g. the purge/cutter area of X1/P1
KEEP_OUT = {
    "Bambu Lab P1P / P1S": [(0, 0, 18, 28)],
    "Bambu Lab X1C / X1E": [(0, 0, 18, 28)],
}


def printer_choice():
    """(printer name or CUSTOM, custom plate size) from the settings."""
    s = load_settings()
    return s.get("printer", DEFAULT_PRINTER), float(s.get("plate_custom", 250.0))


def bed_size_of(name, custom=250.0):
    for n, x, y in PRINTERS:
        if n == name:
            return float(x), float(y)
    return custom + BED_MARGIN, custom + BED_MARGIN


def bed_size():
    """Bed (x, y) in mm for the selected printer."""
    return bed_size_of(*printer_choice())


def max_plate(name, custom):
    for n, x, y in PRINTERS:
        if n == name:
            return min(x, y) - BED_MARGIN
    return custom


def printer_label():
    name, custom = printer_choice()
    return name if name != CUSTOM else T("Custom ({w} mm)", w=f"{custom:g}")


def fits_bed(w, d):
    bx, by = bed_size()
    return (w <= bx and d <= by) or (w <= by and d <= bx)


def keep_out():
    return KEEP_OUT.get(printer_choice()[0], [])


def bambu_template(printer=None):
    """Path of the Bambu project template (a complete project_settings.config) for the printer.

    Without a complete template Bambu Studio ignores the plate layout or crashes, so the
    multi-plate project file is only written when a template exists. To add a printer: save
    a project in Bambu Studio and copy its Metadata/project_settings.config to
    assets/bambu_template_<printer name>.config."""
    name = printer or printer_choice()[0]
    path = os.path.join(paths.ASSETS, "bambu_template_" + re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_") + ".config")
    return path if os.path.isfile(path) else None
