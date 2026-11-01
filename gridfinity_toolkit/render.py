"""Software renderers without OpenGL.

render()          painter's algorithm with Pillow: fast, but overlapping parts can be sorted
                  wrongly; used for the live preview fallback.
render_zbuffer()  per-pixel depth test with numpy: slower but always correct; used for the
                  pictures in exported assembly sheets.
"""

import math

import numpy as np

BG = (247, 248, 250)


def render(v, f, yaw, pitch, size, zoom=1.0, color=(37, 99, 235), bg=BG, face_colors=None, ss=2):
    """Shaded image (painter's algorithm). yaw/pitch in radians."""
    from PIL import Image, ImageDraw
    w, h = size
    img = Image.new("RGB", (w * ss, h * ss), bg)
    if not len(f):
        return img.resize((w, h))
    p = v - (v.min(0) + v.max(0)) / 2
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    q = p @ (rx @ rz).T                      # x right, y depth, z up
    tri = q[f]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    ln = np.linalg.norm(n, axis=1)
    keep = (n[:, 1] < 0) & (ln > 1e-9)       # only faces towards the camera (-y)
    tri, n, ln = tri[keep], n[keep], ln[keep]
    base = np.asarray(face_colors, dtype=float)[keep] if face_colors is not None else None
    n = n / ln[:, None]
    light = np.array([-0.45, -0.75, 0.6])
    light /= np.linalg.norm(light)
    shade = 0.35 + 0.65 * np.clip(n @ light, 0, 1)
    order = np.argsort(-tri[:, :, 1].mean(1))  # back to front
    ext = np.ptp(q, axis=0)
    scale = zoom * 0.8 * min(w / max(ext[0], 1), h / max(ext[2], 1)) * ss
    sx = w * ss / 2 + tri[:, :, 0] * scale
    sz = h * ss / 2 - tri[:, :, 2] * scale
    col = np.clip(np.outer(shade, color) if base is None else base * shade[:, None], 0, 255).astype(int)
    draw = ImageDraw.Draw(img)
    for i in order:
        cc = tuple(col[i])
        draw.polygon([(sx[i, 0], sz[i, 0]), (sx[i, 1], sz[i, 1]), (sx[i, 2], sz[i, 2])], fill=cc, outline=cc)
    return img if ss == 1 else img.resize((w, h), Image.LANCZOS)


def _project(v, f, yaw, pitch, size, zoom, ss):
    """Rotate, cull back faces and project to pixels. Returns (screen x, screen y, depth, normals, keep)."""
    w, h = size
    p = v - (v.min(0) + v.max(0)) / 2
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    q = p @ (rx @ rz).T                      # x right, y depth (away from the camera), z up
    tri = q[f]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    ln = np.linalg.norm(n, axis=1)
    keep = (n[:, 1] < 0) & (ln > 1e-9)       # only faces towards the camera (-y)
    tri, n = tri[keep], n[keep] / ln[keep][:, None]
    ext = np.ptp(q, axis=0)
    scale = zoom * 0.8 * min(w / max(ext[0], 1), h / max(ext[2], 1)) * ss
    sx = w * ss / 2 + tri[:, :, 0] * scale
    sz = h * ss / 2 - tri[:, :, 2] * scale
    return sx, sz, tri[:, :, 1], n, keep


def render_zbuffer(v, f, yaw, pitch, size, zoom=1.0, color=(37, 99, 235), bg=BG, face_colors=None, ss=2):
    """Shaded image with a depth buffer, so hidden surfaces are always hidden. yaw/pitch in radians."""
    from PIL import Image
    w, h = size
    W, H = w * ss, h * ss
    img = np.empty((H, W, 3), dtype=np.uint8)
    img[:] = bg
    if not len(f):
        return Image.fromarray(img).resize((w, h))
    sx, sz, depth, n, keep = _project(np.asarray(v, float), np.asarray(f), yaw, pitch, size, zoom, ss)
    base = np.asarray(face_colors, dtype=float)[keep] if face_colors is not None else np.tile(color, (len(n), 1))
    light = np.array([-0.45, -0.75, 0.6])
    light /= np.linalg.norm(light)
    shade = 0.35 + 0.65 * np.clip(n @ light, 0, 1)
    col = np.clip(base * shade[:, None], 0, 255).astype(np.uint8)
    zbuf = np.full((H, W), np.inf)
    # pixel bounding box of every triangle
    x0 = np.clip(np.floor(sx.min(1)).astype(int), 0, W - 1)
    x1 = np.clip(np.ceil(sx.max(1)).astype(int), 0, W - 1)
    y0 = np.clip(np.floor(sz.min(1)).astype(int), 0, H - 1)
    y1 = np.clip(np.ceil(sz.max(1)).astype(int), 0, H - 1)
    for i in range(len(n)):
        if x1[i] < x0[i] or y1[i] < y0[i]:
            continue
        ax, bx, cx = sx[i]
        ay, by, cy = sz[i]
        area = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
        if abs(area) < 1e-9:
            continue
        px = np.arange(x0[i], x1[i] + 1) + 0.5
        py = np.arange(y0[i], y1[i] + 1)[:, None] + 0.5
        # barycentric coordinates via edge functions
        wa = ((bx - px) * (cy - py) - (by - py) * (cx - px)) / area
        wb = ((cx - px) * (ay - py) - (cy - py) * (ax - px)) / area
        wc = 1.0 - wa - wb
        inside = (wa >= -1e-6) & (wb >= -1e-6) & (wc >= -1e-6)
        if not inside.any():
            continue
        d = wa * depth[i, 0] + wb * depth[i, 1] + wc * depth[i, 2]
        zb = zbuf[y0[i]:y1[i] + 1, x0[i]:x1[i] + 1]
        hit = inside & (d < zb)
        zb[hit] = d[hit]
        img[y0[i]:y1[i] + 1, x0[i]:x1[i] + 1][hit] = col[i]
    out = Image.fromarray(img)
    return out if ss == 1 else out.resize((w, h), Image.LANCZOS)
