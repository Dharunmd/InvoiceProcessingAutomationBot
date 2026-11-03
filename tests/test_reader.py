"""Unit and edge-case tests for src/reader.py."""

import hashlib
from pathlib import Path
import tempfile

import pandas as pd
import pytest

from src.exceptions import (
    CorruptedExcelError,
    EmptyWorkbookError,
    InputFileNotFoundError,
    MissingColumnError,
)
from src.reader import read_invoice_excel


def test_read_valid_excel(valid_invoice_df, temp_excel_builder):
    """Verifies standard ingestion of a valid Excel workbook."""
    filepath = temp_excel_builder(valid_invoice_df)
    df = read_invoice_excel(filepath)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    assert "Invoice ID" in df.columns
    assert "Amount" in df.columns


def test_input_file_not_found():
    """Verifies that InputFileNotFoundError is raised for non-existent files."""
    fake_path = Path("/tmp/non_existent_invoice_12345.xlsx")
    with pytest.raises(InputFileNotFoundError) as exc_info:
        read_invoice_excel(fake_path)
    assert "not found" in str(exc_info.value).lower()


def test_corrupted_excel_file():
    """Verifies that CorruptedExcelError is raised for non-Excel or corrupted files."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(b"NOT_A_VALID_EXCEL_ZIP_BINARY_DATA")
        corrupted_path = Path(tmp.name)

    try:
        with pytest.raises(CorruptedExcelError) as exc_info:
            read_invoice_excel(corrupted_path)
        assert "corrupted" in str(exc_info.value).lower()
    finally:
        corrupted_path.unlink(missing_ok=True)


def test_empty_workbook(temp_excel_builder):
    """Verifies that EmptyWorkbookError is raised when Excel has no data."""
    empty_df = pd.DataFrame()
    filepath = temp_excel_builder(empty_df)

    with pytest.raises(EmptyWorkbookError) as exc_info:
        read_invoice_excel(filepath)
    assert "no data rows" in str(exc_info.value).lower()


def test_missing_required_column(temp_excel_builder):
    """Verifies that MissingColumnError is raised when a required column is absent."""
    df_missing_amount = pd.DataFrame([
        {
            "Invoice ID": "INV-001",
            "Invoice Date": "2024-05-01",
            "Customer Name": "Acme Corp",
            # "Amount" is intentionally omitted
        }
    ])
    filepath = temp_excel_builder(df_missing_amount)

    with pytest.raises(MissingColumnError) as exc_info:
        read_invoice_excel(filepath)
    assert "Amount" in str(exc_info.value)


def test_column_header_whitespace_stripping(temp_excel_builder):
    """Verifies that leading/trailing whitespaces in column names are automatically stripped."""
    df_with_whitespace = pd.DataFrame([
        {
            "  Invoice ID  ": "INV-001",
            " Invoice Date": "2024-05-01",
            "Customer Name  ": "Acme Corp",
            " Amount ": 100.0,
        }
    ])
    filepath = temp_excel_builder(df_with_whitespace)
    df = read_invoice_excel(filepath)

    assert "Invoice ID" in df.columns
    assert "Invoice Date" in df.columns
    assert "Customer Name" in df.columns
    assert "Amount" in df.columns


def test_input_file_never_modified(valid_invoice_df, temp_excel_builder):
    """Verifies that the original input file checksum remains identical before and after reading."""
    filepath = temp_excel_builder(valid_invoice_df)

    with open(filepath, "rb") as f:
        hash_before = hashlib.sha256(f.read()).hexdigest()

    # Read multiple times
    _ = read_invoice_excel(filepath)
    _ = read_invoice_excel(filepath)

    with open(filepath, "rb") as f:
        hash_after = hashlib.sha256(f.read()).hexdigest()

    assert hash_before == hash_after, "Input file was modified during reading!"
