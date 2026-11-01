"""
Assembly sheet (PDF): how the printed parts go into the drawer.

Page 1: 3D overview and the position of the baseplates (A, B, ...).
Then one page per level: the bins of that level in colour with their part id (K1, K2, ...
matching the exported file names), name and size; whatever stands below is drawn faintly so
it is clear what a stacked bin sits on.
"""

import os

from PIL import Image, ImageDraw, ImageFont

from . import logging_setup, printers
from .grid import EPS, fmt, hex_rgb, tint
from .i18n import T
from .planner import Scene, bin_widths, edges, level_role, part_text
from .render import render_zbuffer

log = logging_setup.get("layout_sheet")

PAGE = (1754, 1240)   # A4 landscape at 150 dpi
MARGIN = 70
LEGEND_W = 520
TILE_COLORS = ["#3b82f6", "#f59e0b", "#22c55e", "#ef4444", "#a855f7", "#14b8a6", "#ec4899", "#a16207"]


def _font(size, bold=False):
    names = ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf") if bold else ("segoeui.ttf", "arial.ttf",
                                                                                 "DejaVuSans.ttf")
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _rgb(col):
    return tuple(hex_rgb(col))


def _center_text(d, box, text, font, fill):
    x0, y0, x1, y1 = box
    tw, th = d.multiline_textbbox((0, 0), text, font=font, align="center")[2:]
    if tw > x1 - x0 - 4 or th > y1 - y0 - 4:
        return False
    d.multiline_text(((x0 + x1 - tw) / 2, (y0 + y1 - th) / 2), text, font=font, fill=fill, align="center")
    return True


def _page(title, subtitle):
    img = Image.new("RGB", PAGE, "white")
    d = ImageDraw.Draw(img)
    d.text((MARGIN, 40), title, font=_font(40, True), fill=(31, 41, 55))
    d.text((MARGIN, 92), subtitle, font=_font(22), fill=(107, 114, 128))
    return img, d


def _drawer_box(p):
    """Scale and mapping of drawer mm to page pixels (Y up)."""
    area_w = PAGE[0] - 2 * MARGIN - LEGEND_W - 40
    area_h = PAGE[1] - 150 - MARGIN
    s = min(area_w / p["width"], area_h / p["depth"])
    ox = MARGIN
    oy = 150 + (area_h + p["depth"] * s) / 2
    return s, (lambda x: ox + x * s), (lambda y: oy - y * s)


def _legend(d, numbered, x, y):
    """numbered: [(K number, part group), ...] - numbers stay those of the exported files."""
    d.text((x, y), T("Parts"), font=_font(26, True), fill=(31, 41, 55))
    y += 44
    for n, (_, widths, style, members) in numbered:
        if y > PAGE[1] - MARGIN - 60:
            d.text((x, y), "…", font=_font(20), fill=(107, 114, 128))
            break
        col = members[0][0]["color"]
        d.rounded_rectangle([x, y + 2, x + 26, y + 28], radius=5, fill=_rgb(col))
        names = ", ".join(sorted({b.get("name") or "" for b, _ in members} - {""}))
        d.text((x + 38, y), f"K{n}  {len(members)}x  {names}", font=_font(20, True), fill=(31, 41, 55))
        d.text((x + 38, y + 26), part_text(widths, style), font=_font(17), fill=(107, 114, 128))
        y += 62
    return y


def _draw_level(d, p, bins, labels, level, show_tiles):
    s, X, Y = _drawer_box(p)
    xe, ye = edges(p)
    d.rectangle([X(0), Y(p["depth"]), X(p["width"]), Y(0)], outline=(184, 191, 202), width=2)
    for f in p["fillers"]:
        (x, y), (sx, sy) = f["pos"], f["size"]
        d.rectangle([X(x), Y(y + sy), X(x + sx), Y(y)], fill=(203, 210, 219))
    for i in range(len(p["cols"])):
        for j in range(len(p["rows"])):
            d.rectangle([X(xe[i]), Y(ye[j + 1]), X(xe[i + 1]), Y(ye[j])], fill=(241, 243, 246),
                        outline=(214, 219, 227))
    if show_tiles:
        order = sorted({t["key"] for t in p["tiles"]}, key=lambda k: p["types"][k]["label"])
        for t in p["tiles"]:
            (x, y), (sx, sy) = t["pos"], t["size"]
            col = _rgb(TILE_COLORS[order.index(t["key"]) % len(TILE_COLORS)])
            d.rectangle([X(x) + 3, Y(y + sy) + 3, X(x + sx) - 3, Y(y) - 3], outline=col, width=4)
            d.text((X(x) + 12, Y(y + sy) + 8), T("Plate {l}", l=p["types"][t["key"]]["label"]),
                   font=_font(20, True), fill=col)
    inset = max(2, 0.25 * s + 2)
    for b in sorted(bins, key=lambda b: b["z"]):
        role = level_role(b, level)
        box = [X(xe[b["i"]]) + inset, Y(ye[b["j"] + b["nj"]]) + inset,
               X(xe[b["i"] + b["ni"]]) - inset, Y(ye[b["j"]]) - inset]
        label = labels.get(id(b), T("placeholder"))   # placeholders have no K number
        if role == "current":
            d.rounded_rectangle(box, radius=8, fill=_rgb(b["color"] if id(b) in labels else tint(b["color"], 0.45)),
                                outline="white", width=3)
            wx, wy = bin_widths(p, b)
            size = f"{fmt(sum(wx) - 0.5)} x {fmt(sum(wy) - 0.5)} mm, {fmt(b['style']['h'])} HE"
            for text in (f"{label}\n{b.get('name') or ''}\n{size}", f"{label}\n{b.get('name') or ''}", label):
                if _center_text(d, box, text.strip(), _font(20, True), "white"):
                    break
        elif role in ("below", "surface", "blocked") and b["z"] < level - EPS:
            d.rounded_rectangle(box, radius=8, fill=_rgb(tint(b["color"], 0.82)), outline=_rgb(tint(b["color"], 0.5)),
                                width=2)
            _center_text(d, box, f"{label}\n{T('below')}", _font(16), _rgb(tint(b["color"], 0.2)))


