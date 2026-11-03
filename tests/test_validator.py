"""Unit tests for src/validator.py verifying all validation rules."""

import pandas as pd

from src.config import (
    COL_IS_VALID,
    COL_REJECTION_REASONS,
    REASON_DUPLICATE_ID,
    REASON_INVALID_AMOUNT,
    REASON_MISSING_ID,
)
from src.validator import validate_invoices


def test_valid_invoices_pass(valid_invoice_df):
    """Verifies that clean invoice records pass validation without rejection reasons."""
    result = validate_invoices(valid_invoice_df)

    assert result[COL_IS_VALID].all()
    assert (result[COL_REJECTION_REASONS] == "").all()


def test_missing_invoice_id_detection(missing_id_df):
    """Verifies that null, empty string, whitespace, and 'nan' invoice IDs are flagged."""
    result = validate_invoices(missing_id_df)

    assert not result[COL_IS_VALID].any(), "All missing ID records should be invalid"
    for reason in result[COL_REJECTION_REASONS]:
        assert REASON_MISSING_ID in reason


def test_duplicate_invoice_id_rejects_all_occurrences(duplicate_invoice_df):
    """Verifies that every occurrence of a duplicated ID is rejected (keep=False)."""
    result = validate_invoices(duplicate_invoice_df)

    # In duplicate_invoice_df:
    # Rows 0, 1: INV-DUP-1 (2 occurrences) -> BOTH must be rejected
    # Rows 2, 3, 4: INV-DUP-2 (3 occurrences) -> ALL THREE must be rejected
    # Row 5: INV-UNIQUE -> Must be VALID

    assert not result.loc[0, COL_IS_VALID]
    assert REASON_DUPLICATE_ID in result.loc[0, COL_REJECTION_REASONS]

    assert not result.loc[1, COL_IS_VALID]
    assert REASON_DUPLICATE_ID in result.loc[1, COL_REJECTION_REASONS]

    assert not result.loc[2, COL_IS_VALID]
    assert not result.loc[3, COL_IS_VALID]
    assert not result.loc[4, COL_IS_VALID]
    assert REASON_DUPLICATE_ID in result.loc[2, COL_REJECTION_REASONS]
    assert REASON_DUPLICATE_ID in result.loc[3, COL_REJECTION_REASONS]
    assert REASON_DUPLICATE_ID in result.loc[4, COL_REJECTION_REASONS]

    # The unique record should remain valid
    assert result.loc[5, COL_IS_VALID]
    assert result.loc[5, COL_REJECTION_REASONS] == ""


def test_invalid_amount_validation(invalid_amount_df):
    """Verifies that negative numbers, zero, null, and non-numeric strings are flagged."""
    result = validate_invoices(invalid_amount_df)

    assert not result[COL_IS_VALID].any(), "All invalid amount records must be rejected"
    for reason in result[COL_REJECTION_REASONS]:
        assert REASON_INVALID_AMOUNT in reason


def test_multi_reason_capture(multi_error_df):
    """Verifies that ALL applicable rejection reasons are captured for each record."""
    result = validate_invoices(multi_error_df)

    # Row 0: Duplicate ID + Negative Amount
    row0_reasons = result.loc[0, COL_REJECTION_REASONS]
    assert REASON_DUPLICATE_ID in row0_reasons
    assert REASON_INVALID_AMOUNT in row0_reasons

    # Row 1: Duplicate ID + Non-numeric string amount
    row1_reasons = result.loc[1, COL_REJECTION_REASONS]
    assert REASON_DUPLICATE_ID in row1_reasons
    assert REASON_INVALID_AMOUNT in row1_reasons

    # Row 2: Missing ID + Negative Amount
    row2_reasons = result.loc[2, COL_REJECTION_REASONS]
    assert REASON_MISSING_ID in row2_reasons
    assert REASON_INVALID_AMOUNT in row2_reasons
