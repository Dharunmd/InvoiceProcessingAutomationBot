"""Unit and integration tests for FastAPI REST endpoint (/process)."""

from pathlib import Path
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api import app

client = TestClient(app)


def test_health_check() -> None:
    """Verifies that the /health endpoint responds with 200 and healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "InvoiceProcessingAutomationBot"


def test_process_default_payload() -> None:
    """Verifies POST /process with default body executes successfully."""
    response = client.post("/process", json={})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "execution_status" in data
    assert data["total_records"] > 0
    assert "valid_count" in data
    assert "rejected_count" in data
    assert "output_file_path" in data
    assert Path(data["output_file_path"]).exists()


def test_process_custom_paths(temp_excel_builder, tmp_path: Path) -> None:
    """Verifies POST /process with custom input and output file paths."""
    invoices = pd.DataFrame([
        {"Invoice ID": "INV-API-1", "Invoice Date": "2026-11-01", "Customer Name": "Corp A", "Amount": 100.0},
        {"Invoice ID": "INV-API-2", "Invoice Date": "2026-11-02", "Customer Name": "Corp B", "Amount": -50.0},
    ])
    input_file = temp_excel_builder(invoices, "api_input.xlsx")
    output_file = tmp_path / "api_report.xlsx"

    response = client.post(
        "/process",
        json={"input_path": str(input_file), "output_path": str(output_file)},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["total_records"] == 2
    assert data["valid_count"] == 1
    assert data["rejected_count"] == 1
    assert data["output_file_path"] == str(output_file)
    assert output_file.exists()


def test_process_input_file_not_found(tmp_path: Path) -> None:
    """Verifies POST /process with non-existent file returns 404."""
    non_existent = tmp_path / "does_not_exist.xlsx"
    response = client.post("/process", json={"input_path": str(non_existent)})
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error_type"] == "InputFileNotFoundError"


def test_process_corrupted_file(tmp_path: Path) -> None:
    """Verifies POST /process with corrupted file returns 400."""
    corrupted_file = tmp_path / "corrupted.xlsx"
    corrupted_file.write_text("Not a valid excel zip binary")

    response = client.post("/process", json={"input_path": str(corrupted_file)})
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["error_type"] == "CorruptedExcelError"


def test_process_missing_column(temp_excel_builder, tmp_path: Path) -> None:
    """Verifies POST /process with missing required column returns 400."""
    invalid_schema = pd.DataFrame([
        {"Invoice ID": "INV-101", "Invoice Date": "2026-11-01"}  # Missing Customer Name & Amount
    ])
    bad_file = temp_excel_builder(invalid_schema, "bad_schema.xlsx")
    response = client.post("/process", json={"input_path": str(bad_file)})
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["error_type"] == "MissingColumnError"
