"""Configuration constants and schema definitions for InvoiceProcessingAutomationBot."""

from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"

# Default File Paths
DEFAULT_INPUT_FILE = INPUT_DIR / "sample_invoices.xlsx"
DEFAULT_OUTPUT_FILE = OUTPUT_DIR / "invoice_processing_report.xlsx"
DEFAULT_LOG_FILE = LOGS_DIR / "processing.log"

# Column Schema Requirements
COL_INVOICE_ID = "Invoice ID"
COL_INVOICE_DATE = "Invoice Date"
COL_CUSTOMER_NAME = "Customer Name"
COL_AMOUNT = "Amount"

REQUIRED_COLUMNS = [
    COL_INVOICE_ID,
    COL_INVOICE_DATE,
    COL_CUSTOMER_NAME,
    COL_AMOUNT,
]

# Output Columns for Processed Data
COL_REJECTION_REASONS = "Rejection Reasons"
COL_IS_VALID = "Is_Valid"

# Rejection Reason Messages
REASON_MISSING_ID = "Missing or empty Invoice ID"
REASON_DUPLICATE_ID = "Duplicate Invoice ID (all occurrences rejected)"
REASON_INVALID_AMOUNT = "Amount must be a positive numeric value (> 0)"

# Execution Statuses
STATUS_SUCCESS = "SUCCESS"
STATUS_PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
STATUS_FAILED = "FAILED"
