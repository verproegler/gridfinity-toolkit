"""Gridfinity grid basics shared by baseplates, bins and the planner."""

import re

PITCH = 42.0   # Gridfinity grid pitch
EPS = 1e-6


def fmt(v):
    """Short number for display: 42.0 -> '42', 1.25 -> '1.25'."""
    return f"{v:.2f}".rstrip("0").rstrip(".")


def is_partial(w):
    return abs(w - PITCH) > EPS


def rotations(wx, wy):
    """All orientations of a cell layout as (k, canonical widths): the canonical layout
    rotated by k * 90 degrees counter-clockwise gives (wx, wy)."""
    return [(0, (wx, wy)),
            (1, (wy, wx[::-1])),
            (2, (wx[::-1], wy[::-1])),
            (3, (wy[::-1], wx))]


def canonical(wx, wy):
    """Recognise identical parts in different rotations. Returns (key, k)."""
    best = None
    for k, (cx, cy) in rotations(tuple(wx), tuple(wy)):
        rank = (sum(cx), cx, cy)
        if best is None or rank > best[0]:
            best = (rank, (cx, cy), k)
    return best[1], best[2]


def place_matrix(k, size, pos):
    """3MF transform: rotate a canonical part (A x B from the origin) by k * 90 degrees and
    move it to pos."""
    (a, b), (x, y) = size, pos
    return {0: [1, 0, 0, 0, 1, 0, 0, 0, 1, x, y, 0],
            1: [0, 1, 0, -1, 0, 0, 0, 0, 1, x + b, y, 0],
            2: [-1, 0, 0, 0, -1, 0, 0, 0, 1, x + a, y + b, 0],
            3: [0, -1, 0, 1, 0, 0, 0, 0, 1, x, y + a, 0]}[k]


def cells_text(widths):
    """Plate cells: (42, 42, 27) -> '2+27', (27, 42, 42) -> '27+2'."""
    n = sum(1 for w in widths if not is_partial(w))
    parts = [fmt(w) for w in widths if is_partial(w)]
    if not parts:
        return str(n)
    if not n:
        return parts[0]
    return f"{parts[0]}+{n}" if is_partial(widths[0]) else f"{n}+{parts[0]}"


def widths_text(widths):
    """Bin cells: (42, 42, 27) -> '2+27mm', (42, 21) -> '1.5', (39,) -> '39mm'."""
    n = sum(1.0 if abs(w - PITCH) < EPS else 0.5 if abs(w - PITCH / 2) < EPS else 0.0 for w in widths)
    parts = ([fmt(n)] if n else []) + [fmt(w) + "mm" for w in widths
                                        if abs(w - PITCH) >= EPS and abs(w - PITCH / 2) >= EPS]
    return "+".join(parts)


def safe_folder_name(name):
    """Make a name usable as folder name (keeps spaces and umlauts)."""
    return re.sub(r'[<>:"/\\|?*]+', "_", name).strip(" .")


def safe_file_name(name):
    """Make a name usable in file names (ASCII only, no spaces)."""
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"), ("Ä", "Ae"), ("Ö", "Oe"), ("Ü", "Ue")):
        name = name.replace(a, b)
    return re.sub(r"[^A-Za-z0-9_.+-]+", "_", name).strip("_.")


def bump_name(name, taken):
    """Next free name: 'Bin 1' -> 'Bin 2', 'Screws' -> 'Screws 2'."""
    m = re.fullmatch(r"(.*?)(\s*)(\d+)", name.strip())
    base, sep, n = (m.group(1), m.group(2) or " ", int(m.group(3))) if m else (name.strip(), " ", 1)
    n += 1
    while f"{base}{sep}{n}" in taken:
        n += 1
    return f"{base}{sep}{n}"


def hex_rgb(col, log=None):
    """'#4a90d9' or '#abc' -> [r, g, b]; anything invalid becomes grey."""
    h = str(col).lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    try:
        return [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    except ValueError:
        if log:
            log.warning("Invalid colour %r, using grey", col)
        return [128, 128, 128]


def tint(col, amount=0.55):
    """Lighten a colour towards white (e.g. for partial cells)."""
    return "#" + "".join(f"{int(c + (255 - c) * amount):02x}" for c in hex_rgb(col))
