"""System metadata API routes."""

import os

from fastapi import APIRouter, Request

import j_file_kit.app.file_task.application.config_common as config_common
from j_file_kit.api.app_state import AppState
from j_file_kit.app.file_task.domain.jav_defaults import (
    DEFAULT_JAV_FILENAME_STRIP_SUBSTRINGS,
    DEFAULT_JAV_VR_SERIAL_PREFIXES,
)
from j_file_kit.app.file_task.domain.organizer_defaults import (
    DEFAULT_ARCHIVE_EXTENSIONS,
    DEFAULT_CAMELCASE_NO_SPLIT_WORDS,
    DEFAULT_IMAGE_EXTENSIONS,
    DEFAULT_MISC_FILE_DELETE_EXTENSIONS,
    DEFAULT_MUSIC_EXTENSIONS,
    DEFAULT_SUBTITLE_EXTENSIONS,
    DEFAULT_VIDEO_EXTENSIONS,
)
from j_file_kit.app.file_task.domain.raw_defaults import (
    DEFAULT_RAW_CLEANUP_JUNK_MAX_BYTES,
    DEFAULT_RAW_JUNK_KEYWORDS,
    DEFAULT_RAW_VIDEO_BUCKET_MOVIE_KEYWORDS,
    DEFAULT_RAW_VIDEO_BUCKET_US_KEYWORDS,
    DEFAULT_RAW_VIDEO_BUCKET_US_VR_KEYWORDS,
)
from j_file_kit.app.system.schemas import (
    ExtensionDefaultsResponse,
    FileTypeDefaultsResponse,
    JavDefaultsResponse,
    RawDefaultsResponse,
    SystemInfoResponse,
)
from j_file_kit.shared.constants import MEDIA_ROOT

router = APIRouter(prefix="/api/system", tags=["system"])


def _sorted_values(values: frozenset[str]) -> list[str]:
    return sorted(values, key=str.casefold)


@router.get("/info", response_model=SystemInfoResponse)
async def get_system_info(request: Request) -> SystemInfoResponse:
    """Return runtime metadata needed by the frontend configuration center."""
    app_state: AppState = request.app.state.app_state
    return SystemInfoResponse(
        app_version=request.app.version,
        env=os.getenv("J_FILE_KIT_ENV", "development"),
        base_dir=str(app_state.base_dir),
        media_root=str(MEDIA_ROOT),
        jav_media_root=str(config_common.JAV_MEDIA_ROOT),
        raw_media_root=str(config_common.RAW_MEDIA_ROOT),
        media_mounted=os.path.ismount(MEDIA_ROOT),
    )


@router.get("/file-type-defaults", response_model=FileTypeDefaultsResponse)
async def get_file_type_defaults() -> FileTypeDefaultsResponse:
    """Return read-only organizer defaults for frontend global configuration."""
    return FileTypeDefaultsResponse(
        extensions=ExtensionDefaultsResponse(
            video=_sorted_values(DEFAULT_VIDEO_EXTENSIONS),
            image=_sorted_values(DEFAULT_IMAGE_EXTENSIONS),
            subtitle=_sorted_values(DEFAULT_SUBTITLE_EXTENSIONS),
            archive=_sorted_values(DEFAULT_ARCHIVE_EXTENSIONS),
            music=_sorted_values(DEFAULT_MUSIC_EXTENSIONS),
            misc_delete=_sorted_values(DEFAULT_MISC_FILE_DELETE_EXTENSIONS),
        ),
        raw=RawDefaultsResponse(
            junk_keywords=list(DEFAULT_RAW_JUNK_KEYWORDS),
            video_bucket_movie_keywords=list(DEFAULT_RAW_VIDEO_BUCKET_MOVIE_KEYWORDS),
            video_bucket_us_vr_keywords=list(DEFAULT_RAW_VIDEO_BUCKET_US_VR_KEYWORDS),
            video_bucket_us_keywords=list(DEFAULT_RAW_VIDEO_BUCKET_US_KEYWORDS),
            camelcase_no_split_words=_sorted_values(DEFAULT_CAMELCASE_NO_SPLIT_WORDS),
            cleanup_junk_max_bytes=DEFAULT_RAW_CLEANUP_JUNK_MAX_BYTES,
        ),
        jav=JavDefaultsResponse(
            vr_serial_prefixes=_sorted_values(DEFAULT_JAV_VR_SERIAL_PREFIXES),
            filename_strip_substrings=list(DEFAULT_JAV_FILENAME_STRIP_SUBSTRINGS),
        ),
    )
