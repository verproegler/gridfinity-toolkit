"""
Command line.

    python -m gridfinity_toolkit                         -> GUI
    python -m gridfinity_toolkit baseplate 500 380       -> baseplates for a 500 x 380 mm drawer
    python -m gridfinity_toolkit baseplate 418 238 --partial-x left --plan-only
    python -m gridfinity_toolkit bin 2 1 6               -> 2 x 1 cells, 6 units, solid
    python -m gridfinity_toolkit bin 0 4 6 --partial-x 39 --hex
"""

import argparse
import sys

from . import logging_setup, paths, projects


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        from .gui.app import run
        run()
        return 0
    logging_setup.setup()
    projects.migrate()
    ap = argparse.ArgumentParser(prog="gridfinity_toolkit", description="Gridfinity baseplates and bins.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("baseplate", help="baseplates cut to a drawer")
    b.add_argument("width", type=float, help="inner drawer width in mm (X)")
    b.add_argument("depth", type=float, help="inner drawer depth in mm (Y)")
    b.add_argument("--tol", type=float, default=1.0, help="tolerance subtracted from both sizes (default 1)")
    b.add_argument("--style", choices=("thin", "skeletonized", "weighted"), default="thin",
                   help="baseplate style (default thin, the lightest)")
    b.add_argument("--max", type=float, default=250.0, help="max. plate size in mm (default 250)")
    b.add_argument("--min-partial", type=float, default=12.0, help="smallest partial cell in mm (default 12)")
    b.add_argument("--no-filler", action="store_true", help="no filler strips for remainders of 3 mm or more")
    b.add_argument("--partial-x", choices=("left", "right"), default="right", help="side of the partial cells in X")
    b.add_argument("--partial-y", choices=("bottom", "top"), default="top", help="side of the partial cells in Y")
    b.add_argument("--name", help="project name (folder)")
    b.add_argument("--out", default=paths.OUTPUT, help="output folder")
    b.add_argument("--plan-only", action="store_true", help="only print the layout")
    b.add_argument("--single-files", action="store_true", help="also write STL files and single plates")

    c = sub.add_parser("bin", help="a single stackable bin")
    c.add_argument("width", type=float, help="width in cells (X), half steps (0 = partial cell only)")
    c.add_argument("depth", type=float, help="depth in cells (Y), half steps (0 = partial cell only)")
    c.add_argument("height", type=float, help="height in units of 7 mm")
    c.add_argument("--hex", action="store_true", help="walls with hexagon cut-outs")
    c.add_argument("--hex-floor", action="store_true", help="with --hex: perforate the floor too")
    c.add_argument("--hole", type=float, default=7.0, help="hexagon width across flats in mm (default 7)")
    c.add_argument("--web", type=float, default=3.0, help="web between hexagons in mm (default 3)")
    c.add_argument("--wall", type=float, default=0.8, help="wall thickness in mm (default 0.8)")
    c.add_argument("--no-lip", action="store_true", help="without stacking lip")
    c.add_argument("--base", choices=("lite", "standard"), default="lite",
                   help="lite = hollow feet (default, lightest), standard = solid base")
    c.add_argument("--magnets", action="store_true", help="holes for 6 x 2 mm magnets in the bottom")
    c.add_argument("--partial-x", type=float, default=0.0, help="additional partial cell in X, mm")
    c.add_argument("--partial-y", type=float, default=0.0, help="additional partial cell in Y, mm")
    c.add_argument("--out", default=paths.BIN_OUTPUT, help="output folder")

    a = ap.parse_args(argv)
    if a.cmd == "baseplate":
        from .baseplate import generate, plan, summary
        p = plan(a.width, a.depth, a.tol, a.max, a.min_partial, 1e9 if a.no_filler else 3.0,
                 x_start=a.partial_x == "left", y_start=a.partial_y == "bottom", style=a.style)
        print(summary(p))
        if not a.plan_only:
            folder, files = generate(p, a.out, a.name, singles=a.single_files)
            print(f"\n{len(files)} files in {folder}")
    else:
        from .bins import build_bin, export, summary
        body, info = build_bin(a.width, a.depth, a.height, "hex" if a.hex else "solid", not a.no_lip, a.wall,
                               a.hole, a.web, a.hex_floor, a.partial_x, a.partial_y, a.base, a.magnets)
        print(summary(info))
        for fn in export(body, info, a.out):
            print("->", fn)
    return 0
