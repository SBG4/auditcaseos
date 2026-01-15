"""Evidence router for AuditCaseOS API.

This module provides endpoints for managing evidence files,
including upload, download, listing, and deletion.
"""

import hashlib
import logging
from datetime import datetime
from io import BytesIO
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Path, Query, Request, UploadFile
from fastapi import status as http_status
from fastapi.responses import StreamingResponse
from pydantic import Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.auth import get_current_user_required
from app.schemas.common import BaseSchema, MessageResponse, TimestampMixin
from app.services.audit_service import audit_service
from app.services.case_service import case_service
from app.services.storage_service import storage_service
from app.services.nextcloud_service import nextcloud_service
from app.services.websocket_service import connection_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evidence", tags=["evidence"])


# =============================================================================
# Schemas
# =============================================================================


class EvidenceBase(BaseSchema):
    """Base schema for evidence data."""

    file_name: str = Field(..., description="Original filename")
    mime_type: str | None = Field(None, description="MIME type of the file")
    file_size: int = Field(..., ge=0, description="File size in bytes")
    description: str | None = Field(None, max_length=1000, description="Evidence description")
    file_hash: str | None = Field(None, description="SHA-256 hash of the file")


class EvidenceResponse(EvidenceBase, TimestampMixin):
    """Schema for evidence response."""

    id: UUID = Field(..., description="Evidence UUID")
    case_id: UUID = Field(..., description="Associated case UUID")
    case_id_str: str | None = Field(None, description="Human-readable case ID")
    file_path: str = Field(..., description="Storage path")
    uploaded_by: UUID = Field(..., description="UUID of user who uploaded")
    uploaded_by_name: str | None = Field(None, description="Name of uploader")
    extracted_text: str | None = Field(None, description="OCR extracted text")


class EvidenceListResponse(BaseSchema):
    """List of evidence items."""

    items: list[EvidenceResponse]
    total: int
    case_id: str


class EvidenceUploadResponse(EvidenceResponse):
    """Response after successful upload."""

    message: str = "Evidence uploaded successfully"


# =============================================================================
# Dependencies
# =============================================================================


DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(get_current_user_required)]


# =============================================================================
# Helper Functions
# =============================================================================


async def compute_file_hash(file: UploadFile) -> str:
    """Compute SHA-256 hash of uploaded file."""
    sha256 = hashlib.sha256()
    await file.seek(0)
    while chunk := await file.read(8192):
        sha256.update(chunk)
    await file.seek(0)
    return sha256.hexdigest()


