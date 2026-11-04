"""FastAPI REST interface for InvoiceProcessingAutomationBot.

Exposes a local REST endpoint for RPA orchestrators (such as UiPath Studio
via the 'HTTP Request' activity) to trigger invoice batch processing without
re-implementing any validation or report generation logic.
"""

from pathlib import Path
import sys
from typing import Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from main import execute_process
from src.config import STATUS_FAILED

app = FastAPI(
    title="InvoiceProcessingAutomationBot API",
    description="Local REST API for RPA orchestrators (UiPath, Power Automate) to trigger invoice processing batches.",
    version="1.0.0",
)


class ProcessRequest(BaseModel):
    """Request payload for /process endpoint."""

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
    """Response payload returned upon successful processing."""

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


@app.get(
    "/health",
    tags=["Health"],
    summary="Health check endpoint for RPA bots to verify service readiness.",
)
def health_check() -> dict[str, str]:
    """Returns the health status of the Invoice Processing API."""
    return {"status": "healthy", "service": "InvoiceProcessingAutomationBot"}


@app.post(
    "/process",
    response_model=ProcessResponse,
    tags=["Invoice Processing"],
    summary="Process an invoice batch and generate an audit report.",
    responses={
        200: {"description": "Invoices processed successfully (or partial success with rejections partitioned)."},
        400: {"description": "Input file is corrupted, empty, or schema columns are missing."},
        404: {"description": "Input invoice file was not found."},
        500: {"description": "Unexpected server error during processing."},
    },
)
def process_invoice_batch(request: ProcessRequest | None = None) -> dict[str, Any]:
    """Processes an invoice Excel file and generates a multi-sheet audit report.

    Args:
        request: JSON payload with optional `input_path` and `output_path`.

    Returns:
        JSON response with execution status, record counts, and generated report path.
    """
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

    # Check if execute_process returned a failure summary
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

    # Standardize output_file_path in response
    report_path = result.get("generated_report_path") or result.get("output_file")
    result["output_file_path"] = str(report_path)

    return result


if __name__ == "__main__":
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=False)

