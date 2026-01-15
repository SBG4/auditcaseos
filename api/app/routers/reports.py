"""Reports router for generating audit case reports."""

import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..schemas.report import ReportTemplate
from ..services.report_service import report_service
from .auth import get_current_user_required

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])

# Type aliases for dependency injection
DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(get_current_user_required)]


@router.get(
    "/case/{case_id}.docx",
    summary="Generate DOCX report for a case",
    description="""
    Generate a Microsoft Word (DOCX) report for the specified case.

    The report includes:
    - Cover page with case ID, title, and classification
    - Executive summary (AI-generated when available)
    - Case details and metadata
    - Timeline of events
    - Findings sorted by severity
    - Evidence list with file hashes
    - Similar cases (optional)

    **Templates:**
    - STANDARD: Full report with all sections
    - EXECUTIVE_SUMMARY: Brief summary for management
    - DETAILED: Comprehensive report with appendices
    - COMPLIANCE: Compliance-focused report format
    """,
    responses={
        200: {
            "description": "DOCX report file",
            "content": {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {}
            },
        },
        404: {"description": "Case not found"},
    },
)
async def generate_case_report(
    db: DbSession,
    current_user: CurrentUser,
    case_id: str = Path(
        ...,
        description="Case ID in SCOPE-TYPE-SEQ format (e.g., FIN-USB-0001)",
        examples=["FIN-USB-0001", "IT-POLICY-0002"],
    ),
    template: ReportTemplate = Query(
        default=ReportTemplate.STANDARD,
        description="Report template to use",
    ),
    include_evidence: bool = Query(
        default=True,
        description="Include evidence list section",
    ),
    include_similar: bool = Query(
        default=True,
        description="Include similar cases section",
    ),
    include_ai_summary: bool = Query(
        default=True,
        description="Include AI-generated executive summary",
    ),
    watermark: str | None = Query(
        default=None,
        max_length=50,
        description="Watermark text (e.g., DRAFT, CONFIDENTIAL)",
        examples=["DRAFT", "CONFIDENTIAL"],
    ),
    title: str | None = Query(
        default=None,
        max_length=255,
        description="Custom report title (defaults to 'Audit Case Report')",
    ),
) -> StreamingResponse:
    """Generate and download a DOCX report for the specified case."""
    try:
        # Generate the report
        buffer = await report_service.generate_report(
            db=db,
            case_id=case_id,
            template=template.value,
            include_evidence=include_evidence,
            include_similar=include_similar,
            include_ai_summary=include_ai_summary,
            watermark=watermark,
            title=title,
        )

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{case_id}_report_{timestamp}.docx"

        logger.info(f"User {current_user.get('email')} generated report for case {case_id}")

        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Report-Case-ID": case_id,
                "X-Report-Template": template.value,
            },
        )

    except ValueError as e:
        logger.warning(f"Report generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Report generation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report",
        )


@router.get(
    "/templates",
    summary="List available report templates",
    description="Get list of available report templates with descriptions.",
)
async def list_templates(
    current_user: CurrentUser,
) -> dict:
    """List available report templates."""
    return {
        "templates": [
            {
                "name": "STANDARD",
                "description": "Full case report with all sections including executive summary, case details, timeline, findings, evidence, and similar cases.",
                "sections": [
                    "cover_page",
                    "executive_summary",
                    "case_details",
                    "timeline",
                    "findings",
                    "evidence",
                    "similar_cases",
                ],
            },
            {
                "name": "EXECUTIVE_SUMMARY",
                "description": "Brief summary report suitable for management review. Includes only the most critical information and top findings.",
                "sections": [
                    "cover_page",
                    "executive_summary",
                    "case_details",
                    "top_findings",
                ],
            },
            {
                "name": "DETAILED",
                "description": "Comprehensive investigation report with all available data including entities appendix.",
                "sections": [
                    "cover_page",
                    "executive_summary",
                    "case_details",
                    "timeline",
                    "findings",
                    "evidence",
                    "similar_cases",
                    "entities_appendix",
                ],
            },
            {
                "name": "COMPLIANCE",
                "description": "Compliance-focused report for regulatory requirements. Emphasizes findings, evidence chain, and timeline.",
                "sections": [
                    "cover_page",
                    "case_details",
                    "findings",
                    "timeline",
                    "evidence",
                ],
            },
        ]
    }


@router.get(
    "/health",
    summary="Check report service health",
    description="Verify that the report generation service is operational.",
)
async def report_health() -> dict:
    """Check report service health."""
    try:
        # Try to create a basic document to verify python-docx works
        from docx import Document
        doc = Document()
        doc.add_paragraph("Health check")

        return {
            "status": "healthy",
            "service": "report_service",
            "docx_available": True,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "report_service",
            "docx_available": False,
            "error": str(e),
        }