async def get_file_size(file: UploadFile) -> int:
    """Get file size by reading content."""
    await file.seek(0)
    content = await file.read()
    size = len(content)
    await file.seek(0)
    return size


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/cases/{case_id}/upload",
    response_model=EvidenceUploadResponse,
    status_code=http_status.HTTP_201_CREATED,
    summary="Upload evidence file",
    description="Upload a new evidence file for a case.",
)
async def upload_evidence(
    db: DbSession,
    request: Request,
    current_user: CurrentUser,
    case_id: str = Path(..., description="Case ID (e.g., FIN-USB-0001)"),
    file: UploadFile = File(..., description="Evidence file to upload"),
    description: str | None = Query(None, description="Evidence description"),
) -> EvidenceUploadResponse:
    """
    Upload evidence file for a case.

    Accepts multipart/form-data with a file and optional description.
    The file is stored in MinIO and a SHA-256 hash is computed for integrity.
    """
    try:
        # Verify case exists
        case_data = await case_service.get_case(db, case_id)
        if not case_data:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Case with ID '{case_id}' not found",
            )

        case_uuid = case_data["id"]
        user_id = current_user["id"]

        # Compute file hash and size
        file_hash = await compute_file_hash(file)
        file_size = await get_file_size(file)

        # Read file content
        await file.seek(0)
        file_content = await file.read()
        await file.seek(0)

        # Upload to MinIO
        storage_path = await storage_service.upload_file(
            case_id=case_data["case_id"],
            file=file_content,
            filename=file.filename or "unknown",
            content_type=file.content_type,
        )

        # Insert into database
        query = text("""
            INSERT INTO evidence (case_id, file_name, file_path, file_size, mime_type, file_hash, description, uploaded_by)
            VALUES (:case_id, :file_name, :file_path, :file_size, :mime_type, :file_hash, :description, :uploaded_by)
            RETURNING *
        """)
        result = await db.execute(query, {
            "case_id": str(case_uuid),
            "file_name": file.filename or "unknown",
            "file_path": storage_path,
            "file_size": file_size,
            "mime_type": file.content_type or "application/octet-stream",
            "file_hash": file_hash,
            "description": description,
            "uploaded_by": str(user_id),
        })
        await db.commit()

        row = result.fetchone()
        evidence_data = dict(row._mapping) if row else {}

        # Get uploader name
        user_query = text("SELECT full_name FROM users WHERE id = :user_id")
        user_result = await db.execute(user_query, {"user_id": str(user_id)})
        user_row = user_result.fetchone()
        uploader_name = user_row.full_name if user_row else None

        # Log audit event
        client_ip = request.client.host if request.client else None
        await audit_service.log_create(
            db=db,
            entity_type="evidence",
            entity_id=evidence_data.get("id"),
            user_id=user_id,
            new_values={"file_name": file.filename, "case_id": case_data["case_id"]},
            user_ip=client_ip,
        )

        # Sync to Nextcloud (non-blocking - don't fail upload if NC is unavailable)
        try:
            nc_path = f"AuditCases/{case_data['case_id']}/Evidence/{file.filename or 'unknown'}"
            await nextcloud_service.upload_file(
                path=nc_path,
                content=file_content,
                content_type=file.content_type or "application/octet-stream",
            )
            logger.info(f"Evidence synced to Nextcloud: {nc_path}")
        except Exception as nc_error:
            logger.warning(f"Failed to sync evidence to Nextcloud (non-fatal): {nc_error}")

        # Broadcast evidence upload to case viewers
        try:
            await connection_manager.send_case_update(
                case_id=case_data["case_id"],
                update_type="evidence_added",
                data={
                    "evidence_id": str(evidence_data.get("id")),
                    "file_name": file.filename or "unknown",
                    "file_size": file_size,
                    "mime_type": file.content_type,
                },
                triggered_by=str(user_id),
            )
        except Exception as ws_error:
            logger.debug(f"WebSocket broadcast skipped: {ws_error}")

        now = datetime.utcnow()
        return EvidenceUploadResponse(
            id=evidence_data["id"],
            case_id=case_uuid,
            case_id_str=case_data["case_id"],
            file_name=evidence_data["file_name"],
            mime_type=evidence_data["mime_type"],
            file_size=evidence_data["file_size"],
            file_hash=evidence_data["file_hash"],
            file_path=evidence_data["file_path"],
            description=evidence_data.get("description"),
            uploaded_by=user_id,
            uploaded_by_name=uploader_name,
            extracted_text=None,
            created_at=evidence_data.get("uploaded_at", now),
            updated_at=evidence_data.get("uploaded_at", now),
            message="Evidence uploaded successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload evidence: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload evidence: {str(e)}",
        )


