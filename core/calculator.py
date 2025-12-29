"""Business logic for stock calculations and urgency determination."""

import pandas as pd
from typing import List, Tuple, Optional
from .models import Urgency, InventoryItem


# Target months of stock for suggested orders
TARGET_MONTHS = 3


def calculate_urgency(qoh: float, monthly_avg: float) -> Tuple[Optional[Urgency], float]:
    """
    Determine urgency level based on stock metrics.

    Returns:
        Tuple of (Urgency level or None if no demand, months of stock)
    """
    # No demand = not tracked
    if monthly_avg <= 0:
        return None, float("inf")

    # Out of stock with active demand
    if qoh <= 0:
        return Urgency.CRITICAL, 0.0

    months = qoh / monthly_avg

    if months < 1:
        return Urgency.URGENT, months
    elif months < 2:
        return Urgency.WARNING, months
    else:
        return Urgency.OK, months


def calculate_suggested_order(qoh: float, monthly_avg: float, target_months: int = TARGET_MONTHS) -> int:
    """
    Calculate quantity to order to reach target months of stock.

    Formula: (target_months * monthly_avg) - qoh
    Never returns negative.
    """
    if monthly_avg <= 0:
        return 0

    needed = (target_months * monthly_avg) - qoh
    return max(0, int(needed))


def is_valid_row(row: pd.Series) -> bool:
    """Check if a row has valid data for processing."""
    # Check for missing values
    if pd.isna(row["qoh"]) or pd.isna(row["monthly_average"]):
        return False

    # Check for negative values
    if row["qoh"] < 0 or row["monthly_average"] < 0:
        return False

    # Check for #N/A strings (from broken Excel formulas)
    for col in ["sku", "display_name", "item_id"]:
        if str(row.get(col, "")).startswith("#"):
            return False

    return True


def process_inventory(df: pd.DataFrame) -> List[InventoryItem]:
    """
    Convert parsed DataFrame to list of InventoryItem objects.

    Filters out invalid rows and items with no demand.
    """
    items = []

    for _, row in df.iterrows():
        if not is_valid_row(row):
            continue

        qoh = float(row["qoh"])
        avg = float(row["monthly_average"])

        urgency, months = calculate_urgency(qoh, avg)

        # Skip items with no demand (urgency is None)
        if urgency is None:
            continue

        items.append(InventoryItem(
            item_id=str(row["item_id"]),
            sku=str(row["sku"]),
            category=str(row["category"]),
            display_name=str(row["display_name"]),
            qoh=int(qoh),
            monthly_average=avg,
            months_of_stock=months,
            urgency=urgency,
            suggested_order_qty=calculate_suggested_order(qoh, avg),
        ))

    return items


def sort_items(items: List[InventoryItem]) -> List[InventoryItem]:
    """
    Sort items by urgency (critical first), then by monthly demand (highest first).

    This prioritizes items that are both urgent AND high-impact.
    """
    return sorted(
        items,
        key=lambda x: (x.urgency.value, -x.monthly_average)
    )


def filter_alerts(items: List[InventoryItem], include_ok: bool = False) -> List[InventoryItem]:
    """
    Filter to items that need attention.

    By default, only returns CRITICAL, URGENT, and WARNING items.
    """
    if include_ok:
        return items
    return [i for i in items if i.urgency != Urgency.OK]


def count_by_urgency(items: List[InventoryItem]) -> dict:
    """Count items by urgency level."""
    counts = {u: 0 for u in Urgency}
    for item in items:
        counts[item.urgency] += 1
    return counts


def to_dataframe(items: List[InventoryItem]) -> pd.DataFrame:
    """Convert list of InventoryItems to a display DataFrame."""
    if not items:
        return pd.DataFrame()

    return pd.DataFrame([
        {
            "Status": item.urgency.emoji,
            "Product": item.display_name,
            "SKU": item.sku,
            "Category": item.category,
            "On Hand": item.qoh,
            "Monthly Use": round(item.monthly_average, 1),
            "Months Left": round(item.months_of_stock, 1) if item.months_of_stock < 100 else "-",
            "Suggested Order": item.suggested_order_qty,
        }
        for item in items
    ])


def to_csv(items: List[InventoryItem]) -> str:
    """Export items to CSV string for download."""
    df = pd.DataFrame([
        {
            "Urgency": item.urgency.label,
            "Product": item.display_name,
            "SKU": item.sku,
            "Category": item.category,
            "QOH": item.qoh,
            "Monthly Average": item.monthly_average,
            "Months of Stock": round(item.months_of_stock, 2) if item.months_of_stock < 100 else "",
            "Suggested Order Qty": item.suggested_order_qty,
        }
        for item in items
    ])
    return df.to_csv(index=False)
