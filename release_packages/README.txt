# Image Deduplicator v2.0.0 - Installation Guide

## Package Options

### Option 1: Python Package (Recommended)
For users with Python installed:

```bash
# Install from wheel
pip install image_deduplicator-2.0.0-py3-none-any.whl

# Or install from source
pip install image_deduplicator-2.0.0.tar.gz

# Run the application
image-deduplicator --gui
```

### Option 2: Standalone Executable
For users without Python:

1. Download `ImageDeduplicator.exe`
2. Double-click to run
3. No installation required

## Features

- Visual Review Interface with image thumbnails
- Individual image selection and deletion
- Side-by-side image comparison
- Streamlined workflow with optional confirmation skipping
- Granular safety controls (separate dry-run for bulk vs visual)
- Cross-platform support (Windows, Mac, Linux)

## Usage

1. Launch the application
2. Select your image directory
3. Adjust similarity threshold if needed
4. Click "Scan for Duplicates"
5. Switch to "Visual Review" tab
6. Review image thumbnails and delete unwanted duplicates

## Support

- GitHub Repository: https://github.com/MTGMAD/image-dedup
- Issues: https://github.com/MTGMAD/image-dedup/issues
- License: MIT

## System Requirements

- Python 3.7+ (for Python package)
- Windows 10+ (for standalone executable)
- 100MB free disk space
- Supported image formats: JPG, PNG, BMP, GIF, TIFF, WebP