@router.get(
    "/cases/{case_id}",
    response_model=EvidenceListResponse,
    summary="List case evidence",
    description="Retrieve all evidence files for a case.",
)
async def list_case_evidence(
    db: DbSession,
    current_user: CurrentUser,
    case_id: str = Path(..., description="Case ID"),
) -> EvidenceListResponse:
    """List all evidence files associated with a case."""
    try:
        # Verify case exists
        case_data = await case_service.get_case(db, case_id)
        if not case_data:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Case with ID '{case_id}' not found",
            )

        case_uuid = case_data["id"]

        # Get evidence
        query = text("""
            SELECT e.*, u.full_name as uploaded_by_name
            FROM evidence e
            LEFT JOIN users u ON e.uploaded_by = u.id
            WHERE e.case_id = :case_uuid
            ORDER BY e.uploaded_at DESC
        """)
        result = await db.execute(query, {"case_uuid": str(case_uuid)})
        rows = result.fetchall()

        items = []
        for row in rows:
            row_dict = dict(row._mapping)
            items.append(EvidenceResponse(
                id=row_dict["id"],
                case_id=row_dict["case_id"],
                case_id_str=case_data["case_id"],
                file_name=row_dict["file_name"],
                mime_type=row_dict.get("mime_type"),
                file_size=row_dict.get("file_size", 0),
                file_hash=row_dict.get("file_hash"),
                file_path=row_dict["file_path"],
                description=row_dict.get("description"),
                uploaded_by=row_dict["uploaded_by"],
                uploaded_by_name=row_dict.get("uploaded_by_name"),
                extracted_text=row_dict.get("extracted_text"),
                created_at=row_dict.get("uploaded_at", datetime.utcnow()),
                updated_at=row_dict.get("uploaded_at", datetime.utcnow()),
            ))

        return EvidenceListResponse(
            items=items,
            total=len(items),
            case_id=case_data["case_id"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list evidence: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve evidence",
        )


@router.get(
    "/{evidence_id}",
    response_model=EvidenceResponse,
    summary="Get evidence metadata",
    description="Retrieve metadata for a specific evidence file.",
)
async def get_evidence(
    db: DbSession,
    current_user: CurrentUser,
    evidence_id: UUID = Path(..., description="Evidence UUID"),
) -> EvidenceResponse:
    """Get metadata for a specific evidence file."""
    try:
        query = text("""
            SELECT e.*, u.full_name as uploaded_by_name, c.case_id as case_id_str
            FROM evidence e
            LEFT JOIN users u ON e.uploaded_by = u.id
            LEFT JOIN cases c ON e.case_id = c.id
            WHERE e.id = :evidence_id
        """)
        result = await db.execute(query, {"evidence_id": str(evidence_id)})
        row = result.fetchone()

        if not row:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Evidence with ID '{evidence_id}' not found",
            )

        row_dict = dict(row._mapping)
        return EvidenceResponse(
            id=row_dict["id"],
            case_id=row_dict["case_id"],
            case_id_str=row_dict.get("case_id_str"),
            file_name=row_dict["file_name"],
            mime_type=row_dict.get("mime_type"),
            file_size=row_dict.get("file_size", 0),
            file_hash=row_dict.get("file_hash"),
            file_path=row_dict["file_path"],
            description=row_dict.get("description"),
            uploaded_by=row_dict["uploaded_by"],
            uploaded_by_name=row_dict.get("uploaded_by_name"),
            extracted_text=row_dict.get("extracted_text"),
            created_at=row_dict.get("uploaded_at", datetime.utcnow()),
            updated_at=row_dict.get("uploaded_at", datetime.utcnow()),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get evidence: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve evidence",
        )


@router.get(
    "/{evidence_id}/download",
    response_class=StreamingResponse,
    summary="Download evidence file",
    description="Download the actual evidence file content.",
)
async def download_evidence(
    db: DbSession,
    request: Request,
    current_user: CurrentUser,
    evidence_id: UUID = Path(..., description="Evidence UUID"),
) -> StreamingResponse:
    """Download an evidence file."""
    try:
        # Get evidence metadata
        query = text("SELECT * FROM evidence WHERE id = :evidence_id")
        result = await db.execute(query, {"evidence_id": str(evidence_id)})
        row = result.fetchone()

        if not row:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Evidence with ID '{evidence_id}' not found",
            )

        evidence = dict(row._mapping)

        # Download file from MinIO
        file_content = await storage_service.download_file(evidence["file_path"])

        # Log download event
        client_ip = request.client.host if request.client else None
        try:
            await audit_service.log_download(
                db=db,
                entity_type="evidence",
                entity_id=evidence_id,
                user_id=current_user["id"],
                file_path=evidence["file_path"],
                user_ip=client_ip,
            )
        except Exception as audit_error:
            logger.warning(f"Failed to log download: {audit_error}")

        return StreamingResponse(
            BytesIO(file_content),
            media_type=evidence.get("mime_type", "application/octet-stream"),
            headers={
                "Content-Disposition": f'attachment; filename="{evidence["file_name"]}"',
                "Content-Length": str(len(file_content)),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download evidence: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download evidence",
        )


@router.delete(
    "/{evidence_id}",
    response_model=MessageResponse,
    summary="Delete evidence",
    description="Delete an evidence file and its metadata.",
)
async def delete_evidence(
    db: DbSession,
    request: Request,
    current_user: CurrentUser,
    evidence_id: UUID = Path(..., description="Evidence UUID"),
) -> MessageResponse:
    """Delete an evidence file."""
    try:
        # Get evidence metadata
        query = text("SELECT * FROM evidence WHERE id = :evidence_id")
        result = await db.execute(query, {"evidence_id": str(evidence_id)})
        row = result.fetchone()

        if not row:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Evidence with ID '{evidence_id}' not found",
            )

        evidence = dict(row._mapping)

        # Delete from MinIO
        await storage_service.delete_file(evidence["file_path"])

        # Delete from database
        delete_query = text("DELETE FROM evidence WHERE id = :evidence_id")
        await db.execute(delete_query, {"evidence_id": str(evidence_id)})
        await db.commit()

        # Log delete event
        client_ip = request.client.host if request.client else None
        await audit_service.log_delete(
            db=db,
            entity_type="evidence",
            entity_id=evidence_id,
            user_id=current_user["id"],
            old_values={"file_name": evidence["file_name"], "file_path": evidence["file_path"]},
            user_ip=client_ip,
        )

        return MessageResponse(
            message=f"Evidence '{evidence['file_name']}' deleted successfully",
            details={"evidence_id": str(evidence_id), "file_name": evidence["file_name"]},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete evidence: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete evidence",
        )


