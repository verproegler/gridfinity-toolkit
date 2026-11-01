"""Locations of assets, user data and logs.

Assets live in the repository. User data (output, logs, settings) defaults to the repository
root as well; set GRIDFINITY_TOOLKIT_DATA to another folder to keep it elsewhere (handy for
tests or a shared network drive).

In a PyInstaller build (sys.frozen) the assets come from the bundle and the user data
defaults to the folder of the .exe."""

import os
import sys

FROZEN = bool(getattr(sys, "frozen", False))
if FROZEN:
    ROOT = os.path.dirname(os.path.abspath(sys.executable))
    ASSETS = os.path.join(getattr(sys, "_MEIPASS", ROOT), "assets")
else:
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ASSETS = os.path.join(ROOT, "assets")
DATA = os.path.abspath(os.environ.get("GRIDFINITY_TOOLKIT_DATA") or ROOT)

PROJECTS = os.path.join(DATA, "projects")   # project data: projects/<name>/project.json, layout.json, ...
OUTPUT = os.path.join(DATA, "output")       # generated files: output/<name>/ (print plates, assembly sheet)
LOGS = os.path.join(DATA, "logs")
SETTINGS_FILE = os.path.join(DATA, "settings.json")

BIN_OUTPUT = os.path.join(OUTPUT, "bins")                  # single bins saved from the Bin tab
BIN_TYPES_FILE = os.path.join(PROJECTS, "bin_types.json")  # bin types shared by all planner projects
LEGACY_BIN_TYPES_FILE = os.path.join(OUTPUT, "bin_types.json")
