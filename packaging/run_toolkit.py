"""Entry point for the PyInstaller build (same as `python -m gridfinity_toolkit`)."""

import sys

from gridfinity_toolkit.cli import main

if __name__ == "__main__":
    sys.exit(main())
