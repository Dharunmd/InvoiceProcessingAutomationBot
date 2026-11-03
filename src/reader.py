"""Excel reader module for InvoiceProcessingAutomationBot.

Safely ingests invoice data from Excel files in read-only mode, validating file
integrity, schema presence, and non-empty status without modifying source files.
"""

import logging
from pathlib import Path
from zipfile import BadZipFile

import pandas as pd
from openpyxl.utils.exceptions import InvalidFileException

from src.config import REQUIRED_COLUMNS
from src.exceptions import (
    CorruptedExcelError,
    EmptyWorkbookError,
    InputFileNotFoundError,
    MissingColumnError,
)

logger = logging.getLogger("InvoiceProcessingBot")


def read_invoice_excel(file_path: Path | str) -> pd.DataFrame:
    """Reads invoice data from an Excel workbook with validation checks.

    This function operates strictly in read-only mode, guaranteeing zero
    modifications to the source file.

    Args:
        file_path: Path to the input Excel file (.xlsx or .xls).

    Returns:
        pd.DataFrame containing the raw ingested data.

    Raises:
        InputFileNotFoundError: If the input file path does not exist.
        CorruptedExcelError: If the file is damaged, unreadable, or not a valid Excel file.
        EmptyWorkbookError: If the workbook contains no rows or only empty values.
        MissingColumnError: If one or more required columns are missing.
    """
    path = Path(file_path)

    logger.info(f"Checking input file existence: {path}")
    if not path.exists() or not path.is_file():
        err_msg = f"Input file not found at path: {path}"
        logger.error(err_msg)
        raise InputFileNotFoundError(err_msg)

    # Ingest data using pandas with openpyxl engine
    try:
        logger.info(f"Reading Excel file: {path} (read-only mode)")
        df = pd.read_excel(path, engine="openpyxl")
    except (BadZipFile, InvalidFileException, ValueError, OSError) as exc:
        err_msg = f"Excel file at {path} is corrupted or in an invalid format: {exc}"
        logger.error(err_msg)
        raise CorruptedExcelError(err_msg) from exc
    except Exception as exc:
        err_msg = f"Unexpected error reading Excel file at {path}: {exc}"
        logger.error(err_msg)
        raise CorruptedExcelError(err_msg) from exc

    # Check for empty dataframe
    if df.empty or df.dropna(how="all").empty:
        err_msg = f"Input workbook at {path} contains no data rows."
        logger.error(err_msg)
        raise EmptyWorkbookError(err_msg)

    # Normalize column names: strip whitespace
    df.columns = [str(col).strip() for col in df.columns]

    # Validate required columns
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        err_msg = (
            f"Input file is missing required column(s): {', '.join(missing_cols)}. "
            f"Expected schema: {REQUIRED_COLUMNS}"
        )
        logger.error(err_msg)
        raise MissingColumnError(err_msg)

    logger.info(f"Successfully read {len(df)} records from {path.name}")
    return df
