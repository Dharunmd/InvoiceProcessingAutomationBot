"""Custom exceptions for InvoiceProcessingAutomationBot.

Ensures clear classification of ingestion, validation, and pipeline failures.
"""


class InvoiceProcessingError(Exception):
    """Base exception for all invoice processing errors."""
    pass


class InputFileNotFoundError(InvoiceProcessingError):
    """Raised when the specified Excel input file does not exist."""
    pass


class CorruptedExcelError(InvoiceProcessingError):
    """Raised when an Excel file is corrupted, unreadable, or has an invalid format."""
    pass


class EmptyWorkbookError(InvoiceProcessingError):
    """Raised when the Excel workbook contains no data or empty sheets."""
    pass


class MissingColumnError(InvoiceProcessingError):
    """Raised when required schema columns are missing from the input Excel sheet."""
    pass
