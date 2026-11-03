"""Excel reporting module for InvoiceProcessingAutomationBot.

Builds a polished, multi-sheet Excel workbook using OpenPyXL with executive KPI
summaries, valid invoice tables, and rejected invoice tables with audit annotations.
Guarantees the input file is never touched.
"""

import logging
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
import pandas as pd

from src.config import COL_AMOUNT, COL_REJECTION_REASONS

logger = logging.getLogger("InvoiceProcessingBot")

# Color Palettes
NAVY_HEADER = "1B365D"
EMERALD_HEADER = "1E7E34"
CRIMSON_HEADER = "A71D2A"
LIGHT_GRAY_FILL = "F8F9FA"
ALERT_FILL = "FFEBEE"
BORDER_GRAY = "D1D5DB"


def _apply_border(cell) -> None:
    thin = Side(border_style="thin", color=BORDER_GRAY)
    cell.border = Border(top=thin, left=thin, right=thin, bottom=thin)


def _auto_adjust_column_widths(ws) -> None:
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            # Skip title banner rows that span across
            if cell.row in (1, 2) and ws.title == "Audit Summary":
                continue
            val_str = str(cell.value or "")
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 14)


def _build_summary_sheet(ws, audit_summary: dict[str, Any]) -> None:
    ws.title = "Audit Summary"
    ws.views.sheetView[0].showGridLines = True

    # Title Banner
    ws.merge_cells("A1:E1")
    title_cell = ws["A1"]
    title_cell.value = "INVOICE PROCESSING AUTOMATION REPORT"
    title_cell.font = Font(name="Calibri", size=16, bold=True, color="FFFFFF")
    title_cell.fill = PatternFill(start_color=NAVY_HEADER, end_color=NAVY_HEADER, fill_type="solid")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 40

    # Section 1: Execution Metadata
    ws["A3"] = "Audit Metadata"
    ws["A3"].font = Font(name="Calibri", size=12, bold=True, color=NAVY_HEADER)

    metadata_rows = [
        ("Execution Status", audit_summary["execution_status"]),
        ("Start Time", audit_summary["start_time"]),
        ("End Time", audit_summary["end_time"]),
        ("Duration (seconds)", audit_summary["duration_seconds"]),
        ("Input File Path", audit_summary["input_file"]),
        ("Output File Path", audit_summary["output_file"]),
    ]

    curr_row = 4
    for key, val in metadata_rows:
        ws.cell(row=curr_row, column=1, value=key).font = Font(name="Calibri", bold=True)
        ws.cell(row=curr_row, column=1).fill = PatternFill(start_color=LIGHT_GRAY_FILL, fill_type="solid")
        val_cell = ws.cell(row=curr_row, column=2, value=val)
        val_cell.font = Font(name="Calibri")
        if key == "Execution Status":
            status_color = "1E7E34" if val == "SUCCESS" else ("D97706" if val == "PARTIAL_SUCCESS" else "DC2626")
            val_cell.font = Font(name="Calibri", bold=True, color=status_color)
        _apply_border(ws.cell(row=curr_row, column=1))
        _apply_border(val_cell)
        curr_row += 1

    # Section 2: KPI Metrics Cards
    curr_row += 1
    ws.cell(row=curr_row, column=1, value="Processing Key Metrics").font = Font(
        name="Calibri", size=12, bold=True, color=NAVY_HEADER
    )
    curr_row += 1

    kpi_rows = [
        ("Total Records Processed", audit_summary["total_records"], ""),
        ("Valid Invoices Count", audit_summary["valid_count"], "Approved for ERP"),
        ("Valid Invoices Total Amount", f"${audit_summary['valid_total_amount']:,.2f}", "Total Approved Value"),
        ("Rejected Invoices Count", audit_summary["rejected_count"], "Requires Attention"),
        ("Rejected Invoices Total Amount", f"${audit_summary['rejected_total_amount']:,.2f}", "Total Rejected Value"),
    ]

    for metric, val, note in kpi_rows:
        m_cell = ws.cell(row=curr_row, column=1, value=metric)
        m_cell.font = Font(name="Calibri", bold=True)
        m_cell.fill = PatternFill(start_color=LIGHT_GRAY_FILL, fill_type="solid")

        v_cell = ws.cell(row=curr_row, column=2, value=val)
        v_cell.font = Font(name="Calibri", bold=True)
        v_cell.alignment = Alignment(horizontal="right")

        n_cell = ws.cell(row=curr_row, column=3, value=note)
        n_cell.font = Font(name="Calibri", italic=True, color="6B7280")

        _apply_border(m_cell)
        _apply_border(v_cell)
        _apply_border(n_cell)
        curr_row += 1

    # Section 3: Rejection Breakdown Table
    curr_row += 1
    ws.cell(row=curr_row, column=1, value="Rejection Reasons Breakdown").font = Font(
        name="Calibri", size=12, bold=True, color=CRIMSON_HEADER
    )
    curr_row += 1

    # Table Header
    th1 = ws.cell(row=curr_row, column=1, value="Rejection Reason")
    th2 = ws.cell(row=curr_row, column=2, value="Occurrences")
    for th in (th1, th2):
        th.font = Font(name="Calibri", bold=True, color="FFFFFF")
        th.fill = PatternFill(start_color=CRIMSON_HEADER, fill_type="solid")
        _apply_border(th)
    curr_row += 1

    breakdown = audit_summary.get("rejection_breakdown", {})
    if not breakdown:
        c1 = ws.cell(row=curr_row, column=1, value="None - 100% of records passed validation")
        c2 = ws.cell(row=curr_row, column=2, value=0)
        c1.font = Font(name="Calibri", italic=True)
        _apply_border(c1)
        _apply_border(c2)
    else:
        for reason, count in breakdown.items():
            r_cell = ws.cell(row=curr_row, column=1, value=reason)
            c_cell = ws.cell(row=curr_row, column=2, value=count)
            c_cell.alignment = Alignment(horizontal="right")
            _apply_border(r_cell)
            _apply_border(c_cell)
            curr_row += 1

    _auto_adjust_column_widths(ws)


