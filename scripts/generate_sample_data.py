from pathlib import Path
import sys

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import pandas as pd
from src.config import INPUT_DIR


def create_sample_excel(target_path: Path | str | None = None) -> Path:
    """Creates a sample Excel file containing a mixture of valid and invalid invoice records.

    Includes:
    - Valid invoices
    - Missing Invoice IDs (NaN, empty string, whitespace)
    - Duplicate Invoice IDs (multiple occurrences - all should be rejected)
    - Non-positive amounts (negative numbers, zero)
    - Non-numeric amounts ('PENDING', 'N/A')
    - Records with multiple simultaneous errors
    """
    if target_path is None:
        target_path = INPUT_DIR / "sample_invoices.xlsx"

    target_path = Path(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    records = [
        # Valid Invoices
        {
            "Invoice ID": "INV-2024-001",
            "Invoice Date": "2024-04-01",
            "Customer Name": "Acme Technologies Inc.",
            "Amount": 1540.50,
        },
        {
            "Invoice ID": "INV-2024-002",
            "Invoice Date": "2024-04-02",
            "Customer Name": "Global Logistics LLC",
            "Amount": 2890.00,
        },
        {
            "Invoice ID": "INV-2024-003",
            "Invoice Date": "2024-04-03",
            "Customer Name": "Starlight Retailers",
            "Amount": 475.25,
        },
        {
            "Invoice ID": "INV-2024-004",
            "Invoice Date": "2024-04-04",
            "Customer Name": "Nexus Dynamics",
            "Amount": 8200.00,
        },
        {
            "Invoice ID": "INV-2024-005",
            "Invoice Date": "2024-04-05",
            "Customer Name": "Horizon Media Group",
            "Amount": 950.00,
        },

        # Duplicate ID Group 1: INV-2024-006 (Both occurrences must be rejected)
        {
            "Invoice ID": "INV-2024-006",
            "Invoice Date": "2024-04-06",
            "Customer Name": "Vanguard Solutions",
            "Amount": 1200.00,
        },
        {
            "Invoice ID": "INV-2024-006",
            "Invoice Date": "2024-04-06",
            "Customer Name": "Vanguard Solutions (Duplicate Submission)",
            "Amount": 1200.00,
        },

        # Duplicate ID Group 2: INV-2024-007 (Appears 3 times - all 3 must be rejected)
        {
            "Invoice ID": "INV-2024-007",
            "Invoice Date": "2024-04-07",
            "Customer Name": "Apex Systems",
            "Amount": 3400.00,
        },
        {
            "Invoice ID": "INV-2024-007",
            "Invoice Date": "2024-04-07",
            "Customer Name": "Apex Systems",
            "Amount": 3400.00,
        },
        {
            "Invoice ID": "INV-2024-007",
            "Invoice Date": "2024-04-07",
            "Customer Name": "Apex Systems Copy",
            "Amount": 3400.00,
        },

        # Missing Invoice IDs
        {
            "Invoice ID": None,
            "Invoice Date": "2024-04-08",
            "Customer Name": "Quantum Enterprises",
            "Amount": 550.00,
        },
        {
            "Invoice ID": "   ",
            "Invoice Date": "2024-04-09",
            "Customer Name": "Omni Corp",
            "Amount": 1900.00,
        },

        # Non-Positive Amounts
        {
            "Invoice ID": "INV-2024-008",
            "Invoice Date": "2024-04-10",
            "Customer Name": "BlueSky Consulting",
            "Amount": -450.00,
        },
        {
            "Invoice ID": "INV-2024-009",
            "Invoice Date": "2024-04-11",
            "Customer Name": "Pinnacle Financials",
            "Amount": 0.00,
        },

        # Non-Numeric Amounts
        {
            "Invoice ID": "INV-2024-010",
            "Invoice Date": "2024-04-12",
            "Customer Name": "Summit Partners",
            "Amount": "PENDING_REVIEW",
        },

        # Multi-Reason Failure (Duplicate ID AND Negative Amount)
        {
            "Invoice ID": "INV-2024-011",
            "Invoice Date": "2024-04-13",
            "Customer Name": "Catalyst Labs",
            "Amount": -800.00,
        },
        {
            "Invoice ID": "INV-2024-011",
            "Invoice Date": "2024-04-13",
            "Customer Name": "Catalyst Labs Duplicate",
            "Amount": 800.00,
        },

        # Multi-Reason Failure (Missing ID AND Non-numeric Amount)
        {
            "Invoice ID": "",
            "Invoice Date": "2024-04-14",
            "Customer Name": "Unknown Client",
            "Amount": "FREE_TRIAL",
        },
    ]

    df = pd.DataFrame(records)
    df.to_excel(target_path, index=False, engine="openpyxl")
    print(f"Generated sample Excel file with {len(records)} records at: {target_path}")
    return target_path


if __name__ == "__main__":
    create_sample_excel()
