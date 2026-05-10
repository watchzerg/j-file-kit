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
