"""FastAPI REST interface for InvoiceProcessingAutomationBot.

Exposes endpoints for both local UiPath compatibility and cloud deployment:
1. GET  /health              - Bot health and readiness status
2. POST /upload              - Multipart file upload & processing for cloud/remote clients
3. GET  /download/{proc_id}  - Secure report download for remote clients
4. POST /process             - Local path-based execution (retained for backward compatibility)
"""

from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import re
import sys
import time
from typing import Any
import uuid

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from main import execute_process
from src.config import (
    BASE_DIR,
    REASON_DUPLICATE_ID,
    REASON_INVALID_AMOUNT,
    REASON_MISSING_ID,
    STATUS_FAILED,
    STATUS_SUCCESS,
)

logger = logging.getLogger("InvoiceProcessingBot")

# Maximum upload limit: 10 MB
MAX_UPLOAD_SIZE = 10 * 1024 * 1024

# Cloud storage directory for ephemeral uploads and generated reports
CLOUD_STORAGE_DIR = Path(os.getenv("STORAGE_DIR", str(BASE_DIR / "data" / "cloud_storage")))
UPLOADS_DIR = CLOUD_STORAGE_DIR / "uploads"
REPORTS_DIR = CLOUD_STORAGE_DIR / "reports"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="InvoiceProcessingAutomationBot API",
    description="Enterprise REST API for Invoice Batch Validation, Audit Reporting, and UiPath Cloud Integration.",
    version="2.0.0",
)


def cleanup_old_files(max_age_seconds: int = 3600) -> None:
    """Removes temporary uploads and generated reports older than max_age_seconds."""
    now = time.time()
    for directory in (UPLOADS_DIR, REPORTS_DIR):
        if not directory.exists():
            continue
        for file_path in directory.glob("*.xlsx"):
            try:
                if file_path.is_file() and (now - file_path.stat().st_mtime) > max_age_seconds:
                    file_path.unlink(missing_ok=True)
            except Exception as exc:
                logger.warning(f"Failed to remove stale file {file_path}: {exc}")


class ProcessRequest(BaseModel):
    """Request payload for legacy /process endpoint."""

    input_path: str | None = Field(
        default=None,
        description="Path to the input Excel invoice file. Defaults to data/input/sample_invoices.xlsx.",
        examples=["data/input/sample_invoices.xlsx"],
    )
    output_path: str | None = Field(
        default=None,
        description="Target path for the generated Excel report. Defaults to data/output/invoice_processing_report.xlsx.",
        examples=["data/output/invoice_processing_report.xlsx"],
    )


class ProcessResponse(BaseModel):
    """Response payload returned upon legacy path processing."""

    success: bool
    execution_status: str
    total_records: int
    valid_count: int
    valid_total_amount: float
    rejected_count: int
    rejected_total_amount: float
    output_file_path: str
    duration_seconds: float
    rejection_breakdown: dict[str, int]
    start_time: str
    end_time: str
    input_file: str


class UploadResponse(BaseModel):
    """Response payload returned upon cloud multipart upload and processing."""

    success: bool
    processing_id: str
    processing_status: str
    total_invoices: int
    valid_invoice_count: int
    rejected_invoice_count: int
    valid_invoice_amount: float
    rejected_invoice_amount: float
    duplicate_count: int
    missing_id_count: int
    invalid_amount_count: int
    report_download_url: str
    duration_seconds: float
    start_time: str
    end_time: str


@app.get(
    "/health",
    tags=["Health"],
    summary="Health check endpoint for RPA bots to verify service readiness.",
)
def health_check() -> dict[str, str]:
    """Returns the health status of the Invoice Processing API."""
    return {
        "status": "healthy",
        "service": "InvoiceProcessingAutomationBot",
        "version": "2.0.0",
    }


