"""`python -m gridfinity_toolkit` starts the GUI; with arguments it runs the command line."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
