# EXIF Editor

EXIF metadata editor for JPEG images with:
- Python core logic for EXIF and location-history matching
- Legacy PyQt5 desktop GUI (kept as-is)
- New Flutter desktop GUI (dark gray + green glassy theme)

## What is New

- Added a Flutter macOS app in `flutter_app/`
- Added a Python backend API in `flutter_backend.py` that reuses existing logic from `exif.py` and `location_history.py`
- Added helper scripts:
  - `scripts/dev-flutter.sh` for one-command local startup
  - `scripts/build-flutter-macos.sh` for release build output

## Prerequisites

- Python 3.9+ (managed through `uv`)
- [uv](https://github.com/astral-sh/uv)
- Flutter SDK (stable)
- macOS desktop target enabled for Flutter

Useful checks:

```bash
flutter --version
flutter doctor -v
```

Notes:
- Android SDK is optional unless you want Android builds.
- For signed macOS/iOS distribution builds, install full Xcode (not only Command Line Tools).

## Install Project Dependencies

```bash
uv sync
flutter pub get --project-dir flutter_app
```

## Run the New Flutter App (Recommended)

One command starts both Python backend and Flutter desktop app:

```bash
./scripts/dev-flutter.sh
```

Optional environment overrides:

```bash
BACKEND_HOST=127.0.0.1 BACKEND_PORT=8765 ./scripts/dev-flutter.sh
```

## Run Flutter Web (Lightweight Dev on 8GB RAM)

Use this path when you want to avoid full Xcode for day-to-day UI work.

```bash
./scripts/dev-flutter-web.sh
```

Optional overrides:

```bash
BACKEND_HOST=127.0.0.1 BACKEND_PORT=8765 WEB_DEVICE=chrome ./scripts/dev-flutter-web.sh
```

Notes for web mode:
- Folder and location-history file selection use typed absolute paths in the UI.
- Keep backend on `127.0.0.1` and run browser on the same machine.
- Image previews are served through backend endpoint `/photos/image`.

## Build Release (macOS)

```bash
./scripts/build-flutter-macos.sh
```

Artifacts are written to:
- `dist/exif_editor_flutter.app`
- `dist/exif_editor_flutter-macos.zip`

## Build Release (Web)

```bash
./scripts/build-flutter-web.sh
```

Artifact output:
- `dist/web/`

## Legacy Interfaces (Still Available)

### CLI

```bash
uv run python edit-exif-cli.py <directory> <latitude> <longitude>
```

Example:

```bash
uv run python edit-exif-cli.py ./photos 37.7749 -122.4194
```

### PyQt5 GUI

```bash
uv run python edit-exif-gui.py
```

## Backend API (for Flutter)

Run backend alone:

```bash
uv run python flutter_backend.py --host 127.0.0.1 --port 8765
```

Main endpoints include:
- `/health`
- `/photos/list`
- `/photos/details`
- `/photos/update-gps`
- `/photos/update-timezone`
- `/photos/update-datetime-offset`
- `/location-history/preview`
- `/location-history/apply`

## Technical Notes

- GPS coordinates are stored in EXIF as DMS rationals.
- DateTime format is `YYYY:MM:DD HH:MM:SS`.
- Offset format is `[+-]HH:MM`.
- `update_image_gps_exif` uses `piexif.insert` to avoid JPEG re-encode.
- Existing PyQt GUI code remains untouched for compatibility.

## File Structure

- `exif.py` - core EXIF functions
- `location_history.py` - Google Location History matching
- `edit-exif-cli.py` - CLI batch GPS writer
- `edit-exif-gui.py` - legacy PyQt5 GUI
- `flutter_backend.py` - FastAPI bridge for Flutter
- `flutter_app/` - Flutter desktop UI
- `scripts/dev-flutter.sh` - local dev launcher (backend + Flutter)
- `scripts/build-flutter-macos.sh` - release build helper
