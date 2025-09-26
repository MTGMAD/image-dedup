#!/bin/bash
# Linux/macOS shell script to launch Image Deduplicator GUI
echo "Starting Image Deduplicator GUI..."
# Use the project's virtualenv python if available
if [ -x ".venv/bin/python" ]; then
	.venv/bin/python image_deduplicator.py --gui
else
	python3 image_deduplicator.py --gui
fi
