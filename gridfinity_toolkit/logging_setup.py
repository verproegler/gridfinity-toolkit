"""
Logging and error capture.

Every module gets its logger via get("name"). setup() writes to logs/gridfinity_toolkit.log
(rotating, 3 x 1 MB) and records unhandled exceptions from Python (sys.excepthook) and from
Tk callbacks (report_callback_exception).
"""

import logging
import logging.handlers
import os
import platform
import sys

from . import paths

LOG_FILE = os.path.join(paths.LOGS, "gridfinity_toolkit.log")

_root = logging.getLogger("gridfinity")


def get(name):
    return logging.getLogger(f"gridfinity.{name}")


def setup(debug=False):
    """Configure the log file (calling it twice is harmless)."""
    if _root.handlers:
        return _root
    _root.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    try:
        os.makedirs(paths.LOGS, exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        fh.setFormatter(fmt)
        fh.setLevel(logging.DEBUG if debug else logging.INFO)
        _root.addHandler(fh)
    except OSError as e:   # e.g. read-only folder: console only
        print(f"Cannot write log file: {e}", file=sys.stderr)
    if sys.stderr is not None and getattr(sys.stderr, "isatty", lambda: False)():
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        sh.setLevel(logging.INFO)
        _root.addHandler(sh)

    def hook(exc_type, exc, tb):
        _root.critical("Unhandled exception", exc_info=(exc_type, exc, tb))
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = hook
    _root.info("Start: Python %s, %s, folder %s", platform.python_version(), platform.platform(), paths.ROOT)
    return _root


def install_tk_handler(root, title, message):
    """Log errors raised in Tk callbacks and show them instead of failing silently.
    title/message are callables (so they follow the current language); message gets {e} and {l}."""
    from tkinter import messagebox

    def report(exc_type, exc, tb):
        _root.error("Error in the user interface", exc_info=(exc_type, exc, tb))
        try:
            messagebox.showerror(title(), message().format(e=f"{exc_type.__name__}: {exc}", l=LOG_FILE))
        except Exception:  # noqa: BLE001 - the error dialog itself must never fail
            pass

    root.report_callback_exception = report
