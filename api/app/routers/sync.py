"""
Sync router for AuditCaseOS API.

This module provides endpoints for syncing evidence files with Paperless-ngx
for OCR processing and text extraction.
"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi import status as http_status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.auth import get_current_user_required
from app.services.case_service import case_service
from app.services.paperless_service import paperless_service
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["sync"])


# =============================================================================
# Schemas
# =============================================================================


class SyncResponse(BaseModel):
    """Response for sync operations."""

    message: str = Field(..., description="Status message")
    case_id: str = Field(..., description="Case ID")
    total_files: int = Field(..., description="Total files to sync")
    synced_files: int = Field(0, description="Files successfully synced")
    failed_files: int = Field(0, description="Files that failed to sync")
    skipped_files: int = Field(0, description="Files skipped (not supported)")
    details: list[dict] = Field(default_factory=list, description="Per-file details")


class SyncStatusResponse(BaseModel):
    """Response for sync status check."""

    paperless_status: str = Field(..., description="Paperless connection status")
    paperless_url: str = Field(..., description="Paperless base URL")
    configured: bool = Field(..., description="Whether API token is configured")
    error: str | None = Field(None, description="Error message if unhealthy")


class EvidenceSyncResponse(BaseModel):
    """Response for single evidence sync."""

    message: str
    evidence_id: UUID
    file_name: str
    paperless_status: str
    extracted_text: str | None = None


# =============================================================================
# Dependencies
# =============================================================================


DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(get_current_user_required)]


# =============================================================================
# Helper Functions
# =============================================================================


# Supported file types for OCR
SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/gif",
    "image/tiff",
    "image/webp",
    "image/bmp",
    "text/plain",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def is_supported_for_ocr(mime_type: str | None) -> bool:
    """Check if a file type is supported for OCR processing."""
    if not mime_type:
        return False
    return mime_type.lower() in SUPPORTED_MIME_TYPES


async def sync_single_evidence(
    db: AsyncSession,
    evidence: dict,
    case_id_str: str,
) -> dict:
    """
    Sync a single evidence file to Paperless.

    Args:
        db: Database session
        evidence: Evidence record dict
        case_id_str: Human-readable case ID

    Returns:
        dict with sync result
    """
    evidence_id = evidence["id"]
    file_name = evidence["file_name"]
    file_path = evidence["file_path"]
    mime_type = evidence.get("mime_type", "")

    result = {
        "evidence_id": str(evidence_id),
        "file_name": file_name,
        "status": "pending",
        "error": None,
        "extracted_text_preview": None,
    }

    # Check if file type is supported
    if not is_supported_for_ocr(mime_type):
        result["status"] = "skipped"
        result["error"] = f"Unsupported file type: {mime_type}"
        logger.info(f"Skipping unsupported file: {file_name} ({mime_type})")
        return result

    try:
        # Download file from MinIO
        logger.info(f"Downloading evidence from MinIO: {file_path}")
        file_content = await storage_service.download_file(file_path)

        # Upload to Paperless
        logger.info(f"Uploading to Paperless: {file_name}")
        upload_result = await paperless_service.upload_document(
            file_content=file_content,
            filename=file_name,
            title=file_name,
            case_id=case_id_str,
        )

        result["status"] = "uploaded"
        result["paperless_result"] = upload_result

        # For PDF files, Paperless returns a task ID
        # We can optionally wait for processing, but that can take time
        # For now, mark as uploaded and let a background job handle text retrieval

        logger.info(f"Successfully uploaded {file_name} to Paperless")
        return result

    except ValueError as e:
        # API token not configured
        result["status"] = "error"
        result["error"] = str(e)
        logger.error(f"Configuration error syncing {file_name}: {e}")
        return result

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        logger.error(f"Failed to sync {file_name}: {e}")
        return result


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/status",
    response_model=SyncStatusResponse,
    summary="Check Paperless status",
    description="Check the connection status to Paperless-ngx OCR service.",
)
async def check_paperless_status(
    current_user: CurrentUser,
) -> SyncStatusResponse:
    """Check if Paperless-ngx is accessible and configured."""
    health = await paperless_service.health_check()

    return SyncStatusResponse(
        paperless_status=health.get("status", "unknown"),
        paperless_url=health.get("base_url", ""),
        configured=health.get("configured", False),
        error=health.get("error"),
    )


@router.post(
    "/case/{case_id}",
    response_model=SyncResponse,
    summary="Sync case evidence to Paperless",
    description="Upload all evidence files from a case to Paperless for OCR processing.",
)
async def sync_case_evidence(
    db: DbSession,
    current_user: CurrentUser,
    case_id: str = Path(..., description="Case ID (e.g., FIN-USB-0001)"),
) -> SyncResponse:
    """
    Sync all evidence files for a case to Paperless-ngx.

    This uploads each supported evidence file to Paperless for OCR processing.
    The extracted text will be stored in the evidence.extracted_text field
    once processing completes.
    """
    # Check Paperless configuration
    if not paperless_service.is_configured:
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Paperless API token not configured. Set PAPERLESS_API_TOKEN environment variable.",
        )

    # Verify case exists
    case_data = await case_service.get_case(db, case_id)
    if not case_data:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' not found",
        )

    case_uuid = case_data["id"]
    case_id_str = case_data["case_id"]

    # Get all evidence for the case
    query = text("""
        SELECT id, file_name, file_path, mime_type, extracted_text
        FROM evidence
        WHERE case_id = :case_uuid
        ORDER BY uploaded_at ASC
    """)
    result = await db.execute(query, {"case_uuid": str(case_uuid)})
    evidence_rows = result.fetchall()

    if not evidence_rows:
        return SyncResponse(
            message="No evidence files found for this case",
            case_id=case_id_str,
            total_files=0,
            synced_files=0,
            failed_files=0,
            skipped_files=0,
            details=[],
        )

    # Process each evidence file
    details = []
    synced = 0
    failed = 0
    skipped = 0

    for row in evidence_rows:
        evidence = dict(row._mapping)

        # Skip if already has extracted text
        if evidence.get("extracted_text"):
            details.append({
                "evidence_id": str(evidence["id"]),
                "file_name": evidence["file_name"],
                "status": "skipped",
                "error": "Already has extracted text",
            })
            skipped += 1
            continue

        sync_result = await sync_single_evidence(db, evidence, case_id_str)
        details.append(sync_result)

        if sync_result["status"] == "uploaded":
            synced += 1
        elif sync_result["status"] == "skipped":
            skipped += 1
        else:
            failed += 1

    return SyncResponse(
        message=f"Sync completed: {synced} uploaded, {skipped} skipped, {failed} failed",
        case_id=case_id_str,
        total_files=len(evidence_rows),
        synced_files=synced,
        failed_files=failed,
        skipped_files=skipped,
        details=details,
    )


@router.post(
    "/evidence/{evidence_id}",
    response_model=EvidenceSyncResponse,
    summary="Sync single evidence file",
    description="Upload a single evidence file to Paperless for OCR processing.",
)
async def sync_single_evidence_file(
    db: DbSession,
    current_user: CurrentUser,
    evidence_id: UUID = Path(..., description="Evidence UUID"),
) -> EvidenceSyncResponse:
    """
    Sync a single evidence file to Paperless-ngx.

    This uploads the evidence file to Paperless for OCR processing.
    """
    # Check Paperless configuration
    if not paperless_service.is_configured:
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Paperless API token not configured. Set PAPERLESS_API_TOKEN environment variable.",
        )

    # Get evidence record
    query = text("""
        SELECT e.*, c.case_id as case_id_str
        FROM evidence e
        JOIN cases c ON e.case_id = c.id
        WHERE e.id = :evidence_id
    """)
    result = await db.execute(query, {"evidence_id": str(evidence_id)})
    row = result.fetchone()

    if not row:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Evidence with ID '{evidence_id}' not found",
        )

    evidence = dict(row._mapping)
    case_id_str = evidence.get("case_id_str", "UNKNOWN")

    # Check if already has extracted text
    if evidence.get("extracted_text"):
        return EvidenceSyncResponse(
            message="Evidence already has extracted text",
            evidence_id=evidence_id,
            file_name=evidence["file_name"],
            paperless_status="skipped",
            extracted_text=evidence["extracted_text"][:500] if evidence["extracted_text"] else None,
        )

    # Sync the evidence
    sync_result = await sync_single_evidence(db, evidence, case_id_str)

    if sync_result["status"] == "error":
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync evidence: {sync_result.get('error', 'Unknown error')}",
        )

    return EvidenceSyncResponse(
        message=f"Evidence sync {sync_result['status']}",
        evidence_id=evidence_id,
        file_name=evidence["file_name"],
        paperless_status=sync_result["status"],
        extracted_text=sync_result.get("extracted_text_preview"),
    )


@router.post(
    "/evidence/{evidence_id}/extract",
    response_model=EvidenceSyncResponse,
    summary="Extract text from Paperless",
    description="Retrieve extracted text from Paperless and store in evidence record.",
)
async def extract_text_from_paperless(
    db: DbSession,
    current_user: CurrentUser,
    evidence_id: UUID = Path(..., description="Evidence UUID"),
    paperless_doc_id: int = None,
) -> EvidenceSyncResponse:
    """
    Retrieve extracted text from a Paperless document and update the evidence record.

    This endpoint is used after a document has been processed by Paperless to
    retrieve the OCR text and store it in the evidence table.
    """
    if not paperless_service.is_configured:
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Paperless API token not configured",
        )

    # Get evidence record
    query = text("SELECT * FROM evidence WHERE id = :evidence_id")
    result = await db.execute(query, {"evidence_id": str(evidence_id)})
    row = result.fetchone()

    if not row:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Evidence with ID '{evidence_id}' not found",
        )

    evidence = dict(row._mapping)

    if not paperless_doc_id:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="paperless_doc_id query parameter is required",
        )

    try:
        # Get document content from Paperless
        doc = await paperless_service.get_document(paperless_doc_id)

        if not doc:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Document {paperless_doc_id} not found in Paperless",
            )

        extracted_text = doc.get("content", "")

        # Update evidence record with extracted text
        update_query = text("""
            UPDATE evidence
            SET extracted_text = :extracted_text
            WHERE id = :evidence_id
        """)
        await db.execute(update_query, {
            "extracted_text": extracted_text,
            "evidence_id": str(evidence_id),
        })
        await db.commit()

        logger.info(f"Updated evidence {evidence_id} with extracted text ({len(extracted_text)} chars)")

        return EvidenceSyncResponse(
            message="Successfully extracted and stored OCR text",
            evidence_id=evidence_id,
            file_name=evidence["file_name"],
            paperless_status="extracted",
            extracted_text=extracted_text[:500] if extracted_text else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to extract text from Paperless: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract text: {e!s}",
        )


@router.get(
    "/paperless/search",
    summary="Search Paperless documents",
    description="Search documents in Paperless-ngx by content.",
)
async def search_paperless_documents(
    current_user: CurrentUser,
    query: str,
    page: int = 1,
    page_size: int = 25,
) -> dict:
    """Search documents in Paperless-ngx."""
    if not paperless_service.is_configured:
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Paperless API token not configured",
        )

    try:
        results = await paperless_service.search_documents(
            query=query,
            page=page,
            page_size=page_size,
        )
        return results

    except Exception as e:
        logger.error(f"Paperless search failed: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {e!s}",
        )
