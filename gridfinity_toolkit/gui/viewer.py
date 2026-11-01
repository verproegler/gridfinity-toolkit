"""
3D view for bins and the planner.

Uses OpenGL (pyopengltk + PyOpenGL) when available: real depth testing and smooth rotation.
Without OpenGL, or if context creation fails, a software renderer (Pillow, painter's
algorithm) takes over automatically.

Controls: left drag = rotate, right/middle drag = pan, wheel = zoom, double-click = reset.
"""

import math
import tkinter as tk

import numpy as np

from .. import logging_setup
from ..render import BG, render

log = logging_setup.get("viewer")

BG_HEX = "#%02x%02x%02x" % BG

try:
    from OpenGL import GL
    from pyopengltk import OpenGLFrame
    HAVE_GL = True
except Exception:  # noqa: BLE001 - any import problem means: continue without OpenGL
    HAVE_GL = False
    log.warning("OpenGL not available, using software renderer", exc_info=True)


class Scene:
    """Prepared render data: 3 points per triangle with normal and colour, plus line segments."""

    def __init__(self, v, f, face_colors=None, color=(37, 99, 235), lines=None, line_colors=None):
        v = np.asarray(v, dtype=np.float64)
        f = np.asarray(f, dtype=np.int64)
        self.v, self.f = v, f
        fc = np.tile(color, (len(f), 1)) if face_colors is None else np.asarray(face_colors, dtype=float)
        # optional 4th column: opacity 0..1 (see-through faces are drawn after the solid ones)
        alpha = fc[:, 3] if fc.shape[1] > 3 else np.ones(len(fc))
        self.face_colors = fc[:, :3]   # the software fallback draws everything solid
        tri = v[f]
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        n = n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        rgba = np.column_stack([fc[:, :3] / 255.0, alpha])
        solid = alpha >= 0.999
        self.groups = []   # (positions, normals, RGBA colours, see-through)
        for sel, clear in ((solid, False), (~solid, True)):
            if sel.any():
                self.groups.append((np.ascontiguousarray(tri[sel].reshape(-1, 3), dtype=np.float32),
                                    np.ascontiguousarray(np.repeat(n[sel], 3, axis=0), dtype=np.float32),
                                    np.ascontiguousarray(np.repeat(rgba[sel], 3, axis=0), dtype=np.float32),
                                    clear))
        self.pos = np.ascontiguousarray(tri.reshape(-1, 3), dtype=np.float32)
        if lines is not None and len(lines):   # (m, 2, 3) segments, one colour per segment
            lines = np.asarray(lines, dtype=np.float64).reshape(-1, 2, 3)
            lc = np.tile([22, 163, 74], (len(lines), 1)) if line_colors is None else np.asarray(line_colors)
            self.lpos = np.ascontiguousarray(lines.reshape(-1, 3), dtype=np.float32)
            self.lcol = np.ascontiguousarray(np.repeat(lc / 255.0, 2, axis=0), dtype=np.float32)
        else:
            self.lpos = self.lcol = None
        pts = self.pos if self.lpos is None else np.concatenate([self.pos, self.lpos])
        if len(pts):
            lo, hi = pts.min(0), pts.max(0)
            self.center = (lo + hi) / 2
            self.radius = max(float(np.linalg.norm(hi - lo)) / 2, 1.0)
        else:
            self.center, self.radius = np.zeros(3), 50.0


