#!/usr/bin/env python3
"""
Script to create GitHub releases with multiple package formats
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return None

def create_release_packages():
    """Create all package formats for release."""
    
    print("🚀 Creating GitHub Release Packages for Image Deduplicator")
    print("=" * 60)
    
    # 1. Build Python packages
    print("\n📦 Building Python packages...")
    run_command("python -m build", "Building Python wheel and source distribution")
    
    # 2. Create standalone executable
    print("\n🔨 Building standalone executable...")
    run_command("pyinstaller --onefile --windowed --name ImageDeduplicator image_deduplicator.py", 
                "Creating Windows executable")
    
    # 3. Create release directory
    release_dir = Path("release_packages")
    release_dir.mkdir(exist_ok=True)
    
    # 4. Copy packages to release directory
    print("\n📁 Organizing release packages...")
    
    # Copy Python packages
    if Path("dist/image_deduplicator-2.0.0-py3-none-any.whl").exists():
        run_command(f"copy dist\\image_deduplicator-2.0.0-py3-none-any.whl {release_dir}\\", 
                   "Copying Python wheel")
    
    if Path("dist/image_deduplicator-2.0.0.tar.gz").exists():
        run_command(f"copy dist\\image_deduplicator-2.0.0.tar.gz {release_dir}\\", 
                   "Copying Python source distribution")
    
    # Copy Windows executable
    if Path("dist/ImageDeduplicator.exe").exists():
        run_command(f"copy dist\\ImageDeduplicator.exe {release_dir}\\", 
                   "Copying Windows executable")
    
    # 5. Create installation instructions
    create_installation_guide(release_dir)
    
    print(f"\n✅ All packages created in '{release_dir}' directory")
    print("\n📋 Package Summary:")
    print("   • Python Wheel (.whl) - For pip installation")
    print("   • Python Source (.tar.gz) - For manual installation")
    print("   • Windows Executable (.exe) - Standalone application")
    print("   • Installation Guide (README.txt) - Usage instructions")
    
    return release_dir

def create_installation_guide(release_dir):
    """Create installation guide for users."""
    guide_content = """# Image Deduplicator v2.0.0 - Installation Guide

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
"""
    
    guide_path = release_dir / "README.txt"
    with open(guide_path, 'w', encoding='utf-8') as f:
        f.write(guide_content)
    
    print(f"✅ Created installation guide: {guide_path}")

if __name__ == "__main__":
    create_release_packages()
