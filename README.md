# Image Deduplicator

A cross-platform Python application to find and manage duplicate images using perceptual hashing. The tool can identify visually similar images even if they have different file names, sizes, or slight variations.

## Features

- **Cross-platform**: Works on Windows, macOS, and Linux
- **Dual Interface**: Both command-line and graphical user interface
- **Visual Review Interface**: See actual duplicate images with thumbnails
- **Individual Image Control**: Select which specific images to keep/delete
- **Side-by-Side Comparison**: Compare duplicate images in a popup window
- **Streamlined Workflow**: Skip confirmation dialogs for fast visual review
- **Perceptual Hashing**: Finds similar images, not just identical files
- **Smart Detection**: Identifies exact duplicates and visually similar images
- **Granular Safety Controls**: Separate dry-run settings for bulk vs individual operations
- **Space Analysis**: Shows how much disk space can be saved
- **Multiple Formats**: Supports JPG, PNG, BMP, GIF, TIFF, WebP

## Installation

### Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

### Install Dependencies

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install Pillow imagehash
```

## Usage

### GUI Mode (Recommended for beginners)

Launch the graphical interface:

```bash
python image_deduplicator.py --gui
```

Or simply run without arguments:

```bash
python image_deduplicator.py
```

**GUI Features:**

**Main Interface:**
- Browse and select image directories
- Adjustable similarity threshold
- Bulk dry-run mode toggle
- Real-time progress indication with percentage
- Responsive interface (non-blocking processing)
- Cancel scan functionality

**Tabbed Results Interface:**
- **Text Results Tab**: Traditional text-based duplicate information
- **Visual Review Tab**: Interactive image review with thumbnails

**Visual Review Features:**
- **Image Thumbnails**: See actual duplicate images (200x200px)
- **Group Selector**: Choose which duplicate group to review
- **Individual Selection**: Checkboxes to choose which images to keep
- **File Information**: Display file name, size, dimensions, and format
- **Side-by-Side Comparison**: Popup window for detailed image comparison
- **Individual Delete Buttons**: Delete specific images directly from visual interface
- **Streamlined Workflow**: Skip confirmation dialogs for fast visual review
- **Visual Safety Controls**: Separate dry-run settings for visual deletions
- **Smart Interface Updates**: Automatic refresh after deletions

### Command-Line Mode

#### Basic Usage

```bash
# Scan a directory for duplicates (dry run)
python image_deduplicator.py /path/to/your/images

# Scan with custom similarity threshold
python image_deduplicator.py --threshold 3 /path/to/your/images

# Actually delete duplicates (be careful!)
python image_deduplicator.py --no-dry-run /path/to/your/images
```

#### Advanced Options

```bash
# Save results to JSON file
python image_deduplicator.py --output results.json /path/to/images

# High sensitivity (finds more similar images)
python image_deduplicator.py --threshold 2 /path/to/images

# Low sensitivity (only very similar images)
python image_deduplicator.py --threshold 10 /path/to/images
```

### Command-Line Arguments

- `directory`: Path to directory containing images to scan
- `--gui`: Launch graphical user interface
- `--threshold N`: Similarity threshold (0-20, default: 5)
  - **Lower values (0-3)**: More sensitive - finds images that are very similar but not identical
    - Catches images with slight differences (different sizes, compression, minor edits)
    - Example: Same photo in different formats/sizes will be found as duplicates
  - **Higher values (10-20)**: Less sensitive - only finds images that are nearly identical
    - Ignores images with noticeable differences
    - Example: Only finds exact duplicates or very minor variations
  - **Recommended**: Start with 5 (default), then adjust based on your results
- `--no-dry-run`: Actually delete files (default is dry run)
- `--output FILE`: Save results to JSON file

## How It Works

### Perceptual Hashing

The application uses perceptual hashing to identify similar images:

1. **Average Hash**: Converts images to grayscale and creates a hash based on average brightness
2. **Hamming Distance**: Compares hashes to determine similarity
3. **Threshold**: Configurable sensitivity for similarity detection

### Duplicate Detection Process

1. **File Discovery**: Recursively scans directory for supported image formats
2. **Hash Generation**: Creates both MD5 (exact) and perceptual (similar) hashes
3. **Grouping**: Groups files by similarity using configurable threshold
4. **Analysis**: Identifies largest file in each group to keep
5. **Recommendation**: Suggests deletion of smaller duplicates

### File Selection Logic

For each duplicate group:
- **Keep**: The largest file (by file size)
- **Delete**: All other files in the group
- **Space Saved**: Total size of files marked for deletion

## Supported Formats

- JPEG (.jpg, .jpeg)
- PNG (.png)
- BMP (.bmp)
- GIF (.gif)
- TIFF (.tiff)
- WebP (.webp)

## Safety Features

### Dry Run Mode (Default)

- **No files are deleted** unless explicitly requested
- Shows exactly what would be deleted
- Displays space savings
- Allows review before actual deletion

### Confirmation Prompts

- CLI mode asks for confirmation before deletion
- GUI mode shows confirmation dialog
- Clear indication of files to be deleted

### Error Handling

- Graceful handling of corrupted or unreadable images
- Continues processing even if some files fail
- Reports errors without stopping the scan

## Examples

### Example 1: Basic Duplicate Detection

```bash
python image_deduplicator.py ~/Pictures
```

Output:
```
Scanning directory: /home/user/Pictures
Found 1250 image files
Processing images...
Processed 1250/1250 files...

