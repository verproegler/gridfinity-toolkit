"""
Projects in the projects folder.

A project is a folder projects/<name>/ with
    project.json   parameters of the baseplate plan (used by the Bin and Planner tabs)
    summary.txt    human readable overview
    layout.json    bins placed in the planner, optional inner drawer height
Bin types used by the planner are shared by all projects (projects/bin_types.json).
Generated files go to output/<name>/ (see output_dir).

Older files with German names and values (projekt.json, kombiraster.json, kombi_typen.json,
"geschlossen"/"sechseck") are still read; projects of older versions that lived in output/<name>/
are moved by migrate().
"""

import json
import os
import shutil
import sys

from . import logging_setup, paths
from .i18n import T

log = logging_setup.get("projects")

PROJECT_FILE = "project.json"
SUMMARY_FILE = "summary.txt"
LAYOUT_FILE = "layout.json"
LEGACY_EXPORT_DIR = "print_export"   # planner export inside the project folder (before 2026-11)
PROJECT_DATA = (PROJECT_FILE, SUMMARY_FILE, LAYOUT_FILE, "projekt.json", "kombiraster.json")

LEGACY_PROJECT_FILE = "projekt.json"
LEGACY_LAYOUT_FILE = "kombiraster.json"
LEGACY_TYPES_FILE = os.path.join(paths.OUTPUT, "kombi_typen.json")
LEGACY_FILL = {"geschlossen": "solid", "sechseck": "hex"}


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def load_json(path, default):
    if not os.path.isfile(path):
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        log.exception("File %s unreadable, using default", path)
        return default


