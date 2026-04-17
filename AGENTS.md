# AGENTS.md

Compact repo-specific notes. See also `CLAUDE.md` and `INSTRUCTIONS.md` (user-facing, verbose).

## Commands

- `uv sync` — install deps (do not `pip install`; `uv.lock` is source of truth)
- `uv run python edit-exif-cli.py <dir> <lat> <lon>` — batch-write GPS to all `.jpg/.jpeg` in `<dir>`
- `uv run python edit-exif-gui.py` — PyQt5 GUI
- `uv run python test_timeline_path.py` — ad-hoc test script (prints PASS/FAIL, no pytest, no exit code). There is no test runner configured.

No lint, formatter, typecheck, or CI config exists.

## Layout gotchas

- Script filenames use hyphens (`edit-exif-cli.py`, `edit-exif-gui.py`) so they are **not importable**. Only `exif.py` and `location_history.py` are importable modules. Put shared logic there.
- `location_history.py` imports `exif`, and the GUI imports `location_history`. The CLI only uses `exif`.
- `photos/`, `photos-backup/`, `photos-ice/`, and `location-history.json` are gitignored local data. `location-history.json` is ~30MB — do not read it whole; stream/filter.
- `test_timeline_path copy.py` is a stale duplicate of `test_timeline_path.py`; prefer the canonical one.

## EXIF conventions (enforced in `exif.py`)

- DateTime format: `YYYY:MM:DD HH:MM:SS` (colons, not dashes).
- Offset format: `[+-]HH:MM` parsed by fixed slicing (`offset[:3]`, `offset[4:]`). Must be exactly 6 chars.
- GPS stored as DMS rationals: `((deg,1),(min,1),(sec*100,100))`. Use `convert_to_dms`/`convert_from_dms`.
- `piexif.load(file_path)` is used directly on paths (fast path). Writes that must re-save pixel data use `Image.open(...).save(path, "jpeg", exif=...)` — this re-encodes the JPEG. `update_image_gps_exif` avoids re-encoding via `piexif.insert`.
- Always `exif_dict.pop('thumbnail', None)` before `piexif.dump` to avoid format errors (see `extract_exif_data`).
- GPS ref bytes compare against `b'S'`/`b'W'` (bytes, not str).

## Writing changes

- Prefer editing existing files. There is no package/module scaffold beyond the flat layout above.
- When touching photo files during testing, copy from `photos-backup/` to `photos/` first — writes are in-place and not reversible.

## Python

- `requires-python = ">=3.9"` (pyproject), `.python-version` pins a specific version. Use `uv run` to honor it.