============================================================
DUPLICATE DETECTION RESULTS
============================================================
Total files scanned: 1250
Files processed: 1250
Duplicate groups found: 15
Files that can be deleted: 23
Space that can be saved: 45.2 MB

Group 1 (exact duplicates):
  Keep: /home/user/Pictures/vacation/IMG_001.jpg (2.1 MB)
  Delete: /home/user/Pictures/backup/IMG_001_copy.jpg (2.1 MB)
  Space saved: 2.1 MB
```

### Example 2: High Sensitivity Scan

```bash
python image_deduplicator.py --threshold 2 ~/Pictures
```

This will find more similar images, including those with slight variations.

### Example 3: Visual Review Workflow

```bash
# Launch the GUI with visual interface
python image_deduplicator.py --gui

# 1. Select your image directory
# 2. Adjust similarity threshold if needed
# 3. Click "Scan for Duplicates"
# 4. Switch to "Visual Review" tab
# 5. Select duplicate groups from dropdown
# 6. Review image thumbnails and file information
# 7. Use "Compare with others" for side-by-side comparison
# 8. Click "Delete This Image" for individual deletions
# 9. Or use checkboxes + "Delete Selected" for bulk operations
```

### Example 4: Save Results and Delete

```bash
# First, save results for review
python image_deduplicator.py --output scan_results.json ~/Pictures

# Review the JSON file, then delete if satisfied
python image_deduplicator.py --no-dry-run ~/Pictures
```

## Troubleshooting

### Common Issues

**"Required libraries not installed"**
```bash
pip install Pillow imagehash
```

**"Directory does not exist"**
- Check the path is correct
- Use absolute paths if relative paths don't work

**"No images found"**
- Ensure directory contains supported image formats
- Check file permissions

**GUI doesn't start**
- Install tkinter: `sudo apt-get install python3-tk` (Linux)
- Or use command-line mode

### Performance Tips

- **Large directories**: The tool processes images sequentially for memory efficiency
- **Network drives**: May be slower due to file access overhead
- **SSD vs HDD**: SSD will provide faster file access

## Technical Details

### Memory Usage

- Processes images one at a time to minimize memory usage
- Hash storage is efficient (64-bit hashes)
- Suitable for directories with thousands of images

### Performance

- Typical processing: 50-100 images per second
- Depends on image size and storage speed
- Real-time progress indication with percentage
- Responsive GUI that doesn't freeze during processing
- Cancel functionality for long-running scans

## License

MIT License - Feel free to modify and distribute.

## Contributing

Contributions welcome! Areas for improvement:

- Additional image formats
- More sophisticated similarity algorithms
- Batch processing options
- Integration with cloud storage
- Advanced filtering options

## Changelog

### Version 2.0.0 - Visual Interface Update
- **NEW**: Visual Review tab with image thumbnails
- **NEW**: Individual image selection and deletion
- **NEW**: Side-by-side image comparison popup
- **NEW**: Streamlined workflow with optional confirmation skipping
- **NEW**: Granular safety controls (separate dry-run for bulk vs visual)
- **NEW**: Real-time interface updates after deletions
- **NEW**: Enhanced file information display
- **IMPROVED**: Tabbed interface for better organization
- **IMPROVED**: Smart group management after deletions

### Version 1.0.0
- Initial release
- CLI and GUI interfaces
- Perceptual hashing with configurable threshold
- Cross-platform support
- Dry-run mode for safety
- JSON output support