def _build_data_sheet(
    ws,
    df: pd.DataFrame,
    title: str,
    header_color: str,
    highlight_rejection_col: bool = False,
) -> None:
    ws.title = title
    ws.views.sheetView[0].showGridLines = True

    if df.empty:
        ws.append(["No records available for this section."])
        ws["A1"].font = Font(name="Calibri", italic=True)
        return

    # Write Headers
    headers = list(df.columns)
    ws.append(headers)
    ws.row_dimensions[1].height = 26

    for col_idx, _ in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = Font(name="Calibri", bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color=header_color, fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        _apply_border(cell)

    # Write Rows
    for r_idx, row in df.iterrows():
        row_values = list(row)
        ws.append(row_values)
        curr_row = ws.max_row
        ws.row_dimensions[curr_row].height = 20

        for col_idx, col_name in enumerate(headers, start=1):
            cell = ws.cell(row=curr_row, column=col_idx)
            cell.font = Font(name="Calibri")
            _apply_border(cell)

            # Amount currency formatting
            if col_name == COL_AMOUNT:
                try:
                    num_val = float(cell.value)
                    cell.value = num_val
                    cell.number_format = '$#,##0.00'
                    cell.alignment = Alignment(horizontal="right")
                except (ValueError, TypeError):
                    cell.alignment = Alignment(horizontal="right")

            # Highlight Rejection Reasons Column
            if highlight_rejection_col and col_name == COL_REJECTION_REASONS:
                cell.fill = PatternFill(start_color=ALERT_FILL, fill_type="solid")
                cell.font = Font(name="Calibri", color=CRIMSON_HEADER, bold=True)

    _auto_adjust_column_widths(ws)


def generate_excel_report(
    valid_df: pd.DataFrame,
    rejected_df: pd.DataFrame,
    audit_summary: dict[str, Any],
    output_path: Path | str,
) -> Path:
    """Generates a professional 3-sheet Excel report without modifying the input file.

    Sheets:
    1. 'Audit Summary': Metadata, KPI cards, rejection reasons breakdown.
    2. 'Valid Invoices': Clean data ready for downstream ERP integration.
    3. 'Rejected Invoices': Problematic records with annotated rejection reasons.

    Args:
        valid_df: DataFrame of valid invoices.
        rejected_df: DataFrame of rejected invoices.
        audit_summary: Dictionary of run metadata.
        output_path: Target path to save the Excel file.

    Returns:
        Path object pointing to the generated report file.
    """
    logger.info(f"Generating Excel report at target path: {output_path}")
    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    wb = Workbook()

    # Sheet 1: Audit Summary
    ws_summary = wb.active
    _build_summary_sheet(ws_summary, audit_summary)

    # Sheet 2: Valid Invoices
    ws_valid = wb.create_sheet(title="Valid Invoices")
    _build_data_sheet(ws_valid, valid_df, "Valid Invoices", EMERALD_HEADER, highlight_rejection_col=False)

    # Sheet 3: Rejected Invoices
    ws_rejected = wb.create_sheet(title="Rejected Invoices")
    _build_data_sheet(ws_rejected, rejected_df, "Rejected Invoices", CRIMSON_HEADER, highlight_rejection_col=True)

    wb.save(target_path)
    logger.info(f"Successfully saved processing report to {target_path}")
    return target_path
