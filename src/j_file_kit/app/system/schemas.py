"""System metadata API schemas."""

from pydantic import BaseModel, Field


class SystemInfoResponse(BaseModel):
    """Read-only runtime metadata for frontend configuration screens."""

    app_version: str = Field(..., description="Application version")
    env: str = Field(..., description="Runtime environment name")
    base_dir: str = Field(..., description="Application data directory")
    media_root: str = Field(..., description="Mounted media root")
    jav_media_root: str = Field(..., description="JAV workspace root boundary")
    raw_media_root: str = Field(..., description="Raw workspace root boundary")
    media_mounted: bool = Field(..., description="Whether media root is a mount point")


class ExtensionDefaultsResponse(BaseModel):
    """Read-only file extension defaults used by organizer pipelines."""

    video: list[str] = Field(..., description="Video file extensions")
    image: list[str] = Field(..., description="Image file extensions")
    subtitle: list[str] = Field(..., description="Subtitle file extensions")
    archive: list[str] = Field(..., description="Archive file extensions")
    music: list[str] = Field(..., description="Music file extensions")
    misc_delete: list[str] = Field(..., description="Miscellaneous delete extensions")


class RawDefaultsResponse(BaseModel):
    """Read-only Raw organizer keyword and threshold defaults."""

    junk_keywords: list[str] = Field(..., description="Raw junk filename keywords")
    video_bucket_movie_keywords: list[str] = Field(
        ...,
        description="Raw movie video bucket keywords",
    )
    video_bucket_us_vr_keywords: list[str] = Field(
        ...,
        description="Raw US VR video bucket keywords",
    )
    video_bucket_us_keywords: list[str] = Field(
        ...,
        description="Raw US video bucket keywords",
    )
    camelcase_no_split_words: list[str] = Field(
        ...,
        description="Words preserved during CamelCase keyword expansion",
    )
    cleanup_junk_max_bytes: int = Field(
        ...,
        description="Max bytes for Raw cleanup junk deletion",
    )


class JavDefaultsResponse(BaseModel):
    """Read-only JAV organizer naming defaults."""

    vr_serial_prefixes: list[str] = Field(
        ...,
        description="JAV serial prefixes treated as VR",
    )
    filename_strip_substrings: list[str] = Field(
        ...,
        description="Substrings stripped during JAV filename normalization",
    )


class FileTypeDefaultsResponse(BaseModel):
    """Read-only product defaults shown in the frontend global config tab."""

    extensions: ExtensionDefaultsResponse
    raw: RawDefaultsResponse
    jav: JavDefaultsResponse
