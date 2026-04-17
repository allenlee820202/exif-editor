# EXIF Editor - Complete User Instructions

## Overview
EXIF Editor is a powerful Python application for editing JPEG image metadata, including GPS coordinates, timezone information, and date/time stamps. It provides both command-line and graphical interfaces for batch processing and interactive editing.

## Table of Contents
1. [Installation & Setup](#installation--setup)
2. [Command Line Interface (CLI)](#command-line-interface-cli)
3. [Graphical User Interface (GUI)](#graphical-user-interface-gui)
4. [Feature Descriptions](#feature-descriptions)
5. [File Formats & Standards](#file-formats--standards)
6. [Troubleshooting](#troubleshooting)
7. [Advanced Usage](#advanced-usage)

---

## Installation & Setup

### Prerequisites
- Python 3.8 or higher
- macOS, Windows, or Linux

### Quick Start
1. **Clone or download** the project to your local machine
2. **Navigate** to the project directory:
   ```bash
   cd exif-editor
   ```
3. **Install dependencies** using uv (recommended):
   ```bash
   uv sync
   ```
   Or using pip:
   ```bash
   pip install piexif Pillow PyQt5
   ```

### Verify Installation
Test the installation by running:
```bash
python edit-exif-gui.py
```
This should launch the graphical interface.

---

## Command Line Interface (CLI)

### Basic GPS Coordinate Editing

**Command:**
```bash
python edit-exif-cli.py <directory> <latitude> <longitude>
```

**Parameters:**
- `directory`: Path to folder containing JPEG images
- `latitude`: Decimal degrees (-90 to 90)
- `longitude`: Decimal degrees (-180 to 180)

**Examples:**
```bash
# San Francisco coordinates
python edit-exif-cli.py ./photos 37.7749 -122.4194

# Tokyo coordinates
python edit-exif-cli.py /Users/photos 35.6762 139.6503

# Process current directory
python edit-exif-cli.py . 40.7128 -74.0060
```

**What it does:**
- Processes ALL `.jpg` and `.jpeg` files in the specified directory
- Adds GPS coordinates to EXIF data
- Preserves all other existing EXIF information
- Creates backup is NOT automatic - backup manually if needed

---

## Graphical User Interface (GUI)

### Launching the GUI
```bash
python edit-exif-gui.py
```

### Main Interface Components

#### 1. **Folder Selection**
- **Browse Button**: Select directory containing images
- **Folder Path**: Shows current selected directory
- **Auto-loads**: Thumbnails appear automatically after selection

#### 2. **Image Sorting**
- **Sort by Name**: Alphabetical filename order
- **Sort by Creation Time**: File system creation timestamp
- **Sort by DateTimeOriginal**: EXIF photo capture time (default)

#### 3. **Image Selection**
- **Single Click**: Select one image
- **Ctrl+Click**: Add/remove images from selection
- **Shift+Click**: Select range of images
- **Click empty space**: Clear selection

#### 4. **GPS Coordinate Editing**
**Input Format:** `latitude, longitude`
```
37.7749, -122.4194
```
- **Update GPS Data Button**: Apply coordinates to selected images
- **Supports**: Positive/negative decimal degrees
- **Updates**: All selected images simultaneously

#### 5. **Timezone Offset Management**
**Input Format:** `[+/-]HH:MM`
```
+08:00    (Asia/Shanghai)
-05:00    (US Eastern Standard)
-07:00    (US Pacific Standard)
```
- **Updates**: OffsetTimeOriginal and OffsetTimeDigitized EXIF fields
- **Apply to**: All selected images

#### 6. **Date/Time Adjustment**
**Local Date Time Display**: Shows DateTimeOriginal from selected image

**Local Date Time Offset**: Adjust image timestamps
```
+02:30    (Add 2 hours 30 minutes)
-01:15    (Subtract 1 hour 15 minutes)
```
- **Modifies**: DateTimeOriginal, DateTime, and DateTimeDigitized
- **Useful for**: Correcting camera clock errors

#### 7. **Image Preview & EXIF Data**
- **Sidebar**: Appears when image is selected
- **Image Preview**: Scaled version of selected photo
- **EXIF Table**: Complete metadata display
- **GPS Information**: Current coordinates if present

### Step-by-Step Workflow

#### Batch GPS Coordinate Update
1. **Launch GUI**: `python edit-exif-gui.py`
2. **Select Folder**: Browse to image directory
3. **Select Images**: Choose which photos to update
4. **Enter Coordinates**: Type `lat, lon` in GPS field
5. **Click Update**: Apply changes to selected images
6. **Verify**: Check preview panel for updated GPS data

#### Timezone Correction
1. **Select Images**: Choose photos to update
2. **Enter Timezone**: Type offset like `+09:00`
3. **Update**: Click timezone update button
4. **Confirm**: Success message appears

#### Date/Time Adjustment
1. **Select Image**: View current DateTimeOriginal
2. **Enter Offset**: Type time adjustment like `-02:00`
3. **Update**: Apply time shift to selected images

---

## Feature Descriptions

### GPS Coordinate Handling
- **Input**: Decimal degrees (WGS84 standard)
- **Storage**: Degrees, Minutes, Seconds (DMS) in EXIF
- **Automatic**: Hemisphere detection (N/S, E/W)
- **Precision**: Accurate to ~1 meter

### Timezone Support
- **Standard**: ISO 8601 format (`±HH:MM`)
- **EXIF Fields**: OffsetTimeOriginal, OffsetTimeDigitized
- **Use Cases**: Correct timezone when camera clock was wrong

### Date/Time Adjustment
- **Supports**: Hour and minute offsets
- **Negative Values**: Subtract time (fix fast clocks)
- **Positive Values**: Add time (fix slow clocks)
- **Batch Processing**: Apply same offset to multiple images

### Performance Optimizations
- **Lazy Loading**: EXIF data loaded only when needed
- **Threaded Thumbnails**: Non-blocking image loading
- **Memory Efficient**: Processes large image collections
- **Progress Indicators**: Visual feedback for long operations

---

## File Formats & Standards

### Supported Formats
- **Input**: JPEG files (.jpg, .jpeg)
- **EXIF**: Standard EXIF 2.3 specification
- **GPS**: WGS84 coordinate system

### EXIF Field Mapping
- **GPS Latitude**: `piexif.GPSIFD.GPSLatitude`
- **GPS Longitude**: `piexif.GPSIFD.GPSLongitude`
- **GPS Latitude Ref**: `piexif.GPSIFD.GPSLatitudeRef` (N/S)
- **GPS Longitude Ref**: `piexif.GPSIFD.GPSLongitudeRef` (E/W)
- **DateTimeOriginal**: `piexif.ExifIFD.DateTimeOriginal`
- **OffsetTimeOriginal**: `piexif.ExifIFD.OffsetTimeOriginal`

### Data Formats
```
DateTime: "2024:10:12 14:30:45"
Timezone: "+08:00" or "-05:30"
GPS DMS: ((37, 1), (46, 1), (2964, 100))  # 37°46'29.64"
```

---

## Troubleshooting

### Common Issues

#### "No EXIF data found"
- **Cause**: Some JPEG files lack EXIF headers
- **Solution**: Only affects old/processed images; tool will add EXIF data

#### "Permission denied"
- **Cause**: File is read-only or in use
- **Solution**: Close other applications, check file permissions

#### "Invalid coordinate format"
- **Cause**: Wrong GPS input format
- **Solution**: Use decimal degrees: `37.7749, -122.4194`

#### "Invalid timezone format"
- **Cause**: Wrong timezone offset format
- **Solution**: Use `±HH:MM` format: `+08:00` or `-05:30`

#### GUI doesn't launch
- **Cause**: PyQt5 not installed or display issues
- **Solution**: Install PyQt5: `pip install PyQt5`

### Error Messages

#### CLI Errors
```bash
Usage: python edit-exif.py <directory> <latitude> <longitude>
```
- **Fix**: Provide exactly 3 arguments

#### GUI Errors
- **"No photos selected"**: Select images before updating
- **"Invalid Input"**: Check coordinate/timezone format
- **"Error loading EXIF"**: File may be corrupted or not JPEG

### Debug Mode
Add debugging to see detailed error information:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## Advanced Usage

### Scripting with CLI
Create batch scripts for common operations:

**Windows Batch File (update_gps.bat):**
```batch
@echo off
python edit-exif-cli.py "C:\Photos\Vacation" 48.8566 2.3522
echo GPS coordinates updated for Paris location
pause
```

**Shell Script (update_gps.sh):**
```bash
#!/bin/bash
python edit-exif-cli.py "/Users/photos/trip" 35.6762 139.6503
echo "GPS coordinates updated for Tokyo location"
```

### Integration with Other Tools

#### Location History Import
The project includes `location_history.py` for importing GPS data from external sources:
```python
import location_history
coords = location_history.get_coordinates_for_datetime(datetime_string)
```

#### Bulk Operations
Process multiple directories:
```bash
for dir in photos/*/; do
    python edit-exif-cli.py "$dir" 37.7749 -122.4194
done
```

### Custom Modifications

#### Adding New EXIF Fields
Extend the `exif.py` module to handle additional metadata:
```python
def update_custom_field(exif_dict, field_value):
    exif_dict['Exif'][piexif.ExifIFD.CustomField] = field_value
    return exif_dict
```

#### Custom Sorting
Add new sorting criteria in GUI:
```python
elif sort_criteria == 'File Size':
    files.sort(key=lambda x: os.path.getsize(x))
```

### Performance Tips

#### Large Image Collections
- Process in smaller batches (< 1000 images)
- Use CLI for pure batch operations
- Close other applications to free memory

#### Network Drives
- Copy images locally before processing
- Network latency can slow thumbnail loading

#### Backup Strategy
```bash
# Create backup before processing
cp -r original_photos backup_photos
python edit-exif-cli.py original_photos 37.7749 -122.4194
```

---

## Support & Contributing

### Getting Help
1. Check this documentation
2. Review error messages carefully
3. Test with a small sample of images first
4. Verify JPEG files are not corrupted

### Contributing
- Submit bug reports with sample images (remove personal EXIF data)
- Suggest new features
- Share usage examples and workflows

### Version Information
- **Project**: EXIF Editor
- **Python**: 3.8+ required
- **Dependencies**: piexif, Pillow, PyQt5
- **License**: Check repository for license details

---

*This document covers all major functionality of the EXIF Editor. For specific technical questions, refer to the source code comments and docstrings.*