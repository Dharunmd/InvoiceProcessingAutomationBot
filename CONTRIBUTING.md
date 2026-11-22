# Contributing

Set up the virtual environment in the README and run `python -m pytest -q` from the repository root.

For a validation bug, include the smallest synthetic workbook or table that reproduces it, your Python version, the command or endpoint you used, and the expected and actual results. Replace customer details and invoice numbers with invented values. For identifiers, mention whether the Excel cell stores text or a number.

For a pull request, add a regression case alongside the affected reader, validator, processor, or API tests. Describe any change to rejection reasons, workbook columns, or API response fields so people maintaining UiPath workflows can assess compatibility.
