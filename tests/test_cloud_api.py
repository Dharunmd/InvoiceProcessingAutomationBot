"""Unit and integration tests for Cloud FastAPI endpoints: /upload and /download/{id}."""

import io
from pathlib import Path
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api import MAX_UPLOAD_SIZE, app

client = TestClient(app)


def test_cloud_health_check() -> None:
    """Verifies that the /health endpoint responds with 200, healthy status, and version."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "InvoiceProcessingAutomationBot"
    assert "version" in data


def test_successful_excel_upload(temp_excel_builder) -> None:
    """Verifies successful multipart Excel file upload and processing."""
    sample_df = pd.DataFrame([
        {"Invoice ID": "INV-100", "Invoice Date": "2026-11-01", "Customer Name": "Acme Corp", "Amount": 500.00},
        {"Invoice ID": "INV-101", "Invoice Date": "2026-11-02", "Customer Name": "Globex", "Amount": -10.00},
    ])
    excel_path = temp_excel_builder(sample_df, "test_upload.xlsx")

    with open(excel_path, "rb") as f:
        response = client.post(
            "/upload",
            files={"file": ("test_upload.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "processing_id" in data
    assert data["total_invoices"] == 2
    assert data["valid_invoice_count"] == 1
    assert data["rejected_invoice_count"] == 1
    assert data["invalid_amount_count"] == 1
    assert "report_download_url" in data
    assert data["report_download_url"] == f"/download/{data['processing_id']}"


def test_upload_missing_file() -> None:
    """Verifies POST /upload with missing file payload returns 422 Unprocessable Entity."""
    response = client.post("/upload")
    assert response.status_code == 422


def test_upload_invalid_file_extension() -> None:
    """Verifies POST /upload with non-.xlsx extension returns 400 Bad Request."""
    fake_txt = io.BytesIO(b"invoice data here")
    response = client.post(
        "/upload",
        files={"file": ("invoices.txt", fake_txt, "text/plain")},
    )
    assert response.status_code == 400
    assert "Only Excel files (.xlsx) are supported" in response.json()["detail"]


def test_upload_empty_file() -> None:
    """Verifies POST /upload with zero-byte file returns 400 Bad Request."""
    empty_file = io.BytesIO(b"")
    response = client.post(
        "/upload",
        files={"file": ("empty.xlsx", empty_file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_upload_corrupted_excel_file() -> None:
    """Verifies POST /upload with invalid/corrupted zip header returns 400 Bad Request."""
    corrupted_data = io.BytesIO(b"THIS IS NOT A VALID PK ZIP ARCHIVE")
    response = client.post(
        "/upload",
        files={"file": ("corrupt.xlsx", corrupted_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 400
    assert "missing zip container header" in response.json()["detail"]


def test_upload_oversized_file() -> None:
    """Verifies POST /upload with file exceeding 10 MB returns 413 Payload Too Large."""
    # Create fake oversized content starting with PK zip header to reach size validation
    oversized_data = io.BytesIO(b"PK\x03\x04" + b"X" * (MAX_UPLOAD_SIZE + 2048))
    response = client.post(
        "/upload",
        files={"file": ("oversized.xlsx", oversized_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 413
    assert "maximum allowed limit" in response.json()["detail"]


def test_successful_report_download(temp_excel_builder) -> None:
    """Verifies downloading the generated Excel audit report via GET /download/{processing_id}."""
    sample_df = pd.DataFrame([
        {"Invoice ID": "INV-DL-1", "Invoice Date": "2026-11-01", "Customer Name": "DL Corp", "Amount": 1500.00},
    ])
    excel_path = temp_excel_builder(sample_df, "download_test.xlsx")

    # Step 1: Upload
    with open(excel_path, "rb") as f:
        upload_resp = client.post(
            "/upload",
            files={"file": ("download_test.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
    assert upload_resp.status_code == 200
    proc_id = upload_resp.json()["processing_id"]

    # Step 2: Download
    download_resp = client.get(f"/download/{proc_id}")
    assert download_resp.status_code == 200
    assert download_resp.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert len(download_resp.content) > 0
    # Must be valid zip bytes
    assert download_resp.content.startswith(b"PK\x03\x04")


def test_download_unknown_processing_id() -> None:
    """Verifies GET /download/{id} with unknown ID returns 404 Not Found."""
    fake_proc_id = "0123456789abcdef0123456789abcdef"
    response = client.get(f"/download/{fake_proc_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_download_path_traversal_prevention() -> None:
    """Verifies GET /download/{id} with path traversal characters returns 400 Bad Request."""
    response = client.get("/download/..%2F..%2Fetc%2Fpasswd")
    assert response.status_code in (400, 404)


def test_upload_missing_schema_column(temp_excel_builder) -> None:
    """Verifies uploading an Excel file missing required schema columns returns 400."""
    bad_df = pd.DataFrame([{"Invoice ID": "INV-100", "Customer Name": "No Amount Corp"}])
    excel_path = temp_excel_builder(bad_df, "missing_cols.xlsx")

    with open(excel_path, "rb") as f:
        response = client.post(
            "/upload",
            files={"file": ("missing_cols.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )

    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["error_type"] == "MissingColumnError"