class View3D:
    """Container holding an OpenGL view or the software fallback."""

    def __init__(self, parent):
        self.frame = tk.Frame(parent, background=BG_HEX)
        self.scene = None
        self.drag = None
        self.reset_view()
        self.impl = None
        if HAVE_GL:
            try:
                self.impl = _GLView(self.frame, self)
            except Exception:  # noqa: BLE001
                log.exception("OpenGL view not possible")
        if self.impl is None:
            self.impl = _SoftView(self.frame, self)
        self.impl.pack(fill="both", expand=True)
        self._bind(self.impl)

    def pack(self, **kw):
        self.frame.pack(**kw)

    def pack_forget(self):
        self.frame.pack_forget()

    def fallback(self):
        """Switch from OpenGL to software rendering (e.g. if the context fails)."""
        if isinstance(self.impl, _SoftView):
            return
        log.warning("Switching to software renderer")
        try:
            self.impl.destroy()
        except tk.TclError:
            pass
        self.impl = _SoftView(self.frame, self)
        self.impl.pack(fill="both", expand=True)
        self._bind(self.impl)
        self.redraw()

    def reset_view(self):
        self.yaw, self.elev, self.zoom = -35.0, 30.0, 1.0
        self.pan = [0.0, 0.0]

    def set(self, v, f, face_colors=None, lines=None, line_colors=None, keep_view=True):
        self.scene = Scene(v, f, face_colors, lines=lines, line_colors=line_colors)
        if not keep_view:
            self.reset_view()
        self.impl.scene_changed()
        self.redraw()

    def redraw(self, fast=False):
        self.impl.request(fast)

    def _bind(self, w):
        w.bind("<ButtonPress-1>", lambda e: self._press(e, "rotate"))
        w.bind("<ButtonPress-2>", lambda e: self._press(e, "pan"))
        w.bind("<ButtonPress-3>", lambda e: self._press(e, "pan"))
        for b in ("<B1-Motion>", "<B2-Motion>", "<B3-Motion>"):
            w.bind(b, self._drag)
        for b in ("<ButtonRelease-1>", "<ButtonRelease-2>", "<ButtonRelease-3>"):
            w.bind(b, lambda e: self.redraw())
        w.bind("<MouseWheel>", self._wheel)
        w.bind("<Double-Button-1>", lambda e: (self.reset_view(), self.redraw()))

    def _press(self, e, mode):
        self.drag = (mode, e.x, e.y, self.yaw, self.elev, list(self.pan))

    def _drag(self, e):
        if not self.drag:
            return
        mode, x0, y0, yaw0, elev0, pan0 = self.drag
        if mode == "rotate":
            self.yaw = yaw0 + (e.x - x0) * 0.4
            self.elev = min(max(elev0 + (e.y - y0) * 0.4, -89.0), 89.0)
        else:
            h = max(self.impl.winfo_height(), 1)
            r = (self.scene.radius if self.scene else 50.0) / self.zoom * 1.15
            self.pan = [pan0[0] + (e.x - x0) * 2 * r / h, pan0[1] - (e.y - y0) * 2 * r / h]
        self.redraw(fast=True)

    def _wheel(self, e):
        self.zoom = min(max(self.zoom * (1.12 if e.delta > 0 else 1 / 1.12), 0.2), 12.0)
        self.redraw()


# ---------------------------------------------------------------------------
# OpenGL
# ---------------------------------------------------------------------------

