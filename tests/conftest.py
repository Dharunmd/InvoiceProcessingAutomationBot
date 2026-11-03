"""Pytest configuration and reusable fixtures for InvoiceProcessingAutomationBot."""

from collections.abc import Generator
from pathlib import Path
import tempfile

import pandas as pd
import pytest


@pytest.fixture
def valid_invoice_df() -> pd.DataFrame:
    """Fixture providing a DataFrame of valid invoice records."""
    return pd.DataFrame([
        {
            "Invoice ID": "INV-1001",
            "Invoice Date": "2024-05-01",
            "Customer Name": "Alpha Corp",
            "Amount": 1250.00,
        },
        {
            "Invoice ID": "INV-1002",
            "Invoice Date": "2024-05-02",
            "Customer Name": "Beta Ltd",
            "Amount": 3400.50,
        },
        {
            "Invoice ID": "INV-1003",
            "Invoice Date": "2024-05-03",
            "Customer Name": "Gamma Services",
            "Amount": 890.75,
        },
    ])


@pytest.fixture
def duplicate_invoice_df() -> pd.DataFrame:
    """Fixture providing a DataFrame with duplicate invoice IDs across multiple rows."""
    return pd.DataFrame([
        {
            "Invoice ID": "INV-DUP-1",
            "Invoice Date": "2024-05-01",
            "Customer Name": "First Corp",
            "Amount": 500.00,
        },
        {
            "Invoice ID": "INV-DUP-1",
            "Invoice Date": "2024-05-02",
            "Customer Name": "First Corp Copy",
            "Amount": 500.00,
        },
        {
            "Invoice ID": "INV-DUP-2",
            "Invoice Date": "2024-05-03",
            "Customer Name": "Second Corp A",
            "Amount": 750.00,
        },
        {
            "Invoice ID": "INV-DUP-2",
            "Invoice Date": "2024-05-04",
            "Customer Name": "Second Corp B",
            "Amount": 750.00,
        },
        {
            "Invoice ID": "INV-DUP-2",
            "Invoice Date": "2024-05-05",
            "Customer Name": "Second Corp C",
            "Amount": 750.00,
        },
        {
            "Invoice ID": "INV-UNIQUE",
            "Invoice Date": "2024-05-06",
            "Customer Name": "Unique Corp",
            "Amount": 1000.00,
        },
    ])


@pytest.fixture
def missing_id_df() -> pd.DataFrame:
    """Fixture providing a DataFrame with missing, null, and whitespace-only invoice IDs."""
    return pd.DataFrame([
        {
            "Invoice ID": None,
            "Invoice Date": "2024-05-01",
            "Customer Name": "Null ID Corp",
            "Amount": 100.00,
        },
        {
            "Invoice ID": "",
            "Invoice Date": "2024-05-02",
            "Customer Name": "Empty String Corp",
            "Amount": 200.00,
        },
        {
            "Invoice ID": "   ",
            "Invoice Date": "2024-05-03",
            "Customer Name": "Whitespace Corp",
            "Amount": 300.00,
        },
        {
            "Invoice ID": "nan",
            "Invoice Date": "2024-05-04",
            "Customer Name": "NaN String Corp",
            "Amount": 400.00,
        },
    ])


@pytest.fixture
def invalid_amount_df() -> pd.DataFrame:
    """Fixture providing a DataFrame with negative, zero, and non-numeric amounts."""
    return pd.DataFrame([
        {
            "Invoice ID": "INV-NEG",
            "Invoice Date": "2024-05-01",
            "Customer Name": "Negative Amount Corp",
            "Amount": -150.00,
        },
        {
            "Invoice ID": "INV-ZERO",
            "Invoice Date": "2024-05-02",
            "Customer Name": "Zero Amount Corp",
            "Amount": 0.00,
        },
        {
            "Invoice ID": "INV-STR",
            "Invoice Date": "2024-05-03",
            "Customer Name": "String Amount Corp",
            "Amount": "NOT_A_NUMBER",
        },
        {
            "Invoice ID": "INV-NULL",
            "Invoice Date": "2024-05-04",
            "Customer Name": "Null Amount Corp",
            "Amount": None,
        },
    ])


@pytest.fixture
def multi_error_df() -> pd.DataFrame:
    """Fixture providing records with multiple simultaneous validation violations."""
    return pd.DataFrame([
        {
            "Invoice ID": "INV-MULTI-1",
            "Invoice Date": "2024-05-01",
            "Customer Name": "Multi Error 1A",
            "Amount": -500.00,  # Duplicate ID + Negative Amount
        },
        {
            "Invoice ID": "INV-MULTI-1",
            "Invoice Date": "2024-05-01",
            "Customer Name": "Multi Error 1B",
            "Amount": "INVALID_TEXT",  # Duplicate ID + Non-numeric Amount
        },
        {
            "Invoice ID": "   ",
            "Invoice Date": "2024-05-02",
            "Customer Name": "Multi Error 2",
            "Amount": -100.00,  # Missing ID + Negative Amount
        },
    ])


@pytest.fixture
def temp_excel_builder() -> Generator:
    """Factory fixture to create temporary Excel files for testing."""
    created_files: list[Path] = []

    def _builder(df: pd.DataFrame, filename: str = "test.xlsx") -> Path:
        tmp_dir = Path(tempfile.mkdtemp())
        filepath = tmp_dir / filename
        df.to_excel(filepath, index=False, engine="openpyxl")
        created_files.append(filepath)
        return filepath

    yield _builder

    # Cleanup temporary files
    for file in created_files:
        if file.exists():
            file.unlink(missing_ok=True)
        if file.parent.exists():
            file.parent.rmdir()
