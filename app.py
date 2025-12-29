"""
Rockfon Inventory Reorder Alert Tool

A Streamlit web app that analyzes inventory levels and flags items
that need reordering based on stock coverage.
"""

import streamlit as st
import pandas as pd
from pathlib import Path

from core import (
    parse_excel,
    process_inventory,
    sort_items,
    filter_alerts,
    Urgency,
)
from core.calculator import count_by_urgency, to_dataframe, to_csv
from core.parser import get_parsing_issues

# Page configuration
st.set_page_config(
    page_title="Rockfon Inventory Alerts",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS for clean, modern look
st.markdown("""
<style>
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Header styling */
    .header-container {
        display: flex;
        align-items: center;
        gap: 24px;
        margin-bottom: 12px;
        padding: 8px 0;
    }

    .header-logo {
        flex-shrink: 0;
    }

    .header-title {
        font-size: 2.25rem;
        font-weight: 700;
        color: #212121;
        margin: 0;
        line-height: 1.2;
    }

    .header-subtitle {
        color: #666;
        font-size: 1rem;
        margin-top: 8px;
        margin-bottom: 16px;
    }

    /* Metric cards */
    [data-testid="stMetric"] {
        background-color: #f8f9fa;
        padding: 16px;
        border-radius: 8px;
    }

    /* Table styling */
    .stDataFrame {
        border-radius: 8px;
    }

    /* Upload hint styling */
    .upload-hint {
        text-align: center;
        color: #888;
        padding: 16px 0;
        margin-top: -8px;
    }

    .upload-hint .arrow {
        font-size: 1.5rem;
        display: block;
        margin-bottom: 4px;
        animation: bounce 1.5s ease infinite;
    }

    @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-6px); }
    }

    .upload-hint .hint-text {
        font-size: 0.9rem;
    }


    /* Footnotes styling */
    .footnotes {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 16px 20px;
        margin-top: 24px;
        font-size: 0.85rem;
        color: #555;
    }

    .footnotes h4 {
        margin: 0 0 12px 0;
        font-size: 0.95rem;
        color: #333;
    }

    .footnotes ul {
        margin: 0;
        padding-left: 20px;
    }

    .footnotes li {
        margin-bottom: 6px;
    }

    .footnotes code {
        background-color: #e9ecef;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)


def load_logo() -> str | None:
    """Load the Rockfon logo SVG."""
    logo_path = Path(__file__).parent / "assets" / "rockfon_logo.svg"
    if logo_path.exists():
        return logo_path.read_text()
    return None


def render_header():
    """Render the page header with logo."""
    logo_svg = load_logo()

    if logo_svg:
        # Scale up the logo
        scaled_svg = logo_svg.replace('width="127"', 'width="200"').replace('height="30"', 'height="48"')
        header_html = f"""
        <div class="header-container">
            <div class="header-logo">{scaled_svg}</div>
            <h1 class="header-title">Inventory Reorder Alerts</h1>
        </div>
        """
        st.markdown(header_html, unsafe_allow_html=True)
    else:
        st.title("Inventory Reorder Alerts")

    st.markdown('<p class="header-subtitle">Upload your weekly inventory export to identify items that need attention.</p>', unsafe_allow_html=True)
    st.divider()


def render_metrics(counts: dict, total_skus: int):
    """Render the summary metrics row."""
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            label="🔴 Critical",
            value=counts.get(Urgency.CRITICAL, 0),
            help="Out of stock with active demand"
        )
    with col2:
        st.metric(
            label="🟠 Urgent",
            value=counts.get(Urgency.URGENT, 0),
            help="Less than 1 month of stock"
        )
    with col3:
        st.metric(
            label="🟡 Warning",
            value=counts.get(Urgency.WARNING, 0),
            help="Less than 2 months of stock"
        )
    with col4:
        st.metric(
            label="🟢 OK",
            value=counts.get(Urgency.OK, 0),
            help="2+ months of stock"
        )
    with col5:
        st.metric(
            label="📦 Total SKUs",
            value=total_skus,
            help="Total active SKUs with demand"
        )


def render_filters(categories: list) -> tuple:
    """Render filter controls and return filter values."""
    with st.expander("Filters", expanded=False):
        col1, col2 = st.columns([3, 1])

        with col1:
            selected_categories = st.multiselect(
                "Categories",
                options=sorted(categories),
                default=sorted(categories),
                help="Filter by product category"
            )

        with col2:
            show_ok = st.checkbox(
                "Show OK items",
                value=False,
                help="Include items with sufficient stock"
            )

    return selected_categories, show_ok


def render_alerts_table(items: list, selected_categories: list, show_ok: bool):
    """Render the main alerts table."""
    # Filter items
    filtered = [i for i in items if i.category in selected_categories]
    if not show_ok:
        filtered = [i for i in filtered if i.urgency != Urgency.OK]

    if not filtered:
        st.info("No items match the current filters.")
        return filtered

    # Convert to DataFrame for display
    df = to_dataframe(filtered)

    # Configure columns
    column_config = {
        "Status": st.column_config.TextColumn("", width="small"),
        "Product": st.column_config.TextColumn("Product", width="large"),
        "SKU": st.column_config.TextColumn("SKU", width="medium"),
        "Category": st.column_config.TextColumn("Category", width="small"),
        "On Hand": st.column_config.NumberColumn("QOH", format="%d", width="small"),
        "Monthly Use": st.column_config.NumberColumn("Monthly Use", format="%.1f", width="small"),
        "Months Left": st.column_config.TextColumn("Months Left", width="small"),
        "Suggested Order": st.column_config.NumberColumn("Order Qty", format="%d", width="small"),
    }

    st.dataframe(
        df,
        column_config=column_config,
        hide_index=True,
        use_container_width=True,
        height=min(len(df) * 35 + 38, 600),  # Dynamic height, max 600px
    )

    return filtered


def render_download(items: list):
    """Render the CSV download button (centered and prominent)."""
    if not items:
        return

    csv_data = to_csv(items)

    # Create dashed border box
    st.markdown("""
    <div style="
        border: 2px dashed #00638E;
        border-radius: 12px;
        padding: 44px;
        margin: -12px 0 -68px 0;
    "></div>
    """, unsafe_allow_html=True)

    # Button positioned to overlap into the box
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.download_button(
            label="⬇️ Download Report as CSV",
            data=csv_data,
            file_name="rockfon_reorder_alerts.csv",
            mime="text/csv",
            help="Download the current view as a CSV file",
            use_container_width=True,
        )


def render_footnotes():
    """Render explanatory footnotes about calculations."""
    st.markdown("""
    <div class="footnotes">
        <h4>📋 How This Report Works</h4>
        <ul>
            <li><strong>Months of Stock</strong> = <code>Quantity on Hand / Monthly Average Usage</code></li>
            <li><strong>Suggested Order Qty</strong> = Quantity needed to reach 3 months of stock: <code>(3 × Monthly Avg) - QOH</code></li>
            <li><strong>Critical</strong>: Out of stock (QOH = 0) but has active demand — orders are being lost now</li>
            <li><strong>Urgent</strong>: Less than 1 month of stock remaining — will run out soon</li>
            <li><strong>Warning</strong>: 1-2 months of stock remaining — plan to reorder</li>
            <li><strong>OK</strong>: 2+ months of stock — sufficient inventory</li>
            <li>Items with zero monthly demand are excluded (discontinued or inactive SKUs)</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)


def main():
    """Main application entry point."""
    render_header()

    # File upload
    uploaded_file = st.file_uploader(
        "Drop your Excel file here",
        type=["xlsx", "xls"],
        help="Upload the weekly Rockfon Inventory Reorder Report",
        label_visibility="collapsed"
    )

    if not uploaded_file:
        # Show hint pointing UP to the file uploader
        st.markdown("""
        <div class="upload-hint">
            <span class="arrow">☝️</span>
            <span class="hint-text">Upload your Rockfon Inventory Excel file above to get started</span>
        </div>
        """, unsafe_allow_html=True)
        return

    # Process the uploaded file
    with st.spinner("Analyzing inventory..."):
        try:
            df, stats = parse_excel(uploaded_file)

            if df.empty:
                st.error("Could not find any inventory data in the uploaded file.")
                st.info("Make sure you're uploading the correct Rockfon inventory report.")
                return

            # Show any parsing issues as warnings
            issues = get_parsing_issues(df)
            if issues:
                with st.expander("⚠️ Data quality notes", expanded=False):
                    for issue in issues:
                        st.warning(issue)

            # Process inventory items
            items = process_inventory(df)
            items = sort_items(items)

            if not items:
                st.warning("No items with active demand found in the inventory.")
                return

        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.info("Please ensure you're uploading a valid Rockfon inventory Excel file.")
            return

    # Get unique categories
    categories = list(set(item.category for item in items))

    # Render summary metrics (with total SKUs count)
    counts = count_by_urgency(items)
    total_skus = len(items)
    render_metrics(counts, total_skus)

    st.divider()

    # Render filters
    selected_categories, show_ok = render_filters(categories)

    # Count items requiring attention
    alert_items = filter_alerts(items)
    st.subheader(f"Items Requiring Attention ({len(alert_items)})")

    # Render table
    filtered_items = render_alerts_table(items, selected_categories, show_ok)

    # Render download button
    st.divider()
    render_download(filtered_items)

    # Divider before footer sections
    st.divider()

    # Stats footer
    with st.expander("📊 Import Statistics", expanded=False):
        st.write("Items imported by category:")
        for sheet, count in sorted(stats.items()):
            st.write(f"- **{sheet}**: {count} items")

    # Explanatory footnotes
    render_footnotes()


if __name__ == "__main__":
    main()
