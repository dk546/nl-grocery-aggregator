"""
Reusable UI Components Module.

This module contains all reusable UI components that can be used across different pages
of the Streamlit application. These components capture the "healthy lifestyle supermarket
compare" vibe and provide consistent visual language throughout the app.

Design principles:
- Use emojis sparingly but meaningfully
- Color coding for health status (green = healthy, orange/red = less healthy)
- Clear visual hierarchy with cards and metrics
- Responsive layouts using Streamlit columns

# TODO: Future enhancements:
    - Add interactive product cards with hover effects (if Streamlit supports)
    - Add "Add to basket" buttons directly in table rows
    - Add swap suggestions overlay (show cheaper/healthier alternatives)
    - Add sorting toggles directly in table headers
    - Add image carousel for product images
"""

from typing import List, Optional

import pandas as pd
import streamlit as st


def render_header(title: str, subtitle: Optional[str] = None, show_basket_link: bool = True) -> None:
    """
    Render a consistent page header with title, optional subtitle, and optional basket link.
    
    Args:
        title: Main page title (can include emoji)
        subtitle: Optional subtitle text displayed below title
        show_basket_link: If True, show a link to My Basket page in the header (default: True)
    """
    # Create columns for title area and actions
    if show_basket_link:
        col_title, col_actions = st.columns([3, 1])
        
        with col_title:
            st.title(title)
            if subtitle:
                st.caption(subtitle)
        
        with col_actions:
            # Use st.page_link if available (Streamlit >= 1.28.0), otherwise show info
            try:
                st.page_link(
                    "pages/03_🧺_My_Basket.py",
                    label="View My Basket",
                    icon="🧺",
                )
            except (AttributeError, TypeError):
                # Fallback for older Streamlit versions
                st.caption("🧺 Use sidebar to view My Basket")
    else:
        # No action column if basket link is disabled
        st.title(title)
        if subtitle:
            st.caption(subtitle)
    
    st.divider()


def render_backend_status(status: Optional[dict]) -> None:
    """
    Display backend connection status as a status pill.
    
    Args:
        status: Dictionary from get_health_status() or None if backend unreachable.
                Should contain a "status" key with value "ok" for online status.
                
    Shows:
        - 🟢 "Backend online" if status["status"] == "ok"
        - 🔴 "Backend offline / unreachable" if status is None
    """
    if status and status.get("status") == "ok":
        st.success("🟢 Backend online")
    else:
        st.error("🔴 Backend offline / unreachable")


def render_product_summary(df: pd.DataFrame) -> None:
    """
    Render high-level product search summary metrics.
    
    Args:
        df: DataFrame with columns: retailer, price_eur, and optionally others.
            Each row represents one product from search results.
            
    Displays:
        - Number of items found
        - Number of unique retailers
        - Min/Avg/Max price in euros
    """
    if df.empty:
        st.info("No products to summarize.")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Items Found", len(df))
    
    with col2:
        unique_retailers = df["retailer"].nunique() if "retailer" in df.columns else 0
        st.metric("Retailers", unique_retailers)
    
    with col3:
        if "price_eur" in df.columns:
            min_price = df["price_eur"].min()
            st.metric("Min Price", f"€{min_price:.2f}")
        else:
            st.metric("Min Price", "N/A")
    
    with col4:
        if "price_eur" in df.columns:
            max_price = df["price_eur"].max()
            st.metric("Max Price", f"€{max_price:.2f}")
        else:
            st.metric("Max Price", "N/A")
    
    # Show average price if we have price data
    if "price_eur" in df.columns and not df["price_eur"].empty:
        avg_price = df["price_eur"].mean()
        st.caption(f"Average price: €{avg_price:.2f}")


def health_tag_badge(tag: str | None) -> str:
    """
    Convert health tag to a display string with emoji.
    
    Args:
        tag: Health tag string - "healthy", "unhealthy", "neutral", or None
        
    Returns:
        Formatted string with emoji and text:
        - "healthy" → "🥦 Healthy"
        - "unhealthy" → "⚠️ Less healthy"
        - anything else / None → "❔ Unknown"
    """
    if not tag:
        return "❔ Unknown"
    
    tag_lower = tag.lower()
    
    if tag_lower == "healthy":
        return "🥦 Healthy"
    elif tag_lower == "unhealthy":
        return "⚠️ Less healthy"
    elif tag_lower == "neutral":
        return "⚪ Neutral"
    else:
        return "❔ Unknown"