# =============================================================================
# Sync Endpoints
# =============================================================================


class SyncResponse(BaseSchema):
    """Response for sync operations."""

    success: bool
    message: str
    synced_count: int = 0
    failed_count: int = 0
    details: list[dict[str, Any]] = []


@router.post(
    "/cases/{case_id}/sync-to-nextcloud",
    response_model=SyncResponse,
    summary="Sync evidence to Nextcloud",
    description="Sync all case evidence files from MinIO to Nextcloud Evidence folder.",
)
async def sync_evidence_to_nextcloud(
    db: DbSession,
    current_user: CurrentUser,
    case_id: str = Path(..., description="Case ID"),
) -> SyncResponse:
    """
    Sync all evidence files for a case to Nextcloud.

    Downloads files from MinIO and uploads to Nextcloud AuditCases/{case_id}/Evidence/
    """
    try:
        # Verify case exists
        case_data = await case_service.get_case(db, case_id)
        if not case_data:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Case with ID '{case_id}' not found",
            )

        case_uuid = case_data["id"]

        # Get all evidence for case
        query = text("SELECT * FROM evidence WHERE case_id = :case_uuid")
        result = await db.execute(query, {"case_uuid": str(case_uuid)})
        rows = result.fetchall()

        if not rows:
            return SyncResponse(
                success=True,
                message="No evidence files to sync",
                synced_count=0,
                failed_count=0,
            )

        synced = []
        failed = []

        for row in rows:
            evidence = dict(row._mapping)
            try:
                # Download from MinIO
                file_content = await storage_service.download_file(evidence["file_path"])

                # Upload to Nextcloud
                nc_path = f"AuditCases/{case_data['case_id']}/Evidence/{evidence['file_name']}"
                success = await nextcloud_service.upload_file(
                    path=nc_path,
                    content=file_content,
                    content_type=evidence.get("mime_type", "application/octet-stream"),
                )

                if success:
                    synced.append({
                        "evidence_id": str(evidence["id"]),
                        "file_name": evidence["file_name"],
                        "nc_path": nc_path,
                    })
                else:
                    failed.append({
                        "evidence_id": str(evidence["id"]),
                        "file_name": evidence["file_name"],
                        "error": "Upload to Nextcloud failed",
                    })

            except Exception as e:
                logger.error(f"Failed to sync evidence {evidence['id']}: {e}")
                failed.append({
                    "evidence_id": str(evidence["id"]),
                    "file_name": evidence["file_name"],
                    "error": str(e),
                })

        return SyncResponse(
            success=len(failed) == 0,
            message=f"Synced {len(synced)} files, {len(failed)} failed",
            synced_count=len(synced),
            failed_count=len(failed),
            details=synced + failed,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to sync evidence to Nextcloud: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync evidence: {str(e)}",
        )