@app.post(
    "/upload",
    response_model=UploadResponse,
    tags=["Cloud Invoice Processing"],
    summary="Upload an Excel invoice file for processing and generate a downloadable audit report.",
    responses={
        200: {"description": "Invoices processed successfully (or partial success with rejections partitioned)."},
        400: {"description": "Invalid file type, corrupted zip archive, or missing schema headers."},
        413: {"description": "File exceeds maximum upload size (10 MB)."},
        500: {"description": "Unexpected server error during processing."},
    },
)
async def upload_and_process_invoices(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Excel workbook containing invoice records (.xlsx format)."),
) -> dict[str, Any]:
    """Handles multipart/form-data upload, processes invoices, and prepares downloadable report."""
    # 1. Validate file extension
    filename = file.filename or ""
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file extension. Only Excel files (.xlsx) are supported.",
        )

    # 2. Read content with size check (limit to 10 MB)
    content = await file.read(MAX_UPLOAD_SIZE + 1024)
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE if hasattr(status, "HTTP_413_CONTENT_TOO_LARGE") else 413,
            detail="File size exceeds the maximum allowed limit of 10 MB.",
        )

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes).",
        )

    # 3. Validate ZIP magic bytes (standard .xlsx openXML signature)
    if not content.startswith(b"PK\x03\x04"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid Excel (.xlsx) file: missing zip container header.",
        )

    # 4. Generate unique processing ID and server-side paths
    processing_id = uuid.uuid4().hex
    input_file_path = UPLOADS_DIR / f"{processing_id}.xlsx"
    output_file_path = REPORTS_DIR / f"{processing_id}_report.xlsx"

    # Save content to disk safely
    with open(input_file_path, "wb") as f:
        f.write(content)

    # Schedule background cleanup for old files
    background_tasks.add_task(cleanup_old_files, max_age_seconds=3600)

    # 5. Process through existing processing engine
    try:
        result = execute_process(
            input_path=input_file_path,
            output_path=output_file_path,
        )
    except Exception as exc:
        logger.critical(f"Unhandled exception during /upload: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "processing_id": processing_id,
                "processing_status": STATUS_FAILED,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            },
        ) from exc

    # Check for failure in execute_process
    if not result.get("success", False):
        error_type = result.get("error_type", "ProcessingError")
        error_message = result.get("error_message", "Invoice processing failed.")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "processing_id": processing_id,
                "processing_status": STATUS_FAILED,
                "error_type": error_type,
                "error_message": error_message,
                "duration_seconds": result.get("duration_seconds", 0.0),
            },
        )

    # Extract granular breakdown counts
    rejection_breakdown = result.get("rejection_breakdown", {})
    duplicate_count = rejection_breakdown.get(REASON_DUPLICATE_ID, 0)
    missing_id_count = rejection_breakdown.get(REASON_MISSING_ID, 0)
    invalid_amount_count = rejection_breakdown.get(REASON_INVALID_AMOUNT, 0)

    return {
        "success": True,
        "processing_id": processing_id,
        "processing_status": result.get("execution_status", STATUS_SUCCESS),
        "total_invoices": result.get("total_records", 0),
        "valid_invoice_count": result.get("valid_count", 0),
        "rejected_invoice_count": result.get("rejected_count", 0),
        "valid_invoice_amount": result.get("valid_total_amount", 0.0),
        "rejected_invoice_amount": result.get("rejected_total_amount", 0.0),
        "duplicate_count": duplicate_count,
        "missing_id_count": missing_id_count,
        "invalid_amount_count": invalid_amount_count,
        "report_download_url": f"/download/{processing_id}",
        "duration_seconds": result.get("duration_seconds", 0.0),
        "start_time": result.get("start_time", ""),
        "end_time": result.get("end_time", ""),
    }


@app.get(
    "/download/{processing_id}",
    tags=["Cloud Invoice Processing"],
    summary="Download the generated Excel audit report for a given processing ID.",
    responses={
        200: {
            "description": "Excel audit report workbook file.",
            "content": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}},
        },
        400: {"description": "Invalid processing ID format."},
        404: {"description": "Report not found or has expired."},
    },
)
def download_report(processing_id: str) -> FileResponse:
    """Serves the generated Excel audit report as a downloadable attachment."""
    # Strict validation of processing_id to eliminate path traversal attacks
    if not re.match(r"^[a-zA-Z0-9_-]{8,64}$", processing_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid processing ID format.",
        )

    report_file = REPORTS_DIR / f"{processing_id}_report.xlsx"
    if not report_file.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found or has expired. Processing ID: '{processing_id}'.",
        )

    return FileResponse(
        path=report_file,
        filename=f"invoice_audit_report_{processing_id[:8]}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.post(
    "/process",
    response_model=ProcessResponse,
    tags=["Local Invoice Processing (Legacy Compatibility)"],
    summary="Process an invoice batch by local file path (UiPath local compatibility).",
    responses={
        200: {"description": "Invoices processed successfully (or partial success with rejections partitioned)."},
        400: {"description": "Input file is corrupted, empty, or schema columns are missing."},
        404: {"description": "Input invoice file was not found."},
        500: {"description": "Unexpected server error during processing."},
    },
)
def process_invoice_batch(request: ProcessRequest | None = None) -> dict[str, Any]:
    """Processes an invoice Excel file by local path (retained for backward compatibility)."""
    req_input = request.input_path if request else None
    req_output = request.output_path if request else None

    try:
        result = execute_process(input_path=req_input, output_path=req_output)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "execution_status": STATUS_FAILED,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            },
        ) from exc

    if not result.get("success", False):
        error_type = result.get("error_type", "ProcessingError")
        error_message = result.get("error_message", "Invoice processing failed")

        if error_type == "InputFileNotFoundError":
            http_status = status.HTTP_404_NOT_FOUND
        elif error_type in ("CorruptedExcelError", "EmptyWorkbookError", "MissingColumnError"):
            http_status = status.HTTP_400_BAD_REQUEST
        else:
            http_status = status.HTTP_500_INTERNAL_SERVER_ERROR

        return JSONResponse(
            status_code=http_status,
            content={
                "success": False,
                "execution_status": result.get("execution_status", STATUS_FAILED),
                "error_type": error_type,
                "error_message": error_message,
                "input_file": result.get("input_file"),
                "duration_seconds": result.get("duration_seconds", 0.0),
            },
        )

    report_path = result.get("generated_report_path") or result.get("output_file")
    result["output_file_path"] = str(report_path)

    return result


if __name__ == "__main__":
    # Binds to 0.0.0.0 if PORT is set (cloud container), otherwise 127.0.0.1 for local safety
    port = int(os.getenv("PORT", "8000"))
    host = "0.0.0.0" if os.getenv("PORT") else "127.0.0.1"
    uvicorn.run("api:app", host=host, port=port, reload=False)