def cheapest_icon(is_cheapest: Optional[bool]) -> str:
    """
    Return emoji icon for cheapest product indicator.
    
    Args:
        is_cheapest: Boolean indicating if this is the cheapest option
        
    Returns:
        "💰" if cheapest, empty string otherwise
    """
    return "💰" if is_cheapest else ""


def cheapest_badges(is_cheapest_total: bool = False, is_cheapest_per_unit: bool = False) -> str:
    """
    Return badge text for cheapest product indicators.
    
    Args:
        is_cheapest_total: Whether this has the lowest total price
        is_cheapest_per_unit: Whether this has the lowest price per unit
        
    Returns:
        Formatted string with badges:
        - "💰 Cheapest overall" if is_cheapest_total
        - "⚖️ Best per unit" if is_cheapest_per_unit
        - Combined badges if both are True
        - Empty string if neither
    """
    badges = []
    if is_cheapest_total:
        badges.append("💰 Cheapest overall")
    if is_cheapest_per_unit:
        badges.append("⚖️ Best per unit")
    return ", ".join(badges) if badges else ""


def render_product_table(df: pd.DataFrame, show_selection: bool = False) -> Optional[List[int]]:
    """
    Render a formatted product comparison table.
    
    Args:
        df: DataFrame with product data. Expected columns:
            - name: str (product name)
            - retailer: str (retailer identifier)
            - price_eur: float (price in euros) - will be mapped to "price"
            - price: float (alternative column name for price)
            - unit: str (optional, unit description)
            - unit_size: str (optional, size information)
            - unit_price: str (optional, formatted unit price)
            - health_tag: str (health category)
            - is_cheapest: bool (optional, whether this is cheapest option)
            - image_url: str (optional)
            - url: str (optional)
        show_selection: If True, enables row selection via st.dataframe selection
    
    Returns:
        List of selected row indices if show_selection=True, None otherwise.
        
    # NOTE: This table is designed to support future basket integration.
        When basket features are added, row selection can be used to add items
        to the shopping basket.
        
    # TODO: Add interactive features:
        - "Add to basket" button in each row
        - Click-through to product URL
        - Image preview on hover
        - Sort toggles in column headers
        - Filter chips for retailer/health
        - Advanced filtering by price range
    """
    if df.empty:
        st.info("No products found. Try adjusting your search filters.")
        return None if not show_selection else []
    
    # Prepare display dataframe with formatted columns
    display_df = df.copy()
    
    # Normalize price column name (backend returns price_eur, but we want "price")
    if "price_eur" in display_df.columns and "price" not in display_df.columns:
        display_df["price"] = display_df["price_eur"]
    
    # Ensure name column exists (it's critical)
    if "name" not in display_df.columns:
        st.error("Product data missing 'name' column.")
        return None
    
    # Add cheapest indicator column (legacy support)
    if "is_cheapest" in display_df.columns:
        display_df["💰"] = display_df["is_cheapest"].apply(cheapest_icon)
    else:
        display_df["💰"] = ""
    
    # Add new cheapest badges column (shows both total and per unit badges)
    # Always create the Badges column, checking for cheapest flags in various forms
    def get_best_deals_label(row):
        # Check for is_cheapest_total (new field) or fall back to is_cheapest (legacy)
        is_total = False
        if "is_cheapest_total" in row and pd.notna(row.get("is_cheapest_total")):
            is_total = bool(row["is_cheapest_total"])
        elif "is_cheapest" in row and pd.notna(row.get("is_cheapest")):
            # Fallback to legacy is_cheapest field
            is_total = bool(row["is_cheapest"])
        
        # Check for is_cheapest_per_unit
        is_unit = False
        if "is_cheapest_per_unit" in row and pd.notna(row.get("is_cheapest_per_unit")):
            is_unit = bool(row["is_cheapest_per_unit"])
        
        return cheapest_badges(is_cheapest_total=is_total, is_cheapest_per_unit=is_unit)
    
    display_df["Best Deals"] = display_df.apply(get_best_deals_label, axis=1)
    
    # Format health tags with badges
    if "health_tag" in display_df.columns:
        display_df["Health"] = display_df["health_tag"].apply(health_tag_badge)
    else:
        display_df["Health"] = "❔ Unknown"
    
    # Format price column - ensure we have a price to display
    if "price" in display_df.columns:
        display_df["Price"] = display_df["price"].apply(
            lambda x: f"€{float(x):.2f}" if pd.notna(x) else "N/A"
        )
    elif "price_eur" in display_df.columns:
        display_df["Price"] = display_df["price_eur"].apply(
            lambda x: f"€{float(x):.2f}" if pd.notna(x) else "N/A"
        )
    else:
        display_df["Price"] = "N/A"
    
    # Format unit information if available
    if "unit_size" in display_df.columns or "unit" in display_df.columns:
        unit_info = []
        for idx, row in display_df.iterrows():
            parts = []
            if pd.notna(row.get("unit_size")):
                parts.append(str(row["unit_size"]))
            if pd.notna(row.get("unit")):
                parts.append(str(row["unit"]))
            unit_info.append(" / ".join(parts) if parts else "")
        display_df["Unit"] = unit_info
    elif "unit_price" in display_df.columns:
        # Use unit_price if provided directly
        display_df["Unit"] = display_df["unit_price"].fillna("")
    else:
        display_df["Unit"] = ""
    
    # Select columns to display (in order)
    display_columns = []
    if "💰" in display_df.columns:
        display_columns.append("💰")
    display_columns.extend(["name", "retailer", "Price"])
    if "Unit" in display_df.columns:
        display_columns.append("Unit")
    if "Best Deals" in display_df.columns:
        display_columns.append("Best Deals")
    elif "Badges" in display_df.columns:  # Legacy support
        display_columns.append("Badges")
    if "Health" in display_df.columns:
        display_columns.append("Health")
    
    # Build column configuration for st.dataframe
    column_config = {}
    
    # Configure price column - right-aligned
    if "Price" in display_columns:
        column_config["Price"] = st.column_config.TextColumn(
            "Price",
            help="Price in euros (€)",
            width="small"
        )
    
    # Configure name column
    column_config["name"] = st.column_config.TextColumn(
        "Product Name",
        help="Product name from retailer"
    )
    
    # Configure retailer with badge styling
    column_config["retailer"] = st.column_config.TextColumn(
        "Retailer",
        help="Retailer: Albert Heijn, Jumbo, Picnic, or Dirk"
    )
    
    # Configure health column with color hints
    if "Health" in display_columns:
        column_config["Health"] = st.column_config.TextColumn(
            "Health Tag",
            help="Health category: Healthy, Less healthy, or Neutral"
        )
    
    # Configure cheapest indicator (legacy)
    if "💰" in display_columns:
        column_config["💰"] = st.column_config.TextColumn(
            "Cheapest",
            help="💰 indicates this is the cheapest option for this product"
        )
    
    # Configure Best Deals column
    if "Best Deals" in display_columns:
        column_config["Best Deals"] = st.column_config.TextColumn(
            "Best Deals",
            help="💰 Cheapest overall, ⚖️ Best per unit"
        )
    elif "Badges" in display_columns:  # Legacy support
        column_config["Badges"] = st.column_config.TextColumn(
            "Best Deals",
            help="💰 Cheapest total price | 📏 Best price per unit"
        )
    
    # Display dataframe
    if show_selection:
        # Enable selection mode
        selected_rows = st.dataframe(
            display_df[display_columns],
            column_config=column_config,
            width='stretch',
            on_select="rerun",
            selection_mode="multi-index" if len(display_df) > 0 else "single-row"
        )
        # Extract selected indices (this is a simplified version - Streamlit's API may vary)
        return selected_rows.selection.rows if hasattr(selected_rows, "selection") else []
    else:
        st.dataframe(
            display_df[display_columns],
            column_config=column_config,
            width='stretch',
            hide_index=True
        )
        return None


def render_feature_card(title: str, description: str, emoji: str = "📦") -> None:
    """
    Render a simple feature description card.
    
    Args:
        title: Card title
        description: Card description text
        emoji: Optional emoji to display (default: 📦)
    """
    with st.container():
        st.markdown(f"### {emoji} {title}")
        st.markdown(description)
        st.markdown("---")