def save_json(path, data):
    """Write atomically: complete temp file first, then replace."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1)
        os.replace(tmp, path)
    except OSError:
        log.exception("Could not save %s", path)
        raise


def normalize_style(style):
    """Bring a bin style from older files up to date (German fill values)."""
    style = dict(style)
    style["fill"] = LEGACY_FILL.get(style.get("fill"), style.get("fill", "solid"))
    style.setdefault("base", "lite")
    style.setdefault("magnets", False)
    from .bins import STYLE_DEFAULTS
    for k, v in STYLE_DEFAULTS.items():
        style.setdefault(k, v)
    return style


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

def project_file(folder):
    path = os.path.join(folder, PROJECT_FILE)
    legacy = os.path.join(folder, LEGACY_PROJECT_FILE)
    return path if os.path.isfile(path) or not os.path.isfile(legacy) else legacy


def project_dir(name):
    return os.path.join(paths.PROJECTS, name)


def output_dir(name):
    """Folder for the generated files of a project."""
    return os.path.join(paths.OUTPUT, name)


def list_projects(out_dir=paths.PROJECTS):
    """Project folder names, most recently changed first."""
    if not os.path.isdir(out_dir):
        return []
    found = []
    for name in os.listdir(out_dir):
        d = os.path.join(out_dir, name)
        if os.path.isdir(d) and os.path.isfile(project_file(d)):
            found.append((os.path.getmtime(d), name))
    return [n for _, n in sorted(found, reverse=True)]


def save_project(p, out_dir, name):
    """Write project.json and summary.txt."""
    from .baseplate import side_note, summary
    folder = os.path.join(out_dir, name)
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, SUMMARY_FILE), "w", encoding="utf-8") as f:
        f.write(summary(p) + "\n\n" + side_note(p) + "\n")
    save_json(os.path.join(folder, PROJECT_FILE), p["params"])
    return folder


def load_project(folder):
    """Baseplate plan of a project folder."""
    from .baseplate import plan
    pj = project_file(folder)
    try:
        with open(pj, encoding="utf-8") as f:
            params = json.load(f)
        return plan(**params)
    except FileNotFoundError:
        raise ValueError(T("No {f} in {d}.", f=PROJECT_FILE, d=folder)) from None
    except (ValueError, TypeError) as e:
        log.exception("Project file %s invalid", pj)
        raise ValueError(T("Project file {f} is invalid: {e}", f=pj, e=e)) from e


def delete_project(name, out_dir=paths.PROJECTS):
    """Move a project folder to the recycle bin (Windows) or delete it."""
    folder = os.path.join(out_dir, name)
    if not os.path.isfile(project_file(folder)):
        raise ValueError(T("'{n}' is not a project folder.", n=name))
    move_to_trash(folder)
    log.info("Project %s deleted", name)


def move_to_trash(path):
    """Recycle bin on Windows (can be restored), plain delete elsewhere."""
    path = os.path.abspath(path)
    if sys.platform != "win32":
        shutil.rmtree(path)
        return
    import ctypes
    from ctypes import wintypes

    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT), ("pFrom", wintypes.LPCWSTR),
                    ("pTo", wintypes.LPCWSTR), ("fFlags", ctypes.c_uint16), ("fAnyOperationsAborted", wintypes.BOOL),
                    ("hNameMappings", ctypes.c_void_p), ("lpszProgressTitle", wintypes.LPCWSTR)]

    FO_DELETE, FOF_SILENT, FOF_NOCONFIRMATION, FOF_ALLOWUNDO, FOF_NOERRORUI = 3, 0x4, 0x10, 0x40, 0x400
    op = SHFILEOPSTRUCTW(None, FO_DELETE, path + "\0", None,
                         FOF_SILENT | FOF_NOCONFIRMATION | FOF_ALLOWUNDO | FOF_NOERRORUI, False, None, None)
    res = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    if res != 0 or op.fAnyOperationsAborted or os.path.exists(path):
        raise OSError(T("Could not move {p} to the recycle bin (code {c}).", p=path, c=res))


def migrate():
    """Move projects of older versions from output/<name>/ to projects/<name>/ (project data only).
    Their old exports are tidied up: the assembly sheet and the file with all print plates move
    to output/<name>/, the old single-files folders go to the recycle bin. Safe to call on every
    start; returns the names of the moved projects."""
    moved = []
    if not os.path.isdir(paths.OUTPUT):
        return moved
    if os.path.isfile(paths.LEGACY_BIN_TYPES_FILE) and not os.path.isfile(paths.BIN_TYPES_FILE):
        os.makedirs(paths.PROJECTS, exist_ok=True)
        shutil.move(paths.LEGACY_BIN_TYPES_FILE, paths.BIN_TYPES_FILE)
        log.info("Moved bin types to %s", paths.BIN_TYPES_FILE)
    for name in sorted(os.listdir(paths.OUTPUT)):
        old = os.path.join(paths.OUTPUT, name)
        if not os.path.isdir(old) or not any(os.path.isfile(os.path.join(old, f)) for f in
                                             (PROJECT_FILE, LEGACY_PROJECT_FILE)):
            continue
        new = project_dir(name)
        if os.path.exists(new):
            log.warning("Not migrating %s: %s already exists", old, new)
            continue
        try:
            os.makedirs(new)
            for fn in PROJECT_DATA:
                if os.path.isfile(os.path.join(old, fn)):
                    shutil.move(os.path.join(old, fn), os.path.join(new, fn))
            _tidy_old_export(old)
            moved.append(name)
            log.info("Migrated project %s to %s", name, new)
        except OSError:
            log.exception("Migrating project %s failed", name)
    return moved


def _tidy_old_export(folder):
    """Old layout: print_export/{assembly sheet, all plates, single files}, plus baseplate files
    in the project folder itself. Keeps the complete files, recycles the rest."""
    old_export = os.path.join(folder, LEGACY_EXPORT_DIR)
    if os.path.isdir(old_export):
        keep = [f for f in os.listdir(old_export) if os.path.isfile(os.path.join(old_export, f))
                and f.lower().endswith((".pdf", ".3mf"))]
        for f in keep:   # the planner file replaces the baseplate-only file of the same name
            if os.path.isfile(os.path.join(folder, f)):
                move_to_trash(os.path.join(folder, f))
            shutil.move(os.path.join(old_export, f), os.path.join(folder, f))
    for d in (old_export, os.path.join(folder, T("Single_files")), os.path.join(folder, "Einzeldateien"),
              os.path.join(folder, "Single_files"), os.path.join(folder, "STL")):
        if os.path.isdir(d):
            move_to_trash(d)
    for f in os.listdir(folder):   # even older exports: loose STL/3MF files next to the project files
        path = os.path.join(folder, f)
        if os.path.isfile(path) and (f.lower().endswith((".stl", ".png", ".txt")) or
                                     (f.lower().endswith(".3mf") and "_Bambu_" not in f)):
            move_to_trash(path)


# ---------------------------------------------------------------------------
# Planner layout and bin types
# ---------------------------------------------------------------------------

def load_layout(folder):
    """Placed bins of a project (list of dicts)."""
    path = os.path.join(folder, LAYOUT_FILE)
    if not os.path.isfile(path):
        path = os.path.join(folder, LEGACY_LAYOUT_FILE)
    bins = load_json(path, {}).get("bins", [])
    for b in bins:
        if isinstance(b, dict) and "style" in b:
            b["style"] = normalize_style(b["style"])
    return bins


def save_layout(folder, bins):
    """Write the bins, keeping the other entries of layout.json (e.g. the drawer height)."""
    path = os.path.join(folder, LAYOUT_FILE)
    data = load_json(path, {})
    data = data if isinstance(data, dict) else {}
    data["bins"] = bins
    save_json(path, data)


def load_drawer_height(folder):
    """Inner drawer height in mm, None if not set."""
    h = load_json(os.path.join(folder, LAYOUT_FILE), {}).get("drawer_height")
    return float(h) if isinstance(h, (int, float)) and h > 0 else None


def save_drawer_height(folder, h):
    path = os.path.join(folder, LAYOUT_FILE)
    data = load_json(path, {})
    data = data if isinstance(data, dict) else {}
    data.setdefault("bins", [])
    if h:
        data["drawer_height"] = h
    else:
        data.pop("drawer_height", None)
    save_json(path, data)


def load_bin_types():
    path = next((x for x in (paths.BIN_TYPES_FILE, paths.LEGACY_BIN_TYPES_FILE, LEGACY_TYPES_FILE)
                 if os.path.isfile(x)), paths.BIN_TYPES_FILE)
    types = load_json(path, None)
    if not isinstance(types, list):
        return None
    return [dict(normalize_style(t)) for t in types if isinstance(t, dict)]


def save_bin_types(types):
    save_json(paths.BIN_TYPES_FILE, types)
