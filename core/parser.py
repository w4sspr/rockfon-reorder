"""Excel parsing logic for Rockfon inventory files."""

import pandas as pd
from typing import Tuple, Dict, List
import io

# Sheets to process (inventory data)
INVENTORY_SHEETS = [
    "Kits",
    "kit Components",
    "ColorChip",
    "Fleece",
    "Tiles",
    "Metal",
    "Wood",
    "Marketing",
]

# Sheets to ignore (lookup tables, calculations)
IGNORE_SHEETS = ["FULL 4 LOOK UP KEEP", "Componet Averages"]

# Column positions by sheet (0-indexed, accounting for empty column A)
# Format: {"qoh_col": index, "avg_col": index, "item_col": index, "sku_col": index, "display_col": index}
# Most sheets follow standard layout, Wood is different
STANDARD_COLUMNS = {
    "item": 1,      # Column B
    "sku": 2,       # Column C
    "type": 3,      # Column D
    "display": 4,   # Column E
    "qoh": 5,       # Column F
    "avg": 6,       # Column G
}

WOOD_COLUMNS = {
    "item": 1,      # Column B
    "sku": 2,       # Column C
    "type": 3,      # Column D
    "display": 4,   # Column E
    "avg": 6,       # Column G (Lead Time is F, so avg is G)
    "qoh": 7,       # Column H
}


def get_column_config(sheet_name: str) -> dict:
    """Get column configuration for a specific sheet."""
    if sheet_name == "Wood":
        return WOOD_COLUMNS
    return STANDARD_COLUMNS


def parse_sheet(xl: pd.ExcelFile, sheet_name: str) -> pd.DataFrame:
    """Parse a single inventory sheet."""
    config = get_column_config(sheet_name)

    # Read raw data, skipping the title row (row 0)
    # Header is on row 1 (0-indexed), data starts row 2
    df = pd.read_excel(
        xl,
        sheet_name=sheet_name,
        header=1,  # Row 2 in Excel (0-indexed row 1)
    )

    # Extract relevant columns by position (more reliable than column names)
    result = pd.DataFrame()

    try:
        result["item_id"] = df.iloc[:, config["item"]].astype(str)
        result["sku"] = df.iloc[:, config["sku"]].astype(str)
        result["display_name"] = df.iloc[:, config["display"]].astype(str)
        result["qoh"] = pd.to_numeric(df.iloc[:, config["qoh"]], errors="coerce")
        result["monthly_average"] = pd.to_numeric(df.iloc[:, config["avg"]], errors="coerce")
        result["category"] = sheet_name
    except IndexError:
        # Sheet doesn't have expected columns, return empty
        return pd.DataFrame()

    return result


def parse_excel(file: io.BytesIO | str) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """
    Parse the Rockfon inventory Excel file.

    Args:
        file: Either a file path string or BytesIO object from upload

    Returns:
        Tuple of (combined DataFrame, stats dict with row counts per sheet)
    """
    xl = pd.ExcelFile(file)

    all_data = []
    stats = {}

    for sheet_name in xl.sheet_names:
        if sheet_name in IGNORE_SHEETS:
            continue
        if sheet_name not in INVENTORY_SHEETS:
            continue

        df = parse_sheet(xl, sheet_name)

        if not df.empty:
            stats[sheet_name] = len(df)
            all_data.append(df)

    if not all_data:
        return pd.DataFrame(), stats

    combined = pd.concat(all_data, ignore_index=True)
    return combined, stats


def get_parsing_issues(df: pd.DataFrame) -> List[str]:
    """Identify data quality issues in parsed data."""
    issues = []

    # Count #N/A values (from broken Excel formulas)
    na_count = df.isin(["#N/A", "#REF!", "#VALUE!"]).sum().sum()
    if na_count > 0:
        issues.append(f"{na_count} cells contain Excel formula errors (#N/A, #REF!, etc.)")

    # Count missing QOH values
    missing_qoh = df["qoh"].isna().sum()
    if missing_qoh > 0:
        issues.append(f"{missing_qoh} items have missing QOH values")

    # Count missing monthly average
    missing_avg = df["monthly_average"].isna().sum()
    if missing_avg > 0:
        issues.append(f"{missing_avg} items have missing Monthly Average values")

    return issues
