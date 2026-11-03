"""Validation engine for InvoiceProcessingAutomationBot.

Implements all invoice validation rules, including detecting missing IDs,
rejecting ALL occurrences of duplicate IDs, and enforcing positive numeric amounts.
Captures all applicable rejection reasons per record.
"""

import logging
import pandas as pd

from src.config import (
    COL_AMOUNT,
    COL_INVOICE_ID,
    COL_IS_VALID,
    COL_REJECTION_REASONS,
    REASON_DUPLICATE_ID,
    REASON_INVALID_AMOUNT,
    REASON_MISSING_ID,
)

logger = logging.getLogger("InvoiceProcessingBot")


def validate_invoices(df: pd.DataFrame) -> pd.DataFrame:
    """Applies validation rules to the invoice DataFrame.

    Rules enforced:
    1. Invoice ID must not be null, empty, or whitespace-only.
    2. Every occurrence of a duplicate Invoice ID is rejected (keep=False).
    3. Invoice amount must be a strictly positive numeric value (> 0).

    Captures all applicable rejection reasons for every record.

    Args:
        df: Input DataFrame containing invoice records.

    Returns:
        A copy of the DataFrame with added 'Rejection Reasons' and 'Is_Valid' columns.
    """
    logger.info("Executing invoice validation rules...")
    validated_df = df.copy()

    # Track list of rejection reasons per row
    reasons_list: list[list[str]] = [[] for _ in range(len(validated_df))]

    # -------------------------------------------------------------
    # Rule 1: Missing or Empty Invoice ID
    # -------------------------------------------------------------
    raw_ids = validated_df[COL_INVOICE_ID]
    is_id_missing = (
        raw_ids.isna()
        | raw_ids.astype(str).str.strip().eq("")
        | raw_ids.astype(str).str.strip().str.lower().eq("nan")
        | raw_ids.astype(str).str.strip().str.lower().eq("none")
    )

    for idx, is_missing in enumerate(is_id_missing):
        if is_missing:
            reasons_list[idx].append(REASON_MISSING_ID)

    # -------------------------------------------------------------
    # Rule 2: Duplicate Invoice IDs (Reject ALL Occurrences)
    # -------------------------------------------------------------
    # Normalize ID strings for exact comparison
    normalized_ids = raw_ids.astype(str).str.strip()

    # Check duplicates only among records with non-missing IDs
    valid_id_mask = ~is_id_missing
    duplicate_mask = normalized_ids.duplicated(keep=False) & valid_id_mask

    for idx, is_duplicate in enumerate(duplicate_mask):
        if is_duplicate:
            reasons_list[idx].append(REASON_DUPLICATE_ID)

    # -------------------------------------------------------------
    # Rule 3: Positive Numeric Invoice Amount (> 0)
    # -------------------------------------------------------------
    numeric_amounts = pd.to_numeric(validated_df[COL_AMOUNT], errors="coerce")
    is_amount_invalid = numeric_amounts.isna() | (numeric_amounts <= 0)

    for idx, is_invalid in enumerate(is_amount_invalid):
        if is_invalid:
            reasons_list[idx].append(REASON_INVALID_AMOUNT)

    # -------------------------------------------------------------
    # Aggregate Reasons and Determine Validity
    # -------------------------------------------------------------
    combined_reasons = ["; ".join(reasons) for reasons in reasons_list]
    is_valid = [len(reasons) == 0 for reasons in reasons_list]

    validated_df[COL_REJECTION_REASONS] = combined_reasons
    validated_df[COL_IS_VALID] = is_valid

    # Assign parsed numeric amounts for valid numeric values without warning
    validated_df.loc[numeric_amounts.notna(), COL_AMOUNT] = numeric_amounts[numeric_amounts.notna()]

    valid_count = sum(is_valid)
    rejected_count = len(is_valid) - valid_count
    logger.info(
        f"Validation completed: {valid_count} valid records, {rejected_count} rejected records"
    )

    return validated_df
