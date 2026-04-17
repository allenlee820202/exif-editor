import argparse
import mimetypes
import os
import re
import subprocess
import sys
from typing import Dict, List, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import uvicorn

import exif
import location_history


OFFSET_PATTERN = re.compile(r"^[+-]\d{2}:\d{2}$")
IMAGE_EXTENSIONS = (".jpg", ".jpeg")
IMAGE_PREVIEW_EXTENSIONS = (".jpg", ".jpeg", ".png")


app = FastAPI(title="EXIF Editor Backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str


class PickerPathResponse(BaseModel):
    path: str


class PhotoListRequest(BaseModel):
    folder: str = Field(min_length=1)
    sort_by: Literal["name", "creation_time", "datetime_original"] = "datetime_original"


class PhotoSummary(BaseModel):
    file_path: str
    name: str
    ctime: float
    datetime_original: str


class PhotoListResponse(BaseModel):
    photos: List[PhotoSummary]


class PhotoDetailsRequest(BaseModel):
    file_path: str = Field(min_length=1)


class PhotoDetailsResponse(BaseModel):
    file_path: str
    exif_text: str
    latitude: float
    longitude: float
    timezone_offset: str
    datetime_original: str


class UpdateGpsRequest(BaseModel):
    file_paths: List[str]
    lat: float
    lon: float


class UpdateOffsetRequest(BaseModel):
    file_paths: List[str]
    offset: str


class BatchActionResponse(BaseModel):
    updated_count: int
    failed_paths: List[str]
    errors: List[str]


class LocationPreviewRequest(BaseModel):
    location_file: str = Field(min_length=1)
    photo_files: List[str]


class LocationGps(BaseModel):
    lat: float
    lon: float
    semantic_type: str
    probability: str
    time_diff_minutes: int


class LocationMatch(BaseModel):
    file_path: str
    filename: str
    timestamp: str
    gps: LocationGps


class LocationPreviewResponse(BaseModel):
    matches: List[LocationMatch]


class LocationApplyRequest(BaseModel):
    matches: List[LocationMatch]


def _decode_maybe_bytes(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    return str(value)


def _validate_offset(offset: str) -> None:
    if not OFFSET_PATTERN.match(offset):
        raise ValueError('Invalid offset format. Expected "[+-]HH:MM".')

    hours = int(offset[1:3])
    minutes = int(offset[4:6])
    if hours > 23 or minutes > 59:
        raise ValueError('Invalid offset value. Hours must be 00-23 and minutes 00-59.')


def _list_photo_files(folder: str) -> List[str]:
    return [
        os.path.join(folder, name)
        for name in os.listdir(folder)
        if name.lower().endswith(IMAGE_EXTENSIONS)
    ]


def _collect_photo_summary(file_path: str) -> PhotoSummary:
    datetime_original = ""
    try:
        datetime_original = _decode_maybe_bytes(exif.get_datetime_original(file_path))
    except Exception:
        datetime_original = ""

    return PhotoSummary(
        file_path=file_path,
        name=os.path.basename(file_path),
        ctime=os.path.getctime(file_path),
        datetime_original=datetime_original,
    )


def _batch_apply(file_paths: List[str], updater) -> BatchActionResponse:
    updated_count = 0
    failed_paths: List[str] = []
    errors: List[str] = []

    for file_path in file_paths:
        try:
            updater(file_path)
            updated_count += 1
        except Exception as exc:
            failed_paths.append(file_path)
            errors.append(f"{file_path}: {exc}")

    return BatchActionResponse(
        updated_count=updated_count,
        failed_paths=failed_paths,
        errors=errors,
    )


def _run_osascript(script_lines: List[str]) -> str:
    if sys.platform != "darwin":
        raise HTTPException(
            status_code=501,
            detail="Native picker endpoints are currently supported on macOS only.",
        )

    command = ["osascript"]
    for line in script_lines:
        command.extend(["-e", line])

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        error_text = (result.stderr or "").strip()
        if "User canceled" in error_text:
            raise HTTPException(status_code=400, detail="Selection cancelled.")
        raise HTTPException(status_code=500, detail=f"Native picker failed: {error_text}")

    selected_path = (result.stdout or "").strip()
    if not selected_path:
        raise HTTPException(status_code=400, detail="Selection cancelled.")

    return selected_path


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/picker/folder", response_model=PickerPathResponse)
def picker_folder() -> PickerPathResponse:
    selected_path = _run_osascript(
        [
            'POSIX path of (choose folder with prompt "Select Photo Folder")',
        ]
    )
    return PickerPathResponse(path=selected_path)


@app.get("/picker/location-history-file", response_model=PickerPathResponse)
def picker_location_history_file() -> PickerPathResponse:
    selected_path = _run_osascript(
        [
            'POSIX path of (choose file with prompt "Select Location History JSON")',
        ]
    )

    if not selected_path.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Please select a .json file.")

    return PickerPathResponse(path=selected_path)


@app.get("/photos/image")
def photo_image(path: str = Query(min_length=1)) -> FileResponse:
    file_path = os.path.abspath(path)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=400, detail=f"Image file does not exist: {file_path}")

    if not file_path.lower().endswith(IMAGE_PREVIEW_EXTENSIONS):
        raise HTTPException(status_code=400, detail="Unsupported image format.")

    media_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    return FileResponse(file_path, media_type=media_type, headers={"Cache-Control": "no-store"})


@app.post("/photos/list", response_model=PhotoListResponse)
def list_photos(request: PhotoListRequest) -> PhotoListResponse:
    folder = os.path.abspath(request.folder)
    if not os.path.isdir(folder):
        raise HTTPException(status_code=400, detail=f"Folder does not exist: {folder}")

    file_paths = _list_photo_files(folder)
    photo_summaries = [_collect_photo_summary(path) for path in file_paths]

    if request.sort_by == "name":
        photo_summaries.sort(key=lambda item: item.name.lower())
    elif request.sort_by == "creation_time":
        photo_summaries.sort(key=lambda item: item.ctime)
    else:
        photo_summaries.sort(
            key=lambda item: item.datetime_original if item.datetime_original else "9999:12:31 23:59:59"
        )

    return PhotoListResponse(photos=photo_summaries)


@app.post("/photos/details", response_model=PhotoDetailsResponse)
def photo_details(request: PhotoDetailsRequest) -> PhotoDetailsResponse:
    file_path = os.path.abspath(request.file_path)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=400, detail=f"File does not exist: {file_path}")

    exif_text = "No EXIF data available"
    latitude = 0.0
    longitude = 0.0
    timezone_offset = ""
    datetime_original = ""

    try:
        exif_dict = exif.extract_exif_data(file_path)
        exif_text = exif.format_exif_data(exif_dict)
    except Exception:
        exif_text = "No EXIF data available"

    try:
        latitude, longitude = exif.extract_gps_data(file_path)
    except Exception:
        latitude, longitude = 0.0, 0.0

    try:
        timezone_offset = exif.get_offset_time_data(file_path)
    except Exception:
        timezone_offset = ""

    try:
        datetime_original = _decode_maybe_bytes(exif.get_exif_date_time_original(file_path))
    except Exception:
        datetime_original = ""

    return PhotoDetailsResponse(
        file_path=file_path,
        exif_text=exif_text,
        latitude=latitude,
        longitude=longitude,
        timezone_offset=timezone_offset,
        datetime_original=datetime_original,
    )


