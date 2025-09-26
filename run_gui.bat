#!/bin/sh
# Small wrapper for cross-platform convenience.
# On Linux/macOS, instruct user to run the shell helper or python directly.
echo "run_gui.bat is the Windows batch launcher."
echo "You're on a Unix-like system; run one of these instead:"
echo "  ./run_gui.sh            # uses .venv/bin/python if present"
echo "  .venv/bin/python image_deduplicator.py --gui"
exit 0