@router.post(
    "/cases/{case_id}/import-from-nextcloud",
    response_model=SyncResponse,
    summary="Import files from Nextcloud",
    description="Import files from Nextcloud Evidence folder into AuditCaseOS evidence.",
)
async def import_evidence_from_nextcloud(
    db: DbSession,
    request: Request,
    current_user: CurrentUser,
    case_id: str = Path(..., description="Case ID"),
) -> SyncResponse:
    """
    Import files from Nextcloud Evidence folder into AuditCaseOS.

    Lists files in Nextcloud AuditCases/{case_id}/Evidence/ and creates
    Evidence records for files not already in the database.
    """
    try:
        # Verify case exists
        case_data = await case_service.get_case(db, case_id)
        if not case_data:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Case with ID '{case_id}' not found",
            )

        case_uuid = case_data["id"]
        user_id = current_user["id"]

        # Get existing evidence file names
        query = text("SELECT file_name FROM evidence WHERE case_id = :case_uuid")
        result = await db.execute(query, {"case_uuid": str(case_uuid)})
        existing_files = {row.file_name for row in result.fetchall()}

        # List files in Nextcloud Evidence folder
        nc_path = f"AuditCases/{case_data['case_id']}/Evidence"
        nc_files = await nextcloud_service.list_folder(nc_path)

        if not nc_files:
            return SyncResponse(
                success=True,
                message="No files found in Nextcloud Evidence folder",
                synced_count=0,
                failed_count=0,
            )

        imported = []
        failed = []
        skipped = []

        for nc_file in nc_files:
            # Skip directories
            if nc_file.get("is_directory", False):
                continue

            file_name = nc_file.get("name", "")
            if not file_name:
                continue

            # Skip if already exists
            if file_name in existing_files:
                skipped.append({"file_name": file_name, "reason": "Already exists"})
                continue

            try:
                # Download from Nextcloud
                file_path = f"{nc_path}/{file_name}"
                file_content = await nextcloud_service.download_file(file_path)

                if file_content is None:
                    failed.append({
                        "file_name": file_name,
                        "error": "Failed to download from Nextcloud",
                    })
                    continue

                # Compute hash
                file_hash = hashlib.sha256(file_content).hexdigest()
                file_size = len(file_content)

                # Upload to MinIO
                storage_path = await storage_service.upload_file(
                    case_id=case_data["case_id"],
                    file=file_content,
                    filename=file_name,
                    content_type=nc_file.get("content_type", "application/octet-stream"),
                )

                # Insert into database
                insert_query = text("""
                    INSERT INTO evidence (case_id, file_name, file_path, file_size, mime_type, file_hash, description, uploaded_by)
                    VALUES (:case_id, :file_name, :file_path, :file_size, :mime_type, :file_hash, :description, :uploaded_by)
                    RETURNING id
                """)
                result = await db.execute(insert_query, {
                    "case_id": str(case_uuid),
                    "file_name": file_name,
                    "file_path": storage_path,
                    "file_size": file_size,
                    "mime_type": nc_file.get("content_type", "application/octet-stream"),
                    "file_hash": file_hash,
                    "description": f"Imported from Nextcloud on {datetime.utcnow().isoformat()}",
                    "uploaded_by": str(user_id),
                })
                await db.commit()

                row = result.fetchone()
                evidence_id = row.id if row else None

                # Log audit event
                client_ip = request.client.host if request.client else None
                await audit_service.log_create(
                    db=db,
                    entity_type="evidence",
                    entity_id=evidence_id,
                    user_id=user_id,
                    new_values={"file_name": file_name, "case_id": case_data["case_id"], "source": "nextcloud"},
                    user_ip=client_ip,
                )

                imported.append({
                    "evidence_id": str(evidence_id),
                    "file_name": file_name,
                    "file_size": file_size,
                })

            except Exception as e:
                logger.error(f"Failed to import {file_name} from Nextcloud: {e}")
                failed.append({
                    "file_name": file_name,
                    "error": str(e),
                })

        return SyncResponse(
            success=len(failed) == 0,
            message=f"Imported {len(imported)} files, {len(failed)} failed, {len(skipped)} skipped",
            synced_count=len(imported),
            failed_count=len(failed),
            details=imported + failed + skipped,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to import evidence from Nextcloud: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import evidence: {str(e)}",
        )
