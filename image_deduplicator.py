#!/usr/bin/env python3
"""
Image Deduplicator - Cross-platform tool to find and manage duplicate images
Supports both command-line and GUI interfaces.

Author: AI Assistant
License: MIT
"""

import os
import sys
import argparse
import hashlib
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Tuple, Set
import json
import time

try:
    from PIL import Image
    import imagehash
except ImportError as e:
    print("Error: Required libraries not installed.")
    print("Please run: pip install Pillow imagehash")
    sys.exit(1)

# GUI imports (only imported when needed)
GUI_AVAILABLE = True
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, scrolledtext
    from tkinter.font import Font
    import threading
    import queue
    from PIL import ImageTk
    # Optional modern theming via ttkbootstrap
    try:
        import ttkbootstrap as tb
        from ttkbootstrap import Style
        TB_AVAILABLE = True
    except Exception:
        TB_AVAILABLE = False
except ImportError:
    GUI_AVAILABLE = False
    TB_AVAILABLE = False


class ImageDeduplicator:
    """Main class for image deduplication functionality."""
    
    def __init__(self, threshold: int = 5, dry_run: bool = True):
        """
        Initialize the deduplicator.
        
        Args:
            threshold: Hash difference threshold for considering images similar (0-64)
            dry_run: If True, don't actually delete files
        """
        self.threshold = threshold
        self.dry_run = dry_run
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}
        self.duplicates = []
        self.stats = {
            'total_files': 0,
            'processed_files': 0,
            'duplicate_groups': 0,
            'files_to_delete': 0,
            'space_saved': 0
        }
    
    def is_image_file(self, file_path: Path) -> bool:
        """Check if file is a supported image format."""
        return file_path.suffix.lower() in self.supported_formats
    
    def get_file_hash(self, file_path: Path) -> str:
        """Get MD5 hash of file for exact duplicates."""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except (IOError, OSError):
            return None
    
    def get_perceptual_hash(self, file_path: Path) -> str:
        """Get perceptual hash of image for similar images."""
        try:
            with Image.open(file_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                return str(imagehash.average_hash(img))
        except (IOError, OSError, Exception):
            return None
    
    def get_image_info(self, file_path: Path) -> Dict:
        """Get comprehensive image information."""
        try:
            stat = file_path.stat()
            with Image.open(file_path) as img:
                return {
                    'path': str(file_path),
                    'size': stat.st_size,
                    'width': img.width,
                    'height': img.height,
                    'format': img.format,
                    'mode': img.mode,
                    'modified': stat.st_mtime
                }
        except (IOError, OSError, Exception):
            return None
    
    def find_duplicates(self, directory: str) -> List[Dict]:
        """
        Find duplicate images in the specified directory.
        
        Args:
            directory: Path to directory to scan
            
        Returns:
            List of duplicate groups
        """
        directory_path = Path(directory)
        if not directory_path.exists() or not directory_path.is_dir():
            raise ValueError(f"Directory does not exist: {directory}")
        
        print(f"Scanning directory: {directory_path}")
        
        # Collect all image files
        image_files = []
        for file_path in directory_path.rglob('*'):
            if file_path.is_file() and self.is_image_file(file_path):
                image_files.append(file_path)
        
        self.stats['total_files'] = len(image_files)
        print(f"Found {len(image_files)} image files")
        
        if not image_files:
            return []
        
        # Group by exact hash (identical files)
        exact_duplicates = defaultdict(list)
        perceptual_groups = defaultdict(list)
        
        print("Processing images...")
        for i, file_path in enumerate(image_files):
            if i % 50 == 0:
                print(f"Processed {i}/{len(image_files)} files...")
            
            # Get file hash for exact duplicates
            file_hash = self.get_file_hash(file_path)
            if file_hash:
                exact_duplicates[file_hash].append(file_path)
            
            # Get perceptual hash for similar images
            perceptual_hash = self.get_perceptual_hash(file_path)
            if perceptual_hash:
                perceptual_groups[perceptual_hash].append(file_path)
            
            self.stats['processed_files'] += 1
        
        # Process exact duplicates
        duplicate_groups = []
        for file_hash, files in exact_duplicates.items():
            if len(files) > 1:
                group = self._create_duplicate_group(files, 'exact')
                if group:
                    duplicate_groups.append(group)
        
        # Process perceptual duplicates
        for perceptual_hash, files in perceptual_groups.items():
            if len(files) > 1:
                # Check similarity within the group
                similar_groups = self._group_similar_images(files)
                for group_files in similar_groups:
                    if len(group_files) > 1:
                        group = self._create_duplicate_group(group_files, 'similar')
                        if group:
                            duplicate_groups.append(group)
        
        self.duplicates = duplicate_groups
        self.stats['duplicate_groups'] = len(duplicate_groups)
        self.stats['files_to_delete'] = sum(len(group['files']) - 1 for group in duplicate_groups)
        
        return duplicate_groups
    
    def _group_similar_images(self, files: List[Path]) -> List[List[Path]]:
        """Group similar images based on perceptual hash difference."""
        if len(files) < 2:
            return []
        
        groups = []
        used_files = set()
        
        for i, file1 in enumerate(files):
            if file1 in used_files:
                continue
            
            current_group = [file1]
            used_files.add(file1)
            
            hash1 = self.get_perceptual_hash(file1)
            if not hash1:
                continue
            
            for j, file2 in enumerate(files[i+1:], i+1):
                if file2 in used_files:
                    continue
                
                hash2 = self.get_perceptual_hash(file2)
                if not hash2:
                    continue
                
                # Calculate hamming distance
                hamming_distance = imagehash.hex_to_hash(hash1) - imagehash.hex_to_hash(hash2)
                
                if hamming_distance <= self.threshold:
                    current_group.append(file2)
                    used_files.add(file2)
            
            if len(current_group) > 1:
                groups.append(current_group)
        
        return groups
    
    def _create_duplicate_group(self, files: List[Path], duplicate_type: str) -> Dict:
        """Create a duplicate group with metadata."""
        if len(files) < 2:
            return None
        
        # Get file information
        file_infos = []
        for file_path in files:
            info = self.get_image_info(file_path)
            if info:
                file_infos.append(info)
        
        if len(file_infos) < 2:
            return None
        
        # Sort by file size (largest first)
        file_infos.sort(key=lambda x: x['size'], reverse=True)
        
        # Calculate space that would be saved
        space_saved = sum(info['size'] for info in file_infos[1:])
        self.stats['space_saved'] += space_saved
        
        return {
            'type': duplicate_type,
            'files': file_infos,
            'keep': file_infos[0],  # Keep the largest file
            'delete': file_infos[1:],  # Delete the rest
            'space_saved': space_saved,
            'count': len(file_infos)
        }
    
    def delete_duplicates(self, selected_groups: List[int] = None) -> Dict:
        """
        Delete duplicate files.
        
        Args:
            selected_groups: List of group indices to delete (None for all)
            
        Returns:
            Dictionary with deletion results
        """
        if self.dry_run:
            return {'deleted': 0, 'errors': 0, 'message': 'Dry run mode - no files deleted'}
        
        if not selected_groups:
            selected_groups = list(range(len(self.duplicates)))
        
        deleted_count = 0
        error_count = 0
        errors = []
        
        for group_idx in selected_groups:
            if group_idx >= len(self.duplicates):
                continue
            
            group = self.duplicates[group_idx]
            for file_info in group['delete']:
                try:
                    os.remove(file_info['path'])
                    deleted_count += 1
                except (IOError, OSError) as e:
                    error_count += 1
                    errors.append(f"Error deleting {file_info['path']}: {e}")
        
        return {
            'deleted': deleted_count,
            'errors': error_count,
            'error_list': errors
        }
    
    def print_results(self):
        """Print duplicate detection results."""
        print("\n" + "="*60)
        print("DUPLICATE DETECTION RESULTS")
        print("="*60)
        
        print(f"Total files scanned: {self.stats['total_files']}")
        print(f"Files processed: {self.stats['processed_files']}")
        print(f"Duplicate groups found: {self.stats['duplicate_groups']}")
        print(f"Files that can be deleted: {self.stats['files_to_delete']}")
        print(f"Space that can be saved: {self._format_size(self.stats['space_saved'])}")
        
        if not self.duplicates:
            print("\nNo duplicates found!")
            return
        
        print(f"\nDuplicate Groups:")
        for i, group in enumerate(self.duplicates):
            print(f"\nGroup {i+1} ({group['type']} duplicates):")
            print(f"  Keep: {group['keep']['path']} ({self._format_size(group['keep']['size'])})")
            for file_info in group['delete']:
                print(f"  Delete: {file_info['path']} ({self._format_size(file_info['size'])})")
            print(f"  Space saved: {self._format_size(group['space_saved'])}")
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"


class ImageDeduplicatorGUI:
    """GUI interface for the image deduplicator."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Image Deduplicator")
        # Make geometry adaptive; start size only
        self.root.geometry("1000x700")

        # Apply modern ttkbootstrap style when available
        if 'TB_AVAILABLE' in globals() and TB_AVAILABLE:
            try:
                # Prefer the user's requested ttkbootstrap theme
                self.style = Style(theme='superhero')
                self.tb = tb
            except Exception:
                # fallback
                self.style = ttk.Style()
        else:
            self.style = ttk.Style()

        # Color palette (inspired by the provided screenshot)
        # Color palette tuned to the user's "superhero" preferences
        self.palette = {
            'bg': '#071022',          # dark navy / near-black background
            'panel': '#0f2230',       # slightly lighter panel background
            'accent': '#007bff',      # primary action (blue/purple typical)
            'muted': '#9fb6c6',       # muted text / secondary
            'text': '#e6eef6',        # light gray / off-white text
            'danger': '#e06c75',      # danger (delete) color (kept)
            'disabled': '#21313a',
            'border': '#04121a',
            # Medium/dark gray for image background areas
            'light_panel': '#0f2230'
        }

        # Apply styles for ttk widgets (works with ttkbootstrap or default ttk)
        try:
            # Frame and Label backgrounds
            self.style.configure('TFrame', background=self.palette['panel'])
            self.style.configure('TLabel', background=self.palette['panel'], foreground=self.palette['text'])
            self.style.configure('TLabelframe', background=self.palette['panel'], foreground=self.palette['text'])
            self.style.configure('TLabelframe.Label', background=self.palette['panel'], foreground=self.palette['text'])

            # Text widget / ScrolledText isn't a themed widget; set root bg for area
            self.style.configure('TCheckbutton', background=self.palette['panel'], foreground=self.palette['text'])

            # Primary / Scan button style (use ttkbootstrap semantic style if available)
            try:
                if 'tb' in globals() and TB_AVAILABLE:
                    # ttkbootstrap uses 'primary', 'info', 'success' bootstyles
                    self.scan_bootstyle = 'primary'
                    self.info_bootstyle = 'info'
                    self.success_bootstyle = 'success'
                else:
                    self.style.configure('primary.TButton', background=self.palette['accent'], foreground=self.palette['text'], borderwidth=0)
                    self.style.map('primary.TButton', background=[('active', self.palette['accent']), ('disabled', self.palette['disabled'])])

                # Danger / Delete button style
                self.style.configure('danger.TButton', background=self.palette['danger'], foreground=self.palette['text'], borderwidth=0)
                self.style.map('danger.TButton', background=[('active', self.palette['danger']), ('disabled', self.palette['disabled'])])

                # Default TButton fallback visual
                self.style.configure('TButton', background=self.palette['panel'], foreground=self.palette['text'])
            except Exception:
                pass

            # Entries and Comboboxes
            self.style.configure('TEntry', fieldbackground=self.palette['panel'], foreground=self.palette['text'])
            try:
                # Combobox styling (both the box and dropdown)
                self.style.configure('TCombobox', 
                    fieldbackground=self.palette['panel'],
                    background=self.palette['panel'],
                    foreground=self.palette['text'],
                    selectbackground=self.palette['accent'],
                    selectforeground=self.palette['text']
                )
                # Force dark colors in dropdown
                self.style.map('TCombobox',
                    fieldbackground=[('readonly', self.palette['panel'])],
                    selectbackground=[('readonly', self.palette['accent'])],
                    foreground=[('readonly', self.palette['text'])]
                )
                # Try to style the dropdown list specifically
                self.root.option_add('*TCombobox*Listbox.background', self.palette['panel'])
                self.root.option_add('*TCombobox*Listbox.foreground', self.palette['text'])
                self.root.option_add('*TCombobox*Listbox.selectBackground', self.palette['accent'])
                self.root.option_add('*TCombobox*Listbox.selectForeground', self.palette['text'])
            except Exception:
                pass

            # Notebook / Tabs
            try:
                self.style.configure('TNotebook', background=self.palette['panel'], borderwidth=0)
                self.style.configure('TNotebook.Tab', background=self.palette['panel'], foreground=self.palette['text'])
                self.style.map('TNotebook.Tab', background=[('selected', self.palette['panel'])], foreground=[('selected', self.palette['text'])])
            except Exception:
                pass

            # Progressbar
            try:
                self.style.configure('TProgressbar', troughcolor=self.palette['panel'], background=self.palette['accent'])
            except Exception:
                pass
            # Apply a subtle darker border for framed widgets
            try:
                self.style.configure('TFrame.border', background=self.palette['border'])
            except Exception:
                pass
            # Cancel button running style (light red with white text)
            try:
                self.style.configure('cancel_running.TButton', background='#ff6b6b', foreground=self.palette['text'], borderwidth=0)
                self.style.map('cancel_running.TButton', background=[('active', '#ff5252'), ('disabled', self.palette['disabled'])])
            except Exception:
                pass
        except Exception:
            # If style configuration fails, continue with default styles
            pass

        # Configure background for non-ttk elements and default fonts
        try:
            self.root.configure(bg=self.palette['bg'])
        except Exception:
            self.root.configure(bg='#000000')

        # Avoid setting global option_add fonts (can confuse Tcl with names containing spaces)

        # Variables
        self.directory_var = tk.StringVar()
        self.threshold_var = tk.IntVar(value=5)
        self.dry_run_var = tk.BooleanVar(value=True)
        # Fixed thumbnail size (width, height)
        # Increased slightly so images are more visible in visual review
        self.thumb_size = (200, 200)
        self.deduplicator = None
        self.selected_groups = set()
        
        # Threading
        self.scan_thread = None
        self.message_queue = queue.Queue()
        self.is_scanning = False
        
        self.setup_ui()
        self.setup_threading()
    
    def setup_ui(self):
        """Setup the user interface."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Image Deduplicator", 
                                font=('Segoe UI', 16, 'bold'))
        title_label.grid(row=0, column=0, pady=(0, 20))
        
        # Control panel
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        control_frame.columnconfigure(1, weight=1)
        
        # Directory selection
        ttk.Label(control_frame, text="Image Directory:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(control_frame, textvariable=self.directory_var, width=50).grid(
            row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 5), pady=5)
        ttk.Button(control_frame, text="Browse", command=self.browse_directory).grid(
            row=0, column=2, pady=5)

        # Options frame (wrap in a dark border frame to avoid bright outlines)
        options_outer = tk.Frame(control_frame, bg=self.palette.get('border'))
        options_outer.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        options_frame = ttk.LabelFrame(options_outer, text="Options", padding="10")
        options_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        options_frame.columnconfigure(1, weight=1)

        # Threshold setting
        ttk.Label(options_frame, text="Similarity Threshold:").grid(row=0, column=0, sticky=tk.W, pady=2)
        threshold_frame = ttk.Frame(options_frame)
        threshold_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)

        ttk.Scale(threshold_frame, from_=0, to=20, variable=self.threshold_var, 
                 orient=tk.HORIZONTAL, length=200).pack(side=tk.LEFT)
        ttk.Label(threshold_frame, textvariable=self.threshold_var).pack(side=tk.LEFT, padx=(10, 0))

        # Dry run checkbox
        # Use tb.Checkbutton with info bootstyle if available for cyan accents
        if 'tb' in globals() and TB_AVAILABLE:
            tb.Checkbutton(options_frame, text="Dry Run (bulk delete only)", variable=self.dry_run_var, bootstyle='info').grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
        else:
            ttk.Checkbutton(options_frame, text="Dry Run (bulk delete only)", variable=self.dry_run_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)

        # Buttons frame (stacked full-width main actions to match screenshot)
        buttons_frame = ttk.Frame(control_frame)
        buttons_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)

        # Tune primary and danger styles for bigger full-width buttons
        try:
            self.style.configure('primary.TButton', padding=(10, 8), font=('Helvetica', 11, 'bold'))
            self.style.configure('danger.TButton', padding=(10, 8), font=('Helvetica', 11, 'bold'))
        except Exception:
            pass

        # Large Scan button (full width) - use ttkbootstrap bootstyle if available
        if 'tb' in globals() and TB_AVAILABLE:
            self.scan_button = tb.Button(buttons_frame, text="Scan for Duplicates", command=self.scan_duplicates, bootstyle='primary', width=0)
        else:
            scan_style = 'primary.TButton'
            self.scan_button = ttk.Button(buttons_frame, text="Scan for Duplicates", command=self.scan_duplicates, style=scan_style)
        self.scan_button.pack(side=tk.TOP, fill=tk.X, expand=True, pady=(0, 6))

        # Disabled Download/Delete button (full width)
        delete_style = 'danger.TButton'
        if 'tb' in globals() and TB_AVAILABLE:
            self.delete_button = tb.Button(buttons_frame, text="Delete Selected", command=self.delete_selected, bootstyle='danger', state='disabled')
        else:
            self.delete_button = ttk.Button(buttons_frame, text="Delete Selected", command=self.delete_selected, state='disabled', style=delete_style)
        self.delete_button.pack(side=tk.TOP, fill=tk.X, expand=True, pady=(0, 6))

        # Small action row for cancel (aligned left)
        small_actions = ttk.Frame(buttons_frame)
        small_actions.pack(side=tk.TOP, fill=tk.X)
        # Default style should match the Delete Selected resting style
        self.cancel_default_style = delete_style
        if 'tb' in globals() and TB_AVAILABLE:
            self.cancel_button = tb.Button(small_actions, text="Cancel Scan", command=self.cancel_scan, state='disabled', bootstyle='danger')
        else:
            self.cancel_button = ttk.Button(small_actions, text="Cancel Scan", command=self.cancel_scan, state='disabled', style=self.cancel_default_style)
        self.cancel_button.pack(side=tk.LEFT)
        
        # Create notebook for tabs (wrap tabs area to remove white tab border)
        try:
            self.style.configure('TNotebook', background=self.palette['panel'], borderwidth=0)
            self.style.configure('TNotebook.Tab', background=self.palette['panel'], foreground=self.palette['text'])
        except Exception:
            pass
        notebook_outer = tk.Frame(main_frame, bg=self.palette.get('border'))
        notebook_outer.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        self.notebook = ttk.Notebook(notebook_outer)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        # Text Results Tab
        self.text_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.text_frame, text="Text Results")
        self.text_frame.columnconfigure(0, weight=1)
        self.text_frame.rowconfigure(0, weight=1)
        
        # Results text area (wrap in dark border to avoid white border from the scrolledtext)
        text_outer = tk.Frame(self.text_frame, bg=self.palette.get('border'))
        text_outer.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=0, pady=0)
        self.results_text = scrolledtext.ScrolledText(text_outer, height=15, width=80, bd=0, relief=tk.FLAT, highlightthickness=0)
        self.results_text.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        try:
            self.results_text.configure(background=self.palette['panel'], foreground=self.palette['text'], insertbackground=self.palette['text'])
        except Exception:
            pass
        
        # Visual Review Tab
        self.visual_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.visual_frame, text="Visual Review")
        self.visual_frame.columnconfigure(0, weight=1)
        self.visual_frame.rowconfigure(1, weight=1)
        
        # Visual review controls
        visual_controls = ttk.Frame(self.visual_frame)
        visual_controls.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Left side controls
        left_controls = ttk.Frame(visual_controls)
        left_controls.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Label(left_controls, text="Select duplicate groups to review:").pack(side=tk.LEFT, padx=(0, 10))
        # Group selector with dark style
        self.group_selector = ttk.Combobox(left_controls, state="readonly", width=20)
        # Force the combobox to use our dark theme
        self.group_selector.configure(style='TCombobox')
        try:
            # Explicitly set colors on the widget itself as backup
            self.group_selector.configure(
                foreground=self.palette['text'],
                selectforeground=self.palette['text'],
                selectbackground=self.palette['accent']
            )
        except Exception:
            pass
        self.group_selector.pack(side=tk.LEFT, padx=(0, 10))
        self.group_selector.bind("<<ComboboxSelected>>", self.on_group_selected)
        
        ttk.Button(left_controls, text="Refresh", command=self.refresh_visual).pack(side=tk.LEFT)
        
        # Right side controls - Visual deletion settings
        right_controls = ttk.Frame(visual_controls)
        right_controls.pack(side=tk.RIGHT)
        
        # Visual deletion controls frame
        visual_delete_frame = ttk.Frame(right_controls)
        visual_delete_frame.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Visual deletion dry-run control
        self.visual_dry_run_var = tk.BooleanVar(value=False)
        visual_dry_run_cb = ttk.Checkbutton(visual_delete_frame, text="Visual Delete Dry Run", 
                                           variable=self.visual_dry_run_var)
        visual_dry_run_cb.pack(side=tk.TOP)
        
        # Skip confirmation for visual deletions
        self.skip_visual_confirmation_var = tk.BooleanVar(value=True)
        skip_confirmation_cb = ttk.Checkbutton(visual_delete_frame, text="Skip Visual Delete Confirmation", 
                                             variable=self.skip_visual_confirmation_var)
        skip_confirmation_cb.pack(side=tk.TOP)
        
        # Visual deletion mode label
        self.visual_mode_label = ttk.Label(right_controls, text="Visual Delete: ENABLED", 
                                          foreground="green", font=('Segoe UI', 10, 'bold'))
        self.visual_mode_label.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Bind to update the label when checkbox changes
        self.visual_dry_run_var.trace('w', self.update_visual_mode_label)
        
        # Initialize the label
        self.update_visual_mode_label()

    # Visual review area (use panel bg, set grid weights for scaling)
        self.visual_review_frame = tk.Frame(self.visual_frame, bg=self.palette['panel'])
        self.visual_review_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.visual_review_frame.columnconfigure(0, weight=1)
        self.visual_review_frame.rowconfigure(0, weight=1)

        # Progress bar (use ttkbootstrap styled progress when available)
        if 'tb' in globals() and TB_AVAILABLE:
            try:
                self.progress = tb.Progressbar(main_frame, bootstyle='info', mode='determinate', maximum=100)
            except Exception:
                self.progress = ttk.Progressbar(main_frame, mode='determinate', maximum=100)
        else:
            self.progress = ttk.Progressbar(main_frame, mode='determinate', maximum=100)
        self.progress.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        # Use Consolas for status text if available
        try:
            status_font = ('Consolas', 9)
        except Exception:
            status_font = None
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.FLAT, font=status_font)
        status_bar.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=5)
        status_bar.configure(background=self.palette['panel'], foreground=self.palette['muted'])
    
    def setup_threading(self):
        """Setup threading for responsive GUI."""
        # Check for messages from worker thread
        self.root.after(100, self.check_queue)
    
    def check_queue(self):
        """Check for messages from the worker thread."""
        try:
            while True:
                message = self.message_queue.get_nowait()
                self.handle_thread_message(message)
        except queue.Empty:
            pass
        finally:
            # Schedule next check
            self.root.after(100, self.check_queue)
    
    def handle_thread_message(self, message):
        """Handle messages from the worker thread."""
        msg_type = message.get('type')
        
        if msg_type == 'progress':
            self.status_var.set(f"Processing... {message['current']}/{message['total']} files")
            self.progress['value'] = (message['current'] / message['total']) * 100
        
        elif msg_type == 'complete':
            self.is_scanning = False
            self.progress['value'] = 100
            self.status_var.set("Scan complete")
            self.scan_button.config(state='normal', text="Scan for Duplicates")
            try:
                self.cancel_button.config(state='disabled', style=getattr(self, 'cancel_default_style', 'TButton'))
            except Exception:
                self.cancel_button.config(state='disabled')
            if self.deduplicator and self.deduplicator.duplicates:
                self.delete_button.config(state='normal')
            self.display_results()
        
        elif msg_type == 'error':
            self.is_scanning = False
            self.progress['value'] = 0
            self.status_var.set("Scan failed")
            self.scan_button.config(state='normal', text="Scan for Duplicates")
            try:
                self.cancel_button.config(state='disabled', style=getattr(self, 'cancel_default_style', 'TButton'))
            except Exception:
                self.cancel_button.config(state='disabled')
            messagebox.showerror("Error", message['error'])
        
        elif msg_type == 'cancelled':
            self.is_scanning = False
            self.progress['value'] = 0
            self.status_var.set("Scan cancelled")
            self.scan_button.config(state='normal', text="Scan for Duplicates")
            try:
                self.cancel_button.config(state='disabled', style=getattr(self, 'cancel_default_style', 'TButton'))
            except Exception:
                self.cancel_button.config(state='disabled')
    
    def cancel_scan(self):
        """Cancel the current scan."""
        if self.is_scanning:
            # Signal the worker to stop by clearing the flag. The worker will
            # detect this and finish; do NOT enqueue a 'cancelled' message
            # here because that would cause the UI to revert immediately.
            self.is_scanning = False
            # Update the UI: show Cancelling and disable the cancel button
            # but keep the running (red) style so it stays visually active
            try:
                self.cancel_button.config(state='disabled', style='cancel_running.TButton')
            except Exception:
                self.cancel_button.config(state='disabled')
            self.status_var.set("Cancelling...")
    
    def browse_directory(self):
        """Open directory browser dialog."""
        directory = filedialog.askdirectory(title="Select Image Directory")
        if directory:
            self.directory_var.set(directory)
    
    def scan_duplicates(self):
        """Scan for duplicate images."""
        if self.is_scanning:
            return
        
        directory = self.directory_var.get().strip()
        if not directory:
            messagebox.showerror("Error", "Please select a directory to scan.")
            return
        
        if not os.path.exists(directory):
            messagebox.showerror("Error", "Selected directory does not exist.")
            return
        
        # Update UI for scanning
        self.is_scanning = True
        self.scan_button.config(state='disabled', text="Scanning...")
        # Enable and style the cancel button for running state
        try:
            self.cancel_button.config(state='normal', style='cancel_running.TButton')
        except Exception:
            self.cancel_button.config(state='normal')
        self.delete_button.config(state='disabled')
        self.progress.config(mode='determinate', value=0)
        self.status_var.set("Starting scan...")
        self.results_text.delete(1.0, tk.END)
        
        # Start scan in separate thread
        self.scan_thread = threading.Thread(
            target=self._scan_worker,
            args=(directory,),
            daemon=True
        )
        self.scan_thread.start()
    
    def _scan_worker(self, directory):
        """Worker thread for scanning duplicates."""
        try:
            # Create deduplicator
            self.deduplicator = ImageDeduplicator(
                threshold=self.threshold_var.get(),
                dry_run=self.dry_run_var.get()
            )
            
            # Custom find_duplicates with progress updates
            duplicates = self._find_duplicates_with_progress(directory)
            
            # Send completion message
            self.message_queue.put({'type': 'complete', 'duplicates': duplicates})
            
        except Exception as e:
            self.message_queue.put({'type': 'error', 'error': str(e)})
    
    def _find_duplicates_with_progress(self, directory):
        """Find duplicates with progress updates."""
        directory_path = Path(directory)
        if not directory_path.exists() or not directory_path.is_dir():
            raise ValueError(f"Directory does not exist: {directory}")
        
        # Collect all image files
        image_files = []
        for file_path in directory_path.rglob('*'):
            if file_path.is_file() and self.deduplicator.is_image_file(file_path):
                image_files.append(file_path)
        
        self.deduplicator.stats['total_files'] = len(image_files)
        
        if not image_files:
            return []
        
        # Group by exact hash (identical files)
        exact_duplicates = defaultdict(list)
        perceptual_groups = defaultdict(list)
        
        for i, file_path in enumerate(image_files):
            if not self.is_scanning:  # Check for cancellation
                return []
            
            # Update progress
            self.message_queue.put({
                'type': 'progress',
                'current': i,
                'total': len(image_files)
            })
            
            # Get file hash for exact duplicates
            file_hash = self.deduplicator.get_file_hash(file_path)
            if file_hash:
                exact_duplicates[file_hash].append(file_path)
            
            # Get perceptual hash for similar images
            perceptual_hash = self.deduplicator.get_perceptual_hash(file_path)
            if perceptual_hash:
                perceptual_groups[perceptual_hash].append(file_path)
            
            self.deduplicator.stats['processed_files'] += 1
        
        # Process exact duplicates
        duplicate_groups = []
        for file_hash, files in exact_duplicates.items():
            if len(files) > 1:
                group = self.deduplicator._create_duplicate_group(files, 'exact')
                if group:
                    duplicate_groups.append(group)
        
        # Process perceptual duplicates
        for perceptual_hash, files in perceptual_groups.items():
            if len(files) > 1:
                # Check similarity within the group
                similar_groups = self.deduplicator._group_similar_images(files)
                for group_files in similar_groups:
                    if len(group_files) > 1:
                        group = self.deduplicator._create_duplicate_group(group_files, 'similar')
                        if group:
                            duplicate_groups.append(group)
        
        self.deduplicator.duplicates = duplicate_groups
        self.deduplicator.stats['duplicate_groups'] = len(duplicate_groups)
        self.deduplicator.stats['files_to_delete'] = sum(len(group['files']) - 1 for group in duplicate_groups)
        
        return duplicate_groups
    
    def display_results(self):
        """Display scan results in the text area."""
        if not self.deduplicator:
            return
        
        stats = self.deduplicator.stats
        results = f"Scan Results:\n"
        results += f"{'='*50}\n"
        results += f"Total files scanned: {stats['total_files']}\n"
        results += f"Files processed: {stats['processed_files']}\n"
        results += f"Duplicate groups found: {stats['duplicate_groups']}\n"
        results += f"Files that can be deleted: {stats['files_to_delete']}\n"
        results += f"Space that can be saved: {self.deduplicator._format_size(stats['space_saved'])}\n\n"
        
        if not self.deduplicator.duplicates:
            results += "No duplicates found!\n"
        else:
            results += "Duplicate Groups:\n"
            results += f"{'='*50}\n"
            
            for i, group in enumerate(self.deduplicator.duplicates):
                results += f"\nGroup {i+1} ({group['type']} duplicates):\n"
                results += f"  Keep: {group['keep']['path']} ({self.deduplicator._format_size(group['keep']['size'])})\n"
                for file_info in group['delete']:
                    results += f"  Delete: {file_info['path']} ({self.deduplicator._format_size(file_info['size'])})\n"
                results += f"  Space saved: {self.deduplicator._format_size(group['space_saved'])}\n"
        
        self.results_text.insert(tk.END, results)
        
        # Refresh visual interface
        self.refresh_visual()
    
    def refresh_visual(self):
        """Refresh the visual review interface."""
        if not self.deduplicator or not self.deduplicator.duplicates:
            return
        
        # Clear existing visual content
        for widget in self.visual_review_frame.winfo_children():
            widget.destroy()
        
        # Update group selector
        group_options = [f"Group {i+1} ({group['type']} - {len(group['files'])} images)" 
                        for i, group in enumerate(self.deduplicator.duplicates)]
        self.group_selector['values'] = group_options
        
        if group_options:
            self.group_selector.set(group_options[0])
            self.on_group_selected(None)
    
    def on_group_selected(self, event):
        """Handle group selection in visual review."""
        if not self.deduplicator or not self.deduplicator.duplicates:
            return
        
        selection = self.group_selector.get()
        if not selection:
            return
        
        # Extract group index from selection
        try:
            group_index = int(selection.split()[1]) - 1
            if 0 <= group_index < len(self.deduplicator.duplicates):
                self.display_group_images(group_index)
        except (ValueError, IndexError):
            pass
    
    def display_group_images(self, group_index):
        """Display images for a specific duplicate group."""
        if not self.deduplicator or group_index >= len(self.deduplicator.duplicates):
            return
        
        # Clear existing content
        for widget in self.visual_review_frame.winfo_children():
            widget.destroy()
        
        group = self.deduplicator.duplicates[group_index]

        # Create scrollable frame for images with medium/dark gray background
        canvas = tk.Canvas(self.visual_review_frame, bg=self.palette['light_panel'], highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(self.visual_review_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.palette['light_panel'])

        # Responsive scaling
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.visual_review_frame.columnconfigure(0, weight=1)
        self.visual_review_frame.rowconfigure(0, weight=1)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Configure the group header style first
        self.style.configure('GroupHeader.TLabelframe',
               background=self.palette['light_panel'])  # Medium/dark gray
        self.style.configure('GroupHeader.TLabelframe.Label',
               background=self.palette['light_panel'],  # Medium/dark gray
               foreground='#e0e0e0',  # Light gray text
               font=('TkDefaultFont', 10, 'bold'))

        # Group info with light grey background and dark text
        info_frame = ttk.LabelFrame(scrollable_frame, 
                                  text=f"Group {group_index + 1} - {group['type']} duplicates",
                                  style='GroupHeader.TLabelframe')
        info_frame.grid(row=0, column=0, sticky="ew", padx=6, pady=4)
        
        # Configure weight for the info frame column
        scrollable_frame.columnconfigure(0, weight=1)
        
        # Style the frame and its label for light background
        self.style.configure('GroupHeader.TLabelframe', background=self.palette['light_panel'])
        self.style.configure('GroupHeader.TLabelframe.Label',
               background=self.palette['light_panel'],
               foreground='#e0e0e0',
               font=('TkDefaultFont', 10, 'bold'))

        # Info text with explicit styling
        info_label = ttk.Label(info_frame, 
                            text=f"Files: {len(group['files'])} | Space saved: {self.deduplicator._format_size(group['space_saved'])}",
                            style='GroupHeader.TLabel')
        info_label.grid(row=0, column=0, pady=4, sticky="ew")
        info_frame.columnconfigure(0, weight=1)

        # Image display frame with medium/dark gray background
        images_frame = tk.Frame(scrollable_frame, bg=self.palette['light_panel'])
        images_frame.grid(row=1, column=0, sticky="nsew", padx=6, pady=4)
        scrollable_frame.rowconfigure(1, weight=1)
        scrollable_frame.columnconfigure(0, weight=1)

        # Grid for responsive image layout
        num_columns = 3  # Number of images per row
        current_row = 0
        current_col = 0

        # Create image selection variables
        self.image_vars = {}
        self.image_thumbnails = {}
        self.image_labels = {}

        # Display each image in the group
        for i, file_info in enumerate(group['files']):
            current_row = i // num_columns
            current_col = i % num_columns
            images_frame.columnconfigure(current_col, weight=1)
            # Create and grid the image widget
            self.create_image_widget(images_frame, file_info, i, group_index, row=current_row, col=current_col)

        # Configure row weights for vertical scaling
        for row in range(current_row + 1):
            images_frame.rowconfigure(row, weight=1)
    
    def create_image_widget(self, parent, file_info, index, group_index, row=0, col=0):
        """Create a widget for displaying and selecting an image."""
        # Create frame for this image with light background
        img_frame = ttk.LabelFrame(parent, text=f"Image {index + 1}", style='Card.TLabelframe')
        img_frame.grid(row=row, column=col, padx=5, pady=5, sticky='nsew')
        parent.rowconfigure(row, weight=1)
        parent.columnconfigure(col, weight=1)

        # Image selection variable
        var_name = f"group_{group_index}_img_{index}"
        self.image_vars[var_name] = tk.BooleanVar()

        # Checkbox for selection
        # Create inner frame for content
        content_frame = ttk.Frame(img_frame)
        content_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        img_frame.columnconfigure(0, weight=1)
        img_frame.rowconfigure(0, weight=1)
        
        checkbox = ttk.Checkbutton(content_frame, text="Keep this image",
                                 style='ImageCard.TCheckbutton',
                                 variable=self.image_vars[var_name])
        checkbox.grid(row=0, column=0, pady=(5,2), sticky="w")
        content_frame.columnconfigure(0, weight=1)

        # Set default selection (keep largest file)
        if index == 0:
            self.image_vars[var_name].set(True)

        # Image frame for thumbnail (fixed size to avoid pushing buttons out)
        image_frame = ttk.Frame(content_frame)
        # Use fixed width/height based on self.thumb_size and prevent propagation
        fw, fh = self.thumb_size
        image_frame.configure(width=fw, height=fh)
        image_frame.grid_propagate(False)
        image_frame.grid(row=1, column=0, sticky="nsew")
        # Keep the image area from expanding and pushing buttons out
        content_frame.rowconfigure(1, weight=0)

        def update_thumbnail(event=None):
            try:
                with Image.open(file_info['path']) as img:
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    # Always use the fixed thumbnail size for consistency
                    target_size = self.thumb_size
                    img.thumbnail(target_size, Image.Resampling.LANCZOS)

                    # Paste thumbnail onto a background to ensure consistent cell size
                    thumb = Image.new('RGB', target_size, self.palette.get('light_panel', '#0f2230'))
                    x = (target_size[0] - img.width) // 2
                    y = (target_size[1] - img.height) // 2
                    thumb.paste(img, (x, y))

                    photo = ImageTk.PhotoImage(thumb)
                    self.image_thumbnails[var_name] = photo
                    if var_name in self.image_labels:
                        self.image_labels[var_name].configure(image=photo, text="")
                        self.image_labels[var_name].image = photo
                    else:
                        img_label = ttk.Label(image_frame, image=photo, style='ImageCard.TLabel')
                        img_label.grid(row=0, column=0, pady=5, sticky="n")
                        img_label.image = photo
                        image_frame.columnconfigure(0, weight=1)
                        image_frame.rowconfigure(0, weight=1)
                        self.image_labels[var_name] = img_label
            except Exception as e:
                if var_name in self.image_labels:
                    self.image_labels[var_name].configure(text=f"Error loading image:\n{str(e)[:50]}...", image="")
                else:
                    img_label = ttk.Label(image_frame, text=f"Error loading image:\n{str(e)[:50]}...", style='ImageCard.TLabel')
                    img_label.grid(row=0, column=0, pady=5, sticky="nsew")
                    image_frame.columnconfigure(0, weight=1)
                    image_frame.rowconfigure(0, weight=1)
                    self.image_labels[var_name] = img_label

        # Bind to the frame configure only to refresh thumbnails if needed,
        # but sizing is fixed so thumbnails will remain consistent.
        img_frame.bind('<Configure>', update_thumbnail)
        update_thumbnail()
        
        # File info (simplified for better layout)
        info_text = f"File: {Path(file_info['path']).name}\n"
        info_text += f"Size: {self.deduplicator._format_size(file_info['size'])}"
        
        # Wrap long filenames so they don't expand the cell width
        try:
            info_font = ('Segoe UI', 9)
        except Exception:
            info_font = None
        wrap_px = self.thumb_size[0]
        info_label = ttk.Label(content_frame, text=info_text,
                              justify=tk.LEFT, style='ImageCard.TLabel', wraplength=wrap_px, font=info_font)
        info_label.grid(row=2, column=0, pady=(2,5), sticky="w")
        
        # Add action buttons in a grid layout
        button_frame = ttk.Frame(content_frame)
        button_frame.grid(row=3, column=0, pady=(0,5), sticky="ew")
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        
        # Comparison button
        compare_btn = ttk.Button(button_frame, text="Compare", 
                               command=lambda: self.show_comparison(group_index, index),
                               style='primary.TButton')
        compare_btn.grid(row=0, column=0, padx=5, sticky="ew")
        
        # Individual delete button
        delete_btn = ttk.Button(button_frame, text="Delete This Image", 
                              command=lambda: self.delete_single_image(file_info['path'], group_index, index),
                              style="danger.TButton")
        delete_btn.grid(row=0, column=1, padx=5, sticky="ew")
        
        # Style for better visibility on light background
        try:
            self.style.configure('ImageCard.TLabel', background=self.palette['light_panel'], foreground=self.palette['text'])
            self.style.configure('ImageCard.TCheckbutton', background=self.palette['light_panel'], foreground=self.palette['text'])
            self.style.configure('Card.TLabelframe', background=self.palette['light_panel'])
            self.style.configure('Card.TLabelframe.Label', background=self.palette['light_panel'], foreground=self.palette['text'])
        except Exception:
            pass
    
    def delete_selected(self):
        """Delete selected duplicate files."""
        if not self.deduplicator or not self.deduplicator.duplicates:
            messagebox.showwarning("Warning", "No duplicates to delete.")
            return
        
        if self.dry_run_var.get():
            messagebox.showinfo("Info", "Dry run mode is enabled. No files will be deleted.")
            return
        
        # Check if we have visual selections
        if hasattr(self, 'image_vars') and self.image_vars:
            # Use visual selections
            files_to_delete = self.get_visual_selections()
            if not files_to_delete:
                messagebox.showinfo("Info", "No files selected for deletion.")
                return
            
            # Confirm deletion
            result = messagebox.askyesno("Confirm Deletion", 
                                       f"Are you sure you want to delete {len(files_to_delete)} selected files?\n"
                                       f"This action cannot be undone!")
            
            if result:
                try:
                    deletion_result = self.delete_visual_selections(files_to_delete)
                    messagebox.showinfo("Deletion Complete", 
                                      f"Deleted {deletion_result['deleted']} files.\n"
                                      f"Errors: {deletion_result['errors']}")
                    
                    # Refresh results
                    self.display_results()
                    
                except Exception as e:
                    messagebox.showerror("Error", f"An error occurred during deletion: {str(e)}")
        else:
            # Use default deletion (all duplicates)
            result = messagebox.askyesno("Confirm Deletion", 
                                       f"Are you sure you want to delete {self.deduplicator.stats['files_to_delete']} duplicate files?\n"
                                       f"This action cannot be undone!")
            
            if result:
                try:
                    deletion_result = self.deduplicator.delete_duplicates()
                    messagebox.showinfo("Deletion Complete", 
                                      f"Deleted {deletion_result['deleted']} files.\n"
                                      f"Errors: {deletion_result['errors']}")
                    
                    # Refresh results
                    self.display_results()
                    
                except Exception as e:
                    messagebox.showerror("Error", f"An error occurred during deletion: {str(e)}")
    
    def get_visual_selections(self):
        """Get list of files to delete based on visual selections."""
        files_to_delete = []
        
        if not hasattr(self, 'image_vars') or not self.image_vars:
            return files_to_delete
        
        for group_index, group in enumerate(self.deduplicator.duplicates):
            for file_index, file_info in enumerate(group['files']):
                var_name = f"group_{group_index}_img_{file_index}"
                if var_name in self.image_vars:
                    # If checkbox is unchecked, mark for deletion
                    if not self.image_vars[var_name].get():
                        files_to_delete.append(file_info['path'])
        
        return files_to_delete
    
    def delete_visual_selections(self, files_to_delete):
        """Delete files based on visual selections."""
        deleted_count = 0
        error_count = 0
        errors = []
        
        for file_path in files_to_delete:
            try:
                os.remove(file_path)
                deleted_count += 1
            except (IOError, OSError) as e:
                error_count += 1
                errors.append(f"Error deleting {file_path}: {e}")
        
        return {
            'deleted': deleted_count,
            'errors': error_count,
            'error_list': errors
        }
    
    def show_comparison(self, group_index, selected_index):
        """Show side-by-side comparison of images in a group."""
        if not self.deduplicator or group_index >= len(self.deduplicator.duplicates):
            return
        
        group = self.deduplicator.duplicates[group_index]
        
        # Create comparison window
        comparison_window = tk.Toplevel(self.root)
        comparison_window.title(f"Image Comparison - Group {group_index + 1}")
        comparison_window.geometry("1200x800")
        
        # Create main frame
        main_frame = ttk.Frame(comparison_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text=f"Comparing {len(group['files'])} images", 
                                font=('Segoe UI', 14, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # Create scrollable frame for images
        canvas = tk.Canvas(main_frame, bg=self.palette.get('panel'))
        scrollbar = ttk.Scrollbar(main_frame, orient="horizontal", command=canvas.xview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(xscrollcommand=scrollbar.set)
        
        # Display images side by side
        for i, file_info in enumerate(group['files']):
            self.create_comparison_widget(scrollable_frame, file_info, i, group_index, selected_index)
        
        # Pack canvas and scrollbar
        canvas.pack(side="top", fill="both", expand=True)
        scrollbar.pack(side="bottom", fill="x")
        
        # Close button
        ttk.Button(main_frame, text="Close", command=comparison_window.destroy).pack(pady=10)
    
    def create_comparison_widget(self, parent, file_info, index, group_index, selected_index):
        """Create a comparison widget for an image."""
        # Create frame for this image. Use a colored outer border (palette['border'])
        # and an inner panel frame for the image to avoid bright/white borders.
        outer = tk.Frame(parent, bg=self.palette.get('border', '#1f2a2d'))
        outer.pack(side=tk.LEFT, padx=6, pady=4, fill=tk.BOTH, expand=True)

        img_frame = ttk.LabelFrame(outer, text=f"Image {index + 1}")
        img_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # Highlight selected image by increasing the outer border thickness
        if index == selected_index:
            outer.config(bg=self.palette.get('border', '#1f2a2d'))
            outer.pack_configure(padx=6, pady=4)
        
        # Image thumbnail (larger for comparison)
        try:
            with Image.open(file_info['path']) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize to comparison size
                img.thumbnail((300, 300), Image.Resampling.LANCZOS)
                
                # Convert to PhotoImage
                photo = ImageTk.PhotoImage(img)
                
                # Display image
                img_label = ttk.Label(img_frame, image=photo)
                img_label.image = photo  # Keep reference
                img_label.pack(pady=5)
                
        except Exception as e:
            error_label = ttk.Label(img_frame, text=f"Error loading image:\n{str(e)[:50]}...")
            error_label.pack(pady=5)
        
        # File info
        info_text = f"File: {Path(file_info['path']).name}\n"
        info_text += f"Size: {self.deduplicator._format_size(file_info['size'])}\n"
        info_text += f"Dimensions: {file_info['width']}x{file_info['height']}\n"
        info_text += f"Format: {file_info['format']}"
        
        if index == selected_index:
            info_text += "\n\n[SELECTED]"
        
        info_label = ttk.Label(img_frame, text=info_text, justify=tk.LEFT)
        info_label.pack(pady=5)
    
    def delete_single_image(self, file_path, group_index, image_index):
        """Delete a single image with optional confirmation."""
        if self.visual_dry_run_var.get():
            messagebox.showinfo("Info", "Visual delete dry run mode is enabled. No files will be deleted.")
            return
        
        # Get file name for display
        file_name = Path(file_path).name
        
        # Check if we should skip confirmation
        if self.skip_visual_confirmation_var.get():
            # Skip confirmation dialog - delete directly
            try:
                # Delete the file
                os.remove(file_path)
                
                # Show brief success message
                self.status_var.set(f"Deleted: {file_name}")
                
                # Refresh the visual interface to remove the deleted image
                self.refresh_visual()
                
                # Update the deduplicator data to reflect the deletion
                self.update_after_deletion(group_index, image_index)
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete {file_name}:\n{str(e)}")
        else:
            # Show confirmation dialog
            result = messagebox.askyesno("Confirm Deletion", 
                                       f"Are you sure you want to delete this image?\n\n"
                                       f"File: {file_name}\n"
                                       f"Path: {file_path}\n\n"
                                       f"This action cannot be undone!")
            
            if result:
                try:
                    # Delete the file
                    os.remove(file_path)
                    
                    # Show success message
                    messagebox.showinfo("Deletion Complete", 
                                      f"Successfully deleted: {file_name}")
                    
                    # Refresh the visual interface to remove the deleted image
                    self.refresh_visual()
                    
                    # Update the deduplicator data to reflect the deletion
                    self.update_after_deletion(group_index, image_index)
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete {file_name}:\n{str(e)}")
    
    def update_after_deletion(self, group_index, deleted_image_index):
        """Update the deduplicator data after a single image deletion."""
        if not self.deduplicator or group_index >= len(self.deduplicator.duplicates):
            return
        
        group = self.deduplicator.duplicates[group_index]
        
        # Remove the deleted image from the group
        if deleted_image_index < len(group['files']):
            deleted_file = group['files'].pop(deleted_image_index)
            
            # Update statistics
            self.deduplicator.stats['files_to_delete'] -= 1
            self.deduplicator.stats['space_saved'] -= deleted_file['size']
            
            # If only one image left, remove the entire group
            if len(group['files']) <= 1:
                self.deduplicator.duplicates.pop(group_index)
                self.deduplicator.stats['duplicate_groups'] -= 1
                if len(group['files']) == 1:
                    self.deduplicator.stats['files_to_delete'] -= 1
                    self.deduplicator.stats['space_saved'] -= group['files'][0]['size']
            else:
                # Recalculate which file to keep (largest remaining)
                group['files'].sort(key=lambda x: x['size'], reverse=True)
                group['keep'] = group['files'][0]
                group['delete'] = group['files'][1:]
                group['space_saved'] = sum(f['size'] for f in group['delete'])
                group['count'] = len(group['files'])
        
        # Refresh the text results as well
        self.results_text.delete(1.0, tk.END)
        self.display_results()
    
    def update_visual_mode_label(self, *args):
        """Update the visual deletion mode label."""
        if self.visual_dry_run_var.get():
            self.visual_mode_label.config(text="Visual Delete: DRY RUN", foreground="orange")
        else:
            self.visual_mode_label.config(text="Visual Delete: ENABLED", foreground="green")
    
    def run(self):
        """Start the GUI application."""
        self.root.mainloop()


def main():
    """Main function to handle CLI and GUI modes."""
    parser = argparse.ArgumentParser(
        description="Image Deduplicator - Find and manage duplicate images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python image_deduplicator.py /path/to/images
  python image_deduplicator.py --gui
  python image_deduplicator.py --threshold 3 --no-dry-run /path/to/images
        """
    )
    
    parser.add_argument('directory', nargs='?', help='Directory to scan for duplicate images')
    parser.add_argument('--gui', action='store_true', help='Launch GUI interface')
    parser.add_argument('--threshold', type=int, default=5, 
                       help='Similarity threshold (0-20, default: 5)')
    parser.add_argument('--no-dry-run', action='store_true', 
                       help='Actually delete files (default is dry run)')
    parser.add_argument('--output', help='Save results to JSON file')
    
    args = parser.parse_args()
    
    # GUI mode
    if args.gui or not args.directory:
        if not GUI_AVAILABLE:
            print("Error: GUI not available. Tkinter is not installed.")
            print("Please install tkinter or use command-line mode.")
            sys.exit(1)
        
        app = ImageDeduplicatorGUI()
        app.run()
        return
    
    # CLI mode
    if not args.directory:
        parser.print_help()
        return
    
    try:
        # Create deduplicator
        deduplicator = ImageDeduplicator(
            threshold=args.threshold,
            dry_run=not args.no_dry_run
        )
        
        # Scan for duplicates
        print("Starting duplicate detection...")
        duplicates = deduplicator.find_duplicates(args.directory)
        
        # Print results
        deduplicator.print_results()
        
        # Save to JSON if requested
        if args.output:
            output_data = {
                'stats': deduplicator.stats,
                'duplicates': duplicates,
                'settings': {
                    'threshold': args.threshold,
                    'dry_run': not args.no_dry_run,
                    'directory': args.directory
                }
            }
            
            with open(args.output, 'w') as f:
                json.dump(output_data, f, indent=2)
            print(f"\nResults saved to: {args.output}")
        
        # Ask for deletion if not dry run
        if not args.no_dry_run and duplicates:
            print(f"\nThis was a dry run. To actually delete files, run with --no-dry-run")
        elif args.no_dry_run and duplicates:
            response = input(f"\nDelete {deduplicator.stats['files_to_delete']} duplicate files? (y/N): ")
            if response.lower() in ['y', 'yes']:
                result = deduplicator.delete_duplicates()
                print(f"Deleted {result['deleted']} files.")
                if result['errors'] > 0:
                    print(f"Errors: {result['errors']}")
                    for error in result['error_list']:
                        print(f"  {error}")
            else:
                print("Deletion cancelled.")
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

