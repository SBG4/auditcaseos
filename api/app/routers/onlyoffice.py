"""ONLYOFFICE router for document editing endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.auth import CurrentUser
from app.services.case_service import case_service
from app.services.nextcloud_service import nextcloud_service
from app.services.onlyoffice_service import onlyoffice_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/onlyoffice", tags=["onlyoffice"])


# =============================================================================
# Schemas
# =============================================================================


class OnlyOfficeHealthResponse(BaseModel):
    """ONLYOFFICE health check response."""

    available: bool
    version: str | None = None
    build: str | None = None
    external_url: str | None = None
    error: str | None = None


class SupportedExtensionsResponse(BaseModel):
    """Supported file extensions response."""

    documents: list[str]
    spreadsheets: list[str]
    presentations: list[str]
    editable: list[str]


class EditUrlResponse(BaseModel):
    """Response with document edit URL."""

    file_path: str
    edit_url: str
    document_type: str | None = None
    is_editable: bool
    is_viewable: bool


class CaseDocumentsResponse(BaseModel):
    """Response with editable documents for a case."""

    case_id: str
    documents: list[EditUrlResponse]
    total: int


# =============================================================================
# Dependencies
# =============================================================================


DbSession = Annotated[AsyncSession, Depends(get_db)]


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/health",
    response_model=OnlyOfficeHealthResponse,
    summary="Check ONLYOFFICE health",
    description="Check if ONLYOFFICE Document Server is available.",
)
async def health_check() -> OnlyOfficeHealthResponse:
    """Check ONLYOFFICE Document Server connection status."""
    result = await onlyoffice_service.health_check()
    return OnlyOfficeHealthResponse(**result)


@router.get(
    "/extensions",
    response_model=SupportedExtensionsResponse,
    summary="Get supported extensions",
    description="Get list of file extensions supported by ONLYOFFICE.",
)
async def get_supported_extensions() -> SupportedExtensionsResponse:
    """Get supported file extensions for ONLYOFFICE."""
    extensions = onlyoffice_service.get_supported_extensions()
    return SupportedExtensionsResponse(**extensions)


@router.get(
    "/edit-url",
    response_model=EditUrlResponse,
    summary="Get edit URL for file",
    description="Get the ONLYOFFICE edit URL for a file in Nextcloud.",
)
async def get_edit_url(
    file_path: str = Query(..., description="File path in Nextcloud (e.g., 'AuditCases/IT-POLICY-0001/Reports/report.docx')"),
    current_user: CurrentUser = None,
) -> EditUrlResponse:
    """Get the edit URL for a document."""
    # Extract filename from path
    filename = file_path.split("/")[-1] if "/" in file_path else file_path

    is_editable = onlyoffice_service.is_editable(filename)
    is_viewable = onlyoffice_service.is_viewable(filename)
    document_type = onlyoffice_service.get_document_type(filename)

    if not is_viewable:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"File type not supported by ONLYOFFICE: {filename}",
        )

    # Get file ID from Nextcloud for direct ONLYOFFICE URL
    file_id = await onlyoffice_service.get_nextcloud_file_id(file_path)
    edit_url = onlyoffice_service.get_nextcloud_edit_url(file_path, file_id)

    return EditUrlResponse(
        file_path=file_path,
        edit_url=edit_url,
        document_type=document_type,
        is_editable=is_editable,
        is_viewable=is_viewable,
    )


@router.get(
    "/case/{case_id}/documents",
    response_model=CaseDocumentsResponse,
    summary="List editable case documents",
    description="List all documents in a case that can be edited with ONLYOFFICE.",
)
async def list_case_editable_documents(
    db: DbSession,
    case_id: str,
    subfolder: str = Query("", description="Subfolder to list (Evidence, Reports, Notes, or empty for all)"),
    current_user: CurrentUser = None,
) -> CaseDocumentsResponse:
    """List editable documents for a case."""
    # Verify case exists
    case_data = await case_service.get_case(db, case_id)
    if not case_data:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' not found",
        )

    # Get files from Nextcloud
    base_path = f"AuditCases/{case_id}"
    if subfolder:
        base_path = f"{base_path}/{subfolder}"

    files = await nextcloud_service.list_folder(base_path)

    documents = []
    for file_info in files:
        if file_info.get("is_directory", False):
            continue

        filename = file_info.get("name", "")
        if not filename:
            continue

        # Check if viewable in ONLYOFFICE
        if not onlyoffice_service.is_viewable(filename):
            continue

        file_path = f"{base_path}/{filename}"
        is_editable = onlyoffice_service.is_editable(filename)
        document_type = onlyoffice_service.get_document_type(filename)
        edit_url = onlyoffice_service.get_nextcloud_edit_url(file_path)

        documents.append(EditUrlResponse(
            file_path=file_path,
            edit_url=edit_url,
            document_type=document_type,
            is_editable=is_editable,
            is_viewable=True,
        ))

    return CaseDocumentsResponse(
        case_id=case_id,
        documents=documents,
        total=len(documents),
    )


@router.get(
    "/editor-url",
    summary="Get ONLYOFFICE editor URL",
    description="Get the base URL for ONLYOFFICE Document Server.",
)
async def get_editor_url() -> dict[str, str]:
    """Get the ONLYOFFICE editor base URL."""
    return {
        "editor_url": onlyoffice_service.get_editor_url(),
    }
