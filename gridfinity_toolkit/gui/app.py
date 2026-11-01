"""
Main window with three tabs:
    Baseplate      cut baseplates to a drawer
    Bin            single stackable bins with 3D preview
    Combined Grid  plan (stacked) bins on the grid of a baseplate project and export print plates

Top right: language flags (stored in settings.json). Log: logs/gridfinity_toolkit.log
"""

import tkinter as tk
from tkinter import messagebox, ttk

from .. import i18n, logging_setup, projects
from ..i18n import T
from . import theme, widgets

log = logging_setup.get("app")

TAB_BASE, TAB_BIN, TAB_PLANNER = 0, 1, 2


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.geometry("1360x880")
        self.root.minsize(1180, 740)
        theme.apply(self.root)
        logging_setup.install_tk_handler(self.root, lambda: T("Unexpected error"),
                                         lambda: T("Something went wrong:\n{e}\n\nDetails are in the log:\n{l}"))
        self.nb = None
        self.tabs = {}
        self._flag_images = []
        self.build({}, TAB_BASE)

    def build(self, states, selected):
        """(Re)build the user interface; states: remembered inputs per tab."""
        from . import baseplate_tab, bin_tab, planner_tab

        self.root.title(T("Gridfinity Toolkit"))
        for child in self.root.winfo_children():
            child.destroy()
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True)
        frames = []
        for title in (T("Baseplate"), T("Bin"), T("Combined Grid")):
            f = ttk.Frame(self.nb, style="App.TFrame")
            self.nb.add(f, text=title)
            frames.append(f)
        self.tabs = {}
        # build the planner first: the Bin tab asks it for the names already in use
        for key, mod, idx in (("planner", planner_tab, TAB_PLANNER), ("baseplate", baseplate_tab, TAB_BASE),
                              ("bin", bin_tab, TAB_BIN)):
            try:
                self.tabs[key] = mod.build(frames[idx], self, states.get(key))
            except Exception as e:  # noqa: BLE001 - one broken tab must not take the others down
                log.exception("Tab %s could not be built", key)
                ttk.Label(frames[idx], style="Error.TLabel", padding=20,
                          text=T("This tab could not be loaded:\n{e}\n\nDetails in the log:\n{l}",
                                 e=e, l=logging_setup.LOG_FILE)).pack(anchor="nw")
        self._build_flags()
        self.nb.select(selected)
        self.root.after(200, self.fit_window)
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self.projects_changed(force=False))
        if not hasattr(self, "_shown"):
            self._shown = True
            if len(self.tabs) < 3:
                messagebox.showwarning(T("Note"), T("Not all tabs could be loaded, see log:\n{l}",
                                                    l=logging_setup.LOG_FILE))

    def _build_flags(self):
        """Language flags at the top right of the tab bar; the active one is framed."""
        from . import help as help_window
        bar = tk.Frame(self.root, background=theme.BG)
        bar.place(relx=1.0, x=-14, y=8, anchor="ne")
        self._flag_images = []
        hlp = tk.Label(bar, text="?", cursor="hand2", background=theme.BG, foreground=theme.ACCENT,
                       font=(theme.FONT, 11, "bold"), padx=6, highlightthickness=1,
                       highlightbackground=theme.ACCENT)
        hlp.pack(side="left", padx=(0, 10))
        hlp.bind("<Button-1>", lambda e: help_window.show(self.root, self.nb.index("current")))
        widgets.tip(hlp, T("Help for this tab (F1)"))
        self.root.bind("<F1>", lambda e: help_window.show(self.root, self.nb.index("current")))
        for code in ("de", "en"):
            active = code == i18n.lang()
            img = widgets.flag_image(code, active)
            self._flag_images.append(img)   # keep a reference or Tk drops the image
            lbl = tk.Label(bar, image=img, cursor="hand2", borderwidth=0, background=theme.BG, highlightthickness=2,
                           highlightbackground=theme.ACCENT if active else theme.BG)
            lbl.pack(side="left", padx=3)
            lbl.bind("<Button-1>", lambda e, c=code: c != i18n.lang() and self.switch_language(c))
            widgets.tip(lbl, i18n.LANGUAGES[code])

    def fit_window(self, tries=20):
        """Make the window tall enough that no tab needs its scrollbar, limited to the screen.
        Retries until the window is actually shown (sizes are only known then)."""
        if not self.root.winfo_ismapped() or self.root.winfo_height() < 100:
            if tries:
                self.root.after(150, lambda: self.fit_window(tries - 1))
            return
        try:
            self.root.update_idletasks()
            panels = []

            def walk(wd):
                for c in wd.winfo_children():
                    if isinstance(c, widgets.ScrollPanel):
                        panels.append(c)
                    walk(c)

            walk(self.root)
            visible = [p for p in panels if p.canvas.winfo_height() > 10]
            if not panels or not visible:
                if tries:
                    self.root.after(150, lambda: self.fit_window(tries - 1))
                return
            need = max(p.inner.winfo_reqheight() for p in panels)
            overhead = self.root.winfo_height() - max(p.canvas.winfo_height() for p in visible)
            top, bottom = work_area(self.root)
            frame = 40   # title bar and border
            height = min(need + overhead + 6, bottom - top - frame)
            if height <= self.root.winfo_height():
                return
            y = max(top, min(self.root.winfo_y(), bottom - frame - height))
            self.root.geometry(f"{self.root.winfo_width()}x{height}+{self.root.winfo_x()}+{y}")
            log.info("Window height set to %d px (content %d px)", height, need)
        except tk.TclError:
            log.exception("Could not fit the window")

    def switch_language(self, code):
        from .. import bins as binlib
        states = {k: t.get_state() for k, t in self.tabs.items() if hasattr(t, "get_state")}
        selected = self.nb.index("current")
        # default names belong to the language: only keep names the user typed
        if "baseplate" in states and states["baseplate"].get("name") == states["baseplate"].get("auto_name"):
            states["baseplate"]["name"] = ""
        if "bin" in states and binlib.is_default_bin_name(states["bin"].get("name", "")):
            states["bin"]["name"] = ""
        log.info("Language: %s -> %s", i18n.lang(), code)
        i18n.set_lang(code)
        i18n.save_settings(language=code)
        self.build(states, selected)

    # --- links between the tabs -------------------------------------------
    def _call(self, key, method, *args):
        tab = self.tabs.get(key)
        if tab and hasattr(tab, method):
            try:
                return getattr(tab, method)(*args)
            except Exception:  # noqa: BLE001
                log.exception("%s.%s failed", key, method)
        return None

    def projects_changed(self, force=True):
        """Re-read the project lists; after saving in the Baseplate tab also reload the open
        planner project."""
        self._call("bin", "refresh")
        self._call("planner", "refresh", force)

    def printer_changed(self):
        """Bed size changed: re-run the checks in Bin and Combined Grid."""
        self._call("bin", "refresh")
        self._call("planner", "refresh", True)

    def open_project(self, name):
        if "planner" in self.tabs:
            self._call("planner", "select_project", name)
            self.nb.select(TAB_PLANNER)

    def add_bin_type(self, t, old=None):
        if "planner" in self.tabs:
            self._call("planner", "add_type", t, old)
            self.nb.select(TAB_PLANNER)

    def edit_bin_type(self, t):
        if "bin" in self.tabs:
            self._call("bin", "load_type", t)
            self.nb.select(TAB_BIN)

    def bin_tab_style(self):
        return self._call("bin", "current_style")

    def show_planner(self):
        if "planner" in self.tabs:
            self.nb.select(TAB_PLANNER)

    def planner_type_names(self):
        return self._call("planner", "type_names") or []


def work_area(root):
    """(top, bottom) of the usable screen area (without the taskbar)."""
    try:
        import ctypes
        from ctypes import wintypes
        rect = wintypes.RECT()
        if ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(rect), 0):   # SPI_GETWORKAREA
            return rect.top, rect.bottom
    except (AttributeError, OSError):   # not Windows
        pass
    return 0, root.winfo_screenheight() - 60


def run():
    logging_setup.setup()
    projects.migrate()
    try:
        app = App()
    except Exception:
        log.critical("Start failed", exc_info=True)
        raise
    app.root.mainloop()
    log.info("Closed")
