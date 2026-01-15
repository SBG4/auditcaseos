"""Nextcloud router for file collaboration endpoints."""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi import status as http_status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.auth import get_current_user_required, CurrentUser
from app.services.nextcloud_service import nextcloud_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/nextcloud", tags=["nextcloud"])


# =============================================================================
# Schemas
# =============================================================================


class NextcloudHealthResponse(BaseModel):
    """Nextcloud health check response."""

    available: bool
    installed: bool | None = None
    version: str | None = None
    maintenance: bool | None = None
    error: str | None = None


class FolderCreateRequest(BaseModel):
    """Request to create a folder."""

    path: str = Field(..., description="Folder path to create")


class CaseFolderResponse(BaseModel):
    """Response for case folder creation."""

    case_id: str
    folders_created: list[str]
    success: bool
    folder_url: str | None = None


class FileItem(BaseModel):
    """File or folder item."""

    name: str
    path: str
    is_directory: bool
    content_type: str | None = None
    size: int = 0
    last_modified: str | None = None
    file_id: str | None = None


class FolderListResponse(BaseModel):
    """Response for folder listing."""

    path: str
    items: list[FileItem]
    count: int


class ShareLinkResponse(BaseModel):
    """Response for share link creation."""

    id: str | None
    url: str | None
    path: str


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str
    success: bool = True


# =============================================================================
# Dependencies
# =============================================================================


DbSession = Annotated[AsyncSession, Depends(get_db)]


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/health",
    response_model=NextcloudHealthResponse,
    summary="Check Nextcloud health",
    description="Check if Nextcloud is available and get version info.",
)
async def health_check() -> NextcloudHealthResponse:
    """Check Nextcloud connection status."""
    result = await nextcloud_service.health_check()
    return NextcloudHealthResponse(**result)


@router.post(
    "/folders",
    response_model=MessageResponse,
    summary="Create a folder",
    description="Create a folder in Nextcloud.",
)
async def create_folder(
    request: FolderCreateRequest,
    current_user: CurrentUser,
) -> MessageResponse:
    """Create a folder in Nextcloud."""
    success = await nextcloud_service.create_folder(request.path)
    if success:
        return MessageResponse(message=f"Folder '{request.path}' created successfully")
    raise HTTPException(
        status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to create folder '{request.path}'",
    )


@router.post(
    "/case/{case_id}/folder",
    response_model=CaseFolderResponse,
    summary="Create case folder structure",
    description="Create the folder structure for a case (Evidence, Reports, Notes).",
)
async def create_case_folder(
    case_id: str,
    current_user: CurrentUser,
) -> CaseFolderResponse:
    """Create folder structure for a case."""
    result = await nextcloud_service.create_case_folder(case_id)
    folder_url = await nextcloud_service.get_case_folder_url(case_id)
    return CaseFolderResponse(
        case_id=result["case_id"],
        folders_created=result["folders_created"],
        success=result["success"],
        folder_url=folder_url if result["success"] else None,
    )


@router.get(
    "/folders",
    response_model=FolderListResponse,
    summary="List folder contents",
    description="List files and folders in a Nextcloud directory.",
)
async def list_folder(
    path: str = Query("", description="Folder path to list"),
    current_user: CurrentUser = None,
) -> FolderListResponse:
    """List contents of a Nextcloud folder."""
    items = await nextcloud_service.list_folder(path)
    return FolderListResponse(
        path=path,
        items=[FileItem(**item) for item in items],
        count=len(items),
    )


@router.get(
    "/case/{case_id}/files",
    response_model=FolderListResponse,
    summary="List case files",
    description="List all files in a case folder.",
)
async def list_case_files(
    case_id: str,
    subfolder: str = Query("", description="Subfolder (Evidence, Reports, Notes)"),
    current_user: CurrentUser = None,
) -> FolderListResponse:
    """List files in a case folder."""
    path = f"AuditCases/{case_id}"
    if subfolder:
        path = f"{path}/{subfolder}"

    items = await nextcloud_service.list_folder(path)
    return FolderListResponse(
        path=path,
        items=[FileItem(**item) for item in items],
        count=len(items),
    )


@router.post(
    "/case/{case_id}/upload",
    response_model=MessageResponse,
    summary="Upload file to case folder",
    description="Upload a file to a case's folder in Nextcloud.",
)
async def upload_to_case(
    case_id: str,
    file: UploadFile = File(...),
    subfolder: str = Query("Evidence", description="Subfolder (Evidence, Reports, Notes)"),
    current_user: CurrentUser = None,
) -> MessageResponse:
    """Upload a file to a case folder."""
    # Ensure case folder exists
    await nextcloud_service.create_case_folder(case_id)

    # Read file content
    content = await file.read()
    content_type = file.content_type or "application/octet-stream"

    # Upload to Nextcloud
    path = f"AuditCases/{case_id}/{subfolder}/{file.filename}"
    success = await nextcloud_service.upload_file(path, content, content_type)

    if success:
        return MessageResponse(message=f"File '{file.filename}' uploaded to {subfolder}")
    raise HTTPException(
        status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to upload file '{file.filename}'",
    )


@router.delete(
    "/files",
    response_model=MessageResponse,
    summary="Delete a file or folder",
    description="Delete a file or folder from Nextcloud.",
)
async def delete_item(
    path: str = Query(..., description="Path to delete"),
    current_user: CurrentUser = None,
) -> MessageResponse:
    """Delete a file or folder from Nextcloud."""
    success = await nextcloud_service.delete_item(path)
    if success:
        return MessageResponse(message=f"Item '{path}' deleted successfully")
    raise HTTPException(
        status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to delete '{path}'",
    )


@router.post(
    "/share",
    response_model=ShareLinkResponse,
    summary="Create share link",
    description="Create a public share link for a file or folder.",
)
async def create_share_link(
    path: str = Query(..., description="Path to share"),
    password: str | None = Query(None, description="Optional password"),
    current_user: CurrentUser = None,
) -> ShareLinkResponse:
    """Create a public share link."""
    result = await nextcloud_service.get_share_link(path, password)
    if result:
        return ShareLinkResponse(**result)
    raise HTTPException(
        status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to create share link for '{path}'",
    )


@router.get(
    "/case/{case_id}/url",
    summary="Get case folder URL",
    description="Get the Nextcloud web URL for a case folder.",
)
async def get_case_folder_url(
    case_id: str,
    current_user: CurrentUser = None,
) -> dict[str, str]:
    """Get the web URL for a case folder."""
    url = await nextcloud_service.get_case_folder_url(case_id)
    return {"case_id": case_id, "url": url}
