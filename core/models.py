"""Data models for inventory items and urgency levels."""

from dataclasses import dataclass
from enum import Enum


class Urgency(Enum):
    """Stock urgency levels, ordered by severity."""
    CRITICAL = 1  # QOH=0 with active demand - losing orders NOW
    URGENT = 2    # <1 month of stock remaining
    WARNING = 3   # <2 months of stock remaining
    OK = 4        # >=2 months of stock - sufficient

    @property
    def emoji(self) -> str:
        return {
            Urgency.CRITICAL: "\U0001F534",  # Red circle
            Urgency.URGENT: "\U0001F7E0",    # Orange circle
            Urgency.WARNING: "\U0001F7E1",   # Yellow circle
            Urgency.OK: "\U0001F7E2",        # Green circle
        }[self]

    @property
    def label(self) -> str:
        return {
            Urgency.CRITICAL: "Critical",
            Urgency.URGENT: "Urgent",
            Urgency.WARNING: "Warning",
            Urgency.OK: "OK",
        }[self]


@dataclass
class InventoryItem:
    """Represents a single inventory item with calculated metrics."""
    item_id: str
    sku: str
    category: str
    display_name: str
    qoh: int
    monthly_average: float
    months_of_stock: float
    urgency: Urgency
    suggested_order_qty: int

    @property
    def status_display(self) -> str:
        """Emoji + label for display."""
        return f"{self.urgency.emoji} {self.urgency.label}"
