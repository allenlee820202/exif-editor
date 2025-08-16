# EXIF Editor

A Python-based EXIF metadata editor for JPEG images with both command-line and graphical user interfaces. Edit GPS coordinates, timezone data, and date/time information in your image metadata.

## Features

- **Batch GPS coordinate updates** - Add or modify GPS location data for multiple images
- **Timezone offset editing** - Update OffsetTimeOriginal and OffsetTimeDigitized fields
- **Date/time adjustment** - Modify image timestamps by applying time offsets
- **Dual interface** - Both CLI for batch processing and GUI for interactive editing
- **Thumbnail preview** - Visual interface with image thumbnails and EXIF data display
- **Multiple sorting options** - Sort images by name, creation time, or DateTimeOriginal

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for package management:

```bash
# Install dependencies
uv sync
```

## Usage

### Command Line Interface

Batch process all JPEG images in a directory to add GPS coordinates:

```bash
python edit-exif-cli.py <directory> <latitude> <longitude>
```

Example:
```bash
python edit-exif-cli.py ./photos 37.7749 -122.4194
```

### Graphical User Interface

Launch the PyQt5 GUI application:

```bash
python edit-exif-gui.py
```

**GUI Features:**
- Browse and select image directories
- Thumbnail view with multi-selection support
- Real-time EXIF data preview
- Batch editing of GPS coordinates
- Timezone offset updates
- Date/time adjustment by offset
- Sort images by various criteria

## Dependencies

- **piexif** - EXIF data manipulation
- **Pillow** - Image processing
- **PyQt5** - GUI framework (for GUI version)

## Technical Details

- GPS coordinates are stored in DMS (degrees, minutes, seconds) format in EXIF data
- DateTime fields use format: `YYYY:MM:DD HH:MM:SS`
- Timezone offset format: `[+-]HH:MM`
- Optimized for performance using `piexif.load()` without opening image files
- Automatically removes thumbnail data from EXIF to avoid compatibility issues

## File Structure

- `exif.py` - Core EXIF manipulation functions and utilities
- `edit-exif-cli.py` - Command-line interface for batch processing
- `edit-exif-gui.py` - PyQt5 graphical user interface