def layout_sheet(p, bins, groups, path, project_name="", png_dir=None, png=True):
    """Write the assembly sheet as PDF (plus page 1 as PNG in png_dir if png). groups: result of
    planner.part_groups (same order as the exported K numbers). Returns the written paths."""
    labels = {}
    for n, (_, _, _, members) in enumerate(groups, 1):
        for b, _ in members:
            labels[id(b)] = f"K{n}"
    levels = sorted({round(b["z"], 3) for b in bins}) or [0.0]
    title = project_name or T("Drawer {w} x {d} mm", w=fmt(p["width"]), d=fmt(p["depth"]))
    pages = []

    # page 1: overview in 3D and the baseplates
    img, d = _page(title, T("Assembly sheet – {n} bins on {k} level(s), printer {p}", n=len(bins),
                            k=len(levels), p=printers.printer_label()))
    try:
        v, f, c, _, _ = Scene().build(p, bins, -1.0)
        pic = render_zbuffer(v, f, -0.6, 0.55, (PAGE[0] - 2 * MARGIN - LEGEND_W - 40, PAGE[1] - 150 - MARGIN),
                     zoom=1.15, face_colors=c, bg=(255, 255, 255))
        img.paste(pic, (MARGIN, 150))
    except Exception:  # noqa: BLE001 - the sheet is still useful without the picture
        log.exception("3D picture for the assembly sheet failed")
    numbered = list(enumerate(groups, 1))
    _legend(d, numbered, PAGE[0] - MARGIN - LEGEND_W, 150)
    pages.append(img)

    # page 2: baseplates
    img, d = _page(title, T("Baseplates: where plates A, B, ... go"))
    _draw_level(d, p, [], labels, 0.0, show_tiles=True)
    y = 150
    d.text((PAGE[0] - MARGIN - LEGEND_W, y), T("Plates"), font=_font(26, True), fill=(31, 41, 55))
    y += 44
    for t in sorted(p["types"].values(), key=lambda t: t["label"]):
        d.text((PAGE[0] - MARGIN - LEGEND_W, y), f"{t['label']}: {t['count']}x  {fmt(t['size'][0])} x "
               f"{fmt(t['size'][1])} mm", font=_font(20), fill=(31, 41, 55))
        y += 32
    pages.append(img)

    # one page per level
    for z in levels:
        here = [b for b in bins if abs(b["z"] - z) < EPS]
        sub = T("Level 0: directly on the baseplate") if z < EPS else \
            T("Level {z} units: stacked on the bins drawn faintly", z=fmt(z))
        img, d = _page(f"{title} – {T('Level')} {fmt(z)}", sub + f"  ({len(here)} {T('bins')})")
        _draw_level(d, p, bins, labels, z, show_tiles=False)
        _legend(d, [(n, g) for n, g in numbered if any(abs(b["z"] - z) < EPS for b, _ in g[3])],
                PAGE[0] - MARGIN - LEGEND_W, 150)
        pages.append(img)

    pages[0].save(path, "PDF", resolution=150, save_all=True, append_images=pages[1:])
    log.info("Assembly sheet written: %s (%d pages)", path, len(pages))
    if not png:
        return [path]
    # first page also as PNG for a quick look
    png_path = os.path.join(png_dir or os.path.dirname(path), os.path.splitext(os.path.basename(path))[0] + ".png")
    pages[0].save(png_path)
    return [path, png_path]
