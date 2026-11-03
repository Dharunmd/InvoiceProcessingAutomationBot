"""Integration and pipeline tests for processor, reporter, and main execution."""

from datetime import datetime, timezone
from pathlib import Path
import tempfile

from openpyxl import load_workbook
import pandas as pd

from main import execute_process
from src.config import (
    STATUS_PARTIAL_SUCCESS,
    STATUS_SUCCESS,
)
from src.processor import process_invoices
from src.reporter import generate_excel_report


def test_process_invoices_separation(valid_invoice_df, duplicate_invoice_df):
    """Verifies that records are correctly separated into valid and rejected DataFrames."""
    combined_df = pd.concat([valid_invoice_df, duplicate_invoice_df], ignore_index=True)
    start_time = datetime.now(timezone.utc)

    result = process_invoices(
        raw_df=combined_df,
        start_time=start_time,
        input_file_path="mock_in.xlsx",
        output_file_path="mock_out.xlsx",
    )

    valid_df = result["valid_df"]
    rejected_df = result["rejected_df"]
    audit = result["audit_summary"]

    # In combined:
    # 3 valid from valid_invoice_df
    # 1 valid (INV-UNIQUE) from duplicate_invoice_df
    # 5 rejected (2 for INV-DUP-1, 3 for INV-DUP-2)
    assert len(valid_df) == 4
    assert len(rejected_df) == 5
    assert audit["total_records"] == 9
    assert audit["valid_count"] == 4
    assert audit["rejected_count"] == 5
    assert audit["execution_status"] == STATUS_PARTIAL_SUCCESS


def test_process_all_valid_status(valid_invoice_df):
    """Verifies that an all-valid batch results in STATUS_SUCCESS and empty rejected dataset."""
    start_time = datetime.now(timezone.utc)
    result = process_invoices(
        raw_df=valid_invoice_df,
        start_time=start_time,
        input_file_path="mock_in.xlsx",
        output_file_path="mock_out.xlsx",
    )

    assert result["audit_summary"]["execution_status"] == STATUS_SUCCESS
    assert len(result["rejected_df"]) == 0
    assert result["audit_summary"]["rejected_count"] == 0


def test_excel_report_generation(valid_invoice_df, duplicate_invoice_df):
    """Verifies that generate_excel_report produces a 3-sheet workbook with correct structures."""
    combined_df = pd.concat([valid_invoice_df, duplicate_invoice_df], ignore_index=True)
    start_time = datetime.now(timezone.utc)
    process_result = process_invoices(combined_df, start_time, "in.xlsx", "out.xlsx")

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        out_path = Path(tmp.name)

    try:
        report_path = generate_excel_report(
            valid_df=process_result["valid_df"],
            rejected_df=process_result["rejected_df"],
            audit_summary=process_result["audit_summary"],
            output_path=out_path,
        )

        assert report_path.exists()
        wb = load_workbook(report_path)
        sheet_names = wb.sheetnames

        assert "Audit Summary" in sheet_names
        assert "Valid Invoices" in sheet_names
        assert "Rejected Invoices" in sheet_names

        # Verify summary sheet content
        ws_sum = wb["Audit Summary"]
        assert ws_sum["A1"].value == "INVOICE PROCESSING AUTOMATION REPORT"

        # Verify valid invoices sheet has rows
        ws_valid = wb["Valid Invoices"]
        assert ws_valid.max_row == 5  # 1 header + 4 data rows

        # Verify rejected invoices sheet has rows
        ws_rejected = wb["Rejected Invoices"]
        assert ws_rejected.max_row == 6  # 1 header + 5 data rows

    finally:
        out_path.unlink(missing_ok=True)


def test_execute_process_end_to_end(temp_excel_builder):
    """Verifies end-to-end execution through main.execute_process()."""
    test_df = pd.DataFrame([
        {"Invoice ID": "INV-E2E-1", "Invoice Date": "2024-05-01", "Customer Name": "Good Corp", "Amount": 100.0},
        {"Invoice ID": "INV-E2E-2", "Invoice Date": "2024-05-02", "Customer Name": "Bad Corp", "Amount": -50.0},
    ])
    in_path = temp_excel_builder(test_df, "e2e_input.xlsx")

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_out:
        out_path = Path(tmp_out.name)

    try:
        result = execute_process(input_path=in_path, output_path=out_path)

        assert result["success"] is True
        assert result["total_records"] == 2
        assert result["valid_count"] == 1
        assert result["rejected_count"] == 1
        assert Path(result["generated_report_path"]).exists()

    finally:
        out_path.unlink(missing_ok=True)