if HAVE_GL:
    class _GLView(OpenGLFrame):
        def __init__(self, parent, view):
            super().__init__(parent, width=400, height=300)
            self.view = view
            self.dlist = None
            self.dirty = True
            self.failed = False
            self.job = None
            self.width, self.height = 400, 300

        def tkMap(self, evt):
            try:
                super().tkMap(evt)
            except Exception:  # noqa: BLE001 - no OpenGL context: fall back to software
                log.exception("OpenGL context failed")
                self.failed = True
                self.after_idle(self.view.fallback)

        def tkResize(self, evt):
            self.width, self.height = evt.width, evt.height
            if self.context_created and not self.failed:
                self.request()

        def tkExpose(self, evt):
            if self.context_created and not self.failed:
                self.request()

        def initgl(self):
            GL.glClearColor(BG[0] / 255, BG[1] / 255, BG[2] / 255, 1.0)
            GL.glEnable(GL.GL_DEPTH_TEST)
            GL.glEnable(GL.GL_LIGHTING)
            GL.glEnable(GL.GL_LIGHT0)
            GL.glEnable(GL.GL_LIGHT1)
            GL.glEnable(GL.GL_NORMALIZE)
            GL.glLightModeli(GL.GL_LIGHT_MODEL_TWO_SIDE, GL.GL_TRUE)
            GL.glEnable(GL.GL_COLOR_MATERIAL)
            GL.glColorMaterial(GL.GL_FRONT_AND_BACK, GL.GL_AMBIENT_AND_DIFFUSE)
            GL.glLightModelfv(GL.GL_LIGHT_MODEL_AMBIENT, (0.30, 0.30, 0.30, 1.0))
            GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, (0.70, 0.70, 0.70, 1.0))
            GL.glLightfv(GL.GL_LIGHT1, GL.GL_DIFFUSE, (0.22, 0.22, 0.24, 1.0))
            GL.glShadeModel(GL.GL_FLAT)
            GL.glEnable(GL.GL_POLYGON_OFFSET_FILL)
            GL.glPolygonOffset(1.0, 1.0)   # lines stay visible on surfaces
            GL.glEnable(GL.GL_LINE_SMOOTH)
            self.dlist = None
            self.dirty = True

        def scene_changed(self):
            self.dirty = True

        def request(self, fast=False):
            """Redraw; several requests in a row are merged."""
            if self.failed or not self.context_created:
                return
            if self.job is None:
                self.job = self.after_idle(self._paint)

        def _paint(self):
            self.job = None
            try:
                self.tkMakeCurrent()
                self.redraw()
                self.tkSwapBuffers()
            except Exception:  # noqa: BLE001
                log.exception("OpenGL drawing failed")
                self.failed = True
                self.after_idle(self.view.fallback)

        def _compile(self, s):
            """Upload the scene once into a display list (fast redraws while rotating)."""
            if self.dlist:
                GL.glDeleteLists(self.dlist, 1)
            self.dlist = GL.glGenLists(1)
            GL.glNewList(self.dlist, GL.GL_COMPILE)
            # solid faces first; see-through faces afterwards, blended and without writing depth,
            # so everything behind them (solid or see-through) stays visible
            for pos, nrm, col, clear in s.groups:
                if clear:
                    GL.glEnable(GL.GL_BLEND)
                    GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
                    GL.glDepthMask(GL.GL_FALSE)
                GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
                GL.glEnableClientState(GL.GL_NORMAL_ARRAY)
                GL.glEnableClientState(GL.GL_COLOR_ARRAY)
                GL.glVertexPointer(3, GL.GL_FLOAT, 0, pos)
                GL.glNormalPointer(GL.GL_FLOAT, 0, nrm)
                GL.glColorPointer(4, GL.GL_FLOAT, 0, col)
                GL.glDrawArrays(GL.GL_TRIANGLES, 0, len(pos))
                GL.glDisableClientState(GL.GL_NORMAL_ARRAY)
                GL.glDisableClientState(GL.GL_COLOR_ARRAY)
                GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
                if clear:
                    GL.glDepthMask(GL.GL_TRUE)
                    GL.glDisable(GL.GL_BLEND)
            if s.lpos is not None:
                GL.glDisable(GL.GL_LIGHTING)
                GL.glLineWidth(1.6)
                GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
                GL.glEnableClientState(GL.GL_COLOR_ARRAY)
                GL.glVertexPointer(3, GL.GL_FLOAT, 0, s.lpos)
                GL.glColorPointer(3, GL.GL_FLOAT, 0, s.lcol)
                GL.glDrawArrays(GL.GL_LINES, 0, len(s.lpos))
                GL.glDisableClientState(GL.GL_COLOR_ARRAY)
                GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
                GL.glEnable(GL.GL_LIGHTING)
            GL.glEndList()
            self.dirty = False

        def redraw(self):
            w, h = max(self.width, 1), max(self.height, 1)
            GL.glViewport(0, 0, w, h)
            GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
            v, s = self.view, self.view.scene
            if s is None:
                return
            if self.dirty or self.dlist is None:
                self._compile(s)
            r = s.radius / v.zoom * 1.15
            a = w / h
            GL.glMatrixMode(GL.GL_PROJECTION)
            GL.glLoadIdentity()
            GL.glOrtho(-r * a - v.pan[0], r * a - v.pan[0], -r - v.pan[1], r - v.pan[1],
                       -20 * s.radius, 20 * s.radius)
            GL.glMatrixMode(GL.GL_MODELVIEW)
            GL.glLoadIdentity()
            # lights fixed to the camera: key light top left front, weak back light
            GL.glLightfv(GL.GL_LIGHT0, GL.GL_POSITION, (-0.45, 0.65, 1.0, 0.0))
            GL.glLightfv(GL.GL_LIGHT1, GL.GL_POSITION, (0.6, -0.4, 0.5, 0.0))
            GL.glRotatef(-(90.0 - v.elev), 1, 0, 0)   # Z points up
            GL.glRotatef(v.yaw, 0, 0, 1)
            GL.glTranslatef(*(-s.center))
            GL.glCallList(self.dlist)


# ---------------------------------------------------------------------------
# Software fallback (Pillow)
# ---------------------------------------------------------------------------

class _SoftView(tk.Canvas):
    def __init__(self, parent, view):
        super().__init__(parent, background=BG_HEX, highlightthickness=0)
        self.view = view
        self.photo = None
        self.job = None
        self.bind("<Configure>", lambda e: self.request())

    def scene_changed(self):
        pass

    def request(self, fast=False):
        if self.job:
            self.after_cancel(self.job)
        self.job = self.after(10 if fast else 30, lambda: self._paint(fast))

    def _paint(self, fast):
        from PIL import ImageTk
        self.job = None
        s, v = self.view.scene, self.view
        cw, ch = self.winfo_width(), self.winfo_height()
        if s is None or cw < 50:
            return
        try:
            img = render(s.v, s.f, math.radians(v.yaw), math.radians(v.elev), (cw, ch), v.zoom,
                         face_colors=s.face_colors, ss=1 if fast else 2)
        except Exception:  # noqa: BLE001
            log.exception("Software renderer failed")
            return
        self.photo = ImageTk.PhotoImage(img)
        self.delete("all")
        self.create_image(0, 0, image=self.photo, anchor="nw")
