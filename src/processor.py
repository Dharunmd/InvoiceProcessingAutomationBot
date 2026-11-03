"""Workflow coordinator and separation engine for InvoiceProcessingAutomationBot.

Splits validated records into valid and rejected datasets, computes audit metrics,
and compiles execution statistics.
"""

from collections import Counter
from datetime import datetime, timezone
import logging
from typing import Any

import pandas as pd

from src.config import (
    COL_AMOUNT,
    COL_IS_VALID,
    COL_REJECTION_REASONS,
    STATUS_PARTIAL_SUCCESS,
    STATUS_SUCCESS,
)
from src.validator import validate_invoices

logger = logging.getLogger("InvoiceProcessingBot")


def process_invoices(
    raw_df: pd.DataFrame,
    start_time: datetime,
    input_file_path: str,
    output_file_path: str,
) -> dict[str, Any]:
    """Coordinates validation, separates datasets, and computes audit statistics.

    Args:
        raw_df: Raw ingested DataFrame.
        start_time: Datetime object indicating when processing commenced.
        input_file_path: Path to the input file.
        output_file_path: Target path for the output report.

    Returns:
        Dictionary containing:
        - 'valid_df': DataFrame of valid invoice records.
        - 'rejected_df': DataFrame of rejected invoice records with reasons.
        - 'audit_summary': Dictionary containing audit trail and KPI metrics.
    """
    logger.info("Starting processing pipeline and dataset separation...")

    # Run validation rules
    validated_df = validate_invoices(raw_df)

    # Separate valid vs rejected
    valid_mask = validated_df[COL_IS_VALID]

    # Valid invoices: remove internal validator columns
    valid_df = validated_df[valid_mask].drop(
        columns=[COL_REJECTION_REASONS, COL_IS_VALID]
    ).copy()

    # Rejected invoices: keep rejection reasons, drop internal is_valid flag
    rejected_df = validated_df[~valid_mask].drop(
        columns=[COL_IS_VALID]
    ).copy()

    # Calculate numeric totals
    valid_numeric_amounts = pd.to_numeric(valid_df[COL_AMOUNT], errors="coerce").fillna(0)
    valid_total_amount = float(valid_numeric_amounts.sum())

    rejected_numeric_amounts = pd.to_numeric(rejected_df[COL_AMOUNT], errors="coerce").fillna(0)
    rejected_total_amount = float(rejected_numeric_amounts.sum())

    # Count breakdown of individual rejection reasons
    reason_counter: Counter[str] = Counter()
    for reasons_str in rejected_df[COL_REJECTION_REASONS]:
        for reason in str(reasons_str).split("; "):
            if reason.strip():
                reason_counter[reason.strip()] += 1

    end_time = datetime.now(timezone.utc)
    duration_seconds = round((end_time - start_time).total_seconds(), 3)

    total_records = len(validated_df)
    valid_count = len(valid_df)
    rejected_count = len(rejected_df)

    # Determine execution status
    if rejected_count == 0:
        execution_status = STATUS_SUCCESS
    else:
        execution_status = STATUS_PARTIAL_SUCCESS

    audit_summary = {
        "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "duration_seconds": duration_seconds,
        "input_file": str(input_file_path),
        "output_file": str(output_file_path),
        "total_records": total_records,
        "valid_count": valid_count,
        "valid_total_amount": round(valid_total_amount, 2),
        "rejected_count": rejected_count,
        "rejected_total_amount": round(rejected_total_amount, 2),
        "rejection_breakdown": dict(reason_counter),
        "execution_status": execution_status,
    }

    logger.info(
        f"Processing completed in {duration_seconds}s. "
        f"Status: {execution_status}. "
        f"Valid: {valid_count} (${valid_total_amount:,.2f}), "
        f"Rejected: {rejected_count} (${rejected_total_amount:,.2f})"
    )

    return {
        "valid_df": valid_df,
        "rejected_df": rejected_df,
        "audit_summary": audit_summary,
    }
