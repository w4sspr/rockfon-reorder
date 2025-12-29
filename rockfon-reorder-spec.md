# Rockfon Sample Inventory Reorder Alert Tool — Prototype Spec

## Context

Rockfon USA sells ceiling products (acoustic tiles, metal ceilings, grid systems). They send free marketing samples to architects and designers — roughly 1,000 different SKUs.

They outsource sample fulfillment to a third-party company (ARC) who runs a warehouse and a web portal. Rockfon pays ~$27K/month for this service.

The problem: Rockfon has no real-time visibility into inventory. They receive a weekly Excel export showing stock levels, but nobody systematically analyzes it. As a result, they frequently run out of samples without warning, which means salespeople can't get samples to architects, and Rockfon loses sales.

## The Pain Points

1. **No proactive alerts**: They don't know something is low until it's already out
2. **Different products have different lead times**: Some items take days to replenish, others take 6+ weeks. A "low stock" warning means different things for different products.
3. **Manual process**: Someone would have to scan 600+ rows weekly to spot problems. Nobody does this consistently.
4. **Data exists but isn't actionable**: The Excel has everything needed (SKU, current stock, monthly usage) but no automation on top of it.

## The Goal

Build a prototype tool that:
1. Ingests their weekly Excel export
2. Calculates stock coverage (months of stock remaining) for each SKU
3. Flags items that need attention based on configurable thresholds
4. Outputs a prioritized, actionable list

This is a **free proof-of-concept** to demonstrate value. If they like it, there may be paid work later.

## Input: The Excel File

**File name pattern**: `Rockfon_Inventory_-_Reorder_Report_V8__MMYYYY.xlsx`

**Sheets** (each category of product is a separate sheet):
- Kits (~45 items)
- Kit Components (~110 items)
- ColorChip (~91 items)
- Fleece (~36 items)
- Tiles (~110 items)
- Metal (~185 items)
- Wood (~47 items)
- Marketing (~90 items)
- `FULL 4 LOOK UP KEEP` (lookup table, ~668 rows — can be used as master reference)
- `Componet Averages` (calculation sheet, can ignore)

**Column structure** (varies slightly by sheet, but core columns are):

| Column | Description |
|--------|-------------|
| Item | Internal item number |
| SKU | Product code (e.g., `SWT-Sonar-CDX-7.8`) |
| TYPE / Type | Category (Tile, Kit, Fleece, Colorchip, Metal, etc.) |
| Display As | Human-readable product name |
| QOH / Current QOH | Quantity on Hand (current stock) |
| Monthly Average | Average units shipped per month (based on historical data) |

**Note**: The Excel has messy headers — row 1 is often a title row, row 2 contains actual column headers. Some columns are unnamed. You'll need to handle this.

**The Wood sheet** has additional columns that other sheets don't:
- Lead Time in Mths
- Reorder Level  
- Max QTY (Max)
- Suggested Order Qty
- QTY on Order

These are mostly empty/zero but show the intended data model.

## Output Requirements

A prioritized alert list showing items that need attention, grouped by urgency:

### Urgency Levels

| Level | Criteria | Meaning |
|-------|----------|---------|
| 🔴 CRITICAL | QOH = 0 AND Monthly Average > 0 | Out of stock with active demand — losing orders NOW |
| 🟠 URGENT | Months of stock < 1 | Will run out within a month |
| 🟡 WARNING | Months of stock < 2 | Will run out within 2 months |
| 🟢 OK | Months of stock >= 2 | Sufficient stock |

**Months of stock** = QOH / Monthly Average

(In future versions, thresholds should be configurable per-category based on lead times. For prototype, use fixed thresholds above.)

### Output Should Show

For each flagged item:
- Product name (Display As)
- SKU
- Category (which sheet it came from)
- Current stock (QOH)
- Monthly usage (Monthly Average)
- Months of stock remaining (calculated)
- Suggested order quantity (to reach 3 months of stock)

### Output Should Be Sorted By
1. Urgency level (CRITICAL first)
2. Within each level: by monthly demand descending (highest-impact items first)

## Output Format

You decide what format makes most sense. Options to consider:

1. **Google Sheets**: They already use Excel, so Sheets is familiar. Could include conditional formatting, auto-calculations. Easy to share. But requires manual upload each week.

2. **HTML report**: A single HTML file they can open in browser. Looks professional, can have nice styling. But static — need to regenerate each time.

3. **Python script + output**: They run a script, it reads Excel, outputs a report (HTML, CSV, or terminal). More technical but more flexible.

4. **Simple web app**: Upload Excel, see dashboard. Most polished but more work.

5. **anything else you can think of if you consider is better**. Consider that they mostly use Windows machines with very wide screens (their work laptops, work monitors are a bit more normal in aspect ratio). 

For a free prototype, lean toward simplicity and "wow factor" — something that looks useful and professional with minimal friction to use. 


## Technical Notes

- potentially Python with pandas for Excel parsing unless you have a better, more modern, more efficient and reliable way of doing so.
- Handle the messy Excel structure (skip title rows, handle unnamed columns)
- Ignore items with Monthly Average = 0 (discontinued or not actively ordered), or look at it in its right context. 
- Ignore items with QOH = NaN or negative
- The "Suggested order qty" formula: `(3 * Monthly Average) - QOH` (to get to 3 months of stock). Don't suggest negative orders.

## Files Provided

The actual Excel file will be provided: `Rockfon_Inventory_-_Reorder_Report_V8__102025.xlsx`

## Success Criteria

The prototype is successful if:
1. It correctly parses the Excel and handles the messy structure
2. It identifies the out-of-stock and low-stock items accurately
3. The output is clear, professional-looking, minimal clutter, minimalistic, modern, and immediately actionable
4. It's easy for a non-technical person (the user's mum) to use or understand