@app.post("/photos/update-gps", response_model=BatchActionResponse)
def update_gps(request: UpdateGpsRequest) -> BatchActionResponse:
    if not request.file_paths:
        raise HTTPException(status_code=400, detail="No files provided.")

    gps_data = {"lat": request.lat, "lon": request.lon}
    return _batch_apply(
        request.file_paths,
        lambda file_path: exif.update_image_gps_exif(file_path, gps_data),
    )


@app.post("/photos/update-timezone", response_model=BatchActionResponse)
def update_timezone(request: UpdateOffsetRequest) -> BatchActionResponse:
    if not request.file_paths:
        raise HTTPException(status_code=400, detail="No files provided.")

    try:
        _validate_offset(request.offset)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _batch_apply(
        request.file_paths,
        lambda file_path: exif.update_image_offset_time_exif(file_path, request.offset),
    )


@app.post("/photos/update-datetime-offset", response_model=BatchActionResponse)
def update_datetime_offset(request: UpdateOffsetRequest) -> BatchActionResponse:
    if not request.file_paths:
        raise HTTPException(status_code=400, detail="No files provided.")

    try:
        _validate_offset(request.offset)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _batch_apply(
        request.file_paths,
        lambda file_path: exif.update_local_date_time_by_offset(file_path, request.offset),
    )


@app.post("/location-history/preview", response_model=LocationPreviewResponse)
def preview_location_history(request: LocationPreviewRequest) -> LocationPreviewResponse:
    location_file = os.path.abspath(request.location_file)
    if not os.path.isfile(location_file):
        raise HTTPException(status_code=400, detail=f"Location file does not exist: {location_file}")

    if not request.photo_files:
        raise HTTPException(status_code=400, detail="No photo files provided.")

    matches = location_history.process_photos_with_location_history(location_file, request.photo_files)
    serialized_matches: List[LocationMatch] = []
    for item in matches:
        serialized_matches.append(
            LocationMatch(
                file_path=item["file_path"],
                filename=item["filename"],
                timestamp=item["timestamp"].isoformat(),
                gps=LocationGps(
                    lat=item["gps"]["lat"],
                    lon=item["gps"]["lon"],
                    semantic_type=item["gps"]["semantic_type"],
                    probability=str(item["gps"]["probability"]),
                    time_diff_minutes=item["gps"]["time_diff_minutes"],
                ),
            )
        )

    return LocationPreviewResponse(matches=serialized_matches)


@app.post("/location-history/apply", response_model=BatchActionResponse)
def apply_location_history(request: LocationApplyRequest) -> BatchActionResponse:
    if not request.matches:
        raise HTTPException(status_code=400, detail="No location matches provided.")

    def updater(match: LocationMatch) -> None:
        exif.update_image_gps_exif(
            match.file_path,
            {
                "lat": match.gps.lat,
                "lon": match.gps.lon,
            },
        )

    updated_count = 0
    failed_paths: List[str] = []
    errors: List[str] = []

    for match in request.matches:
        try:
            updater(match)
            updated_count += 1
        except Exception as exc:
            failed_paths.append(match.file_path)
            errors.append(f"{match.file_path}: {exc}")

    return BatchActionResponse(
        updated_count=updated_count,
        failed_paths=failed_paths,
        errors=errors,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run EXIF editor backend API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
