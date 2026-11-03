"""Main entrypoint for InvoiceProcessingAutomationBot.

Supports both:
1. CLI execution (for manual execution or UiPath 'Start Process' activity)
2. Direct Python invocation via `execute_process()` (for UiPath 'Python Scope' activity)
"""

import argparse
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys
from typing import Any

# Ensure project root is in sys.path for external execution (e.g. UiPath)
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (
    DEFAULT_INPUT_FILE,
    DEFAULT_LOG_FILE,
    DEFAULT_OUTPUT_FILE,
    STATUS_FAILED,
)
from src.exceptions import InvoiceProcessingError
from src.logger import setup_logger
from src.processor import process_invoices
from src.reader import read_invoice_excel
from src.reporter import generate_excel_report


def execute_process(
    input_path: str | Path | None = None,
    output_path: str | Path | None = None,
    log_path: str | Path | None = None,
) -> dict[str, Any]:
    """Callable entrypoint for UiPath Python Activity and automated workflows.

    Args:
        input_path: Path to the input Excel invoice file.
        output_path: Path where the output Excel report will be saved.
        log_path: Path for the execution log file.

    Returns:
        Dictionary containing execution status, record counts, and audit summary.
    """
    start_time = datetime.now(timezone.utc)

    # Resolve paths with defaults
    resolved_input = Path(input_path) if input_path else DEFAULT_INPUT_FILE
    resolved_output = Path(output_path) if output_path else DEFAULT_OUTPUT_FILE
    resolved_log = Path(log_path) if log_path else DEFAULT_LOG_FILE

    # Initialize logger
    logger = setup_logger(log_file=resolved_log)
    logger.info("=" * 60)
    logger.info("InvoiceProcessingAutomationBot execution started")
    logger.info(f"Input File:  {resolved_input}")
    logger.info(f"Output File: {resolved_output}")
    logger.info("=" * 60)

    try:
        # Step 1: Read Excel file (strictly read-only)
        raw_df = read_invoice_excel(resolved_input)

        # Step 2: Validate, separate datasets, and calculate audit statistics
        process_result = process_invoices(
            raw_df=raw_df,
            start_time=start_time,
            input_file_path=str(resolved_input),
            output_file_path=str(resolved_output),
        )

        valid_df = process_result["valid_df"]
        rejected_df = process_result["rejected_df"]
        audit_summary = process_result["audit_summary"]

        # Step 3: Generate Excel report with openpyxl
        generated_report = generate_excel_report(
            valid_df=valid_df,
            rejected_df=rejected_df,
            audit_summary=audit_summary,
            output_path=resolved_output,
        )

        audit_summary["generated_report_path"] = str(generated_report)
        audit_summary["success"] = True

        logger.info("=" * 60)
        logger.info(f"Job completed successfully. Report: {generated_report}")
        logger.info("=" * 60)
        return audit_summary

    except InvoiceProcessingError as exc:
        end_time = datetime.now(timezone.utc)
        duration_seconds = round((end_time - start_time).total_seconds(), 3)
        logger.error(f"Invoice Processing Failure: {exc}")

        failure_summary = {
            "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "duration_seconds": duration_seconds,
            "input_file": str(resolved_input),
            "output_file": str(resolved_output),
            "execution_status": STATUS_FAILED,
            "error_type": exc.__class__.__name__,
            "error_message": str(exc),
            "success": False,
        }
        return failure_summary

    except Exception as exc:
        end_time = datetime.now(timezone.utc)
        duration_seconds = round((end_time - start_time).total_seconds(), 3)
        logger.critical(f"Unhandled system error during execution: {exc}", exc_info=True)

        critical_summary = {
            "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "duration_seconds": duration_seconds,
            "input_file": str(resolved_input),
            "output_file": str(resolved_output),
            "execution_status": STATUS_FAILED,
            "error_type": "UnhandledException",
            "error_message": str(exc),
            "success": False,
        }
        return critical_summary


def _build_argument_parser() -> argparse.ArgumentParser:
    """Builds the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="InvoiceProcessingAutomationBot: Enterprise RPA for Excel Invoice Validation.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-i",
        "--input",
        dest="input_path",
        type=str,
        default=str(DEFAULT_INPUT_FILE),
        help="Path to the input Excel invoice workbook (.xlsx)",
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="output_path",
        type=str,
        default=str(DEFAULT_OUTPUT_FILE),
        help="Path for the generated multi-sheet Excel report (.xlsx)",
    )
    parser.add_argument(
        "-l",
        "--log",
        dest="log_path",
        type=str,
        default=str(DEFAULT_LOG_FILE),
        help="Path for the audit log file",
    )
    return parser


def main() -> None:
    """Main CLI handler with process exit codes for RPA engines."""
    parser = _build_argument_parser()
    args = parser.parse_args()

    result = execute_process(
        input_path=args.input_path,
        output_path=args.output_path,
        log_path=args.log_path,
    )

    # Print summary JSON to stdout for easy RPA parser capture
    print("\n--- EXECUTION RESULT SUMMARY ---")
    print(json.dumps(result, indent=2))

    # Determine exit code: 0 if job processed, 1 if fatal failure
    if result.get("success", False):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
