"""
My Basket Page - Shopping Cart Management.

This page displays the current shopping basket and allows users to view
their selected items, see totals, and manage the basket contents.
"""

import sys
from pathlib import Path

# Ensure the streamlit_app directory is in the Python path
streamlit_app_dir = Path(__file__).parent.parent
if str(streamlit_app_dir) not in sys.path:
    sys.path.insert(0, str(streamlit_app_dir))

import sys
from pathlib import Path

# Add project root to path to import app module
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pandas as pd
import streamlit as st

from streamlit_app.app import get_or_create_session_id
from utils.api_client import view_cart_backend, add_to_cart_backend, remove_from_cart_backend
from utils.ui_components import render_header

render_header("🧺 My Basket", "Review and adjust your planned groceries")

# Get session ID for cart operations (using shared helper from app.py)
session_id = get_or_create_session_id()

# Get cart from backend
cart_data = view_cart_backend(session_id)

if not cart_data or not cart_data.get("items"):
    # Empty cart state
    basket = []
    summary = {"count_items": 0, "total_price": 0.0, "unique_retailer_count": 0, "total_quantity": 0}
else:
    basket = cart_data["items"]
    summary = {
        "count_items": len(basket),
        "total_price": cart_data.get("total_price", 0.0),
        "unique_retailer_count": len(set(item.get("retailer", "") for item in basket)),
        "total_quantity": sum(item.get("quantity", 0) for item in basket)
    }

if not basket:
    # Empty basket state
    st.info("🛒 Your basket is empty. Add items from the Search & Compare page.")
    st.markdown("""
    **Get started:**
    1. Go to **Search & Compare** page
    2. Search for products you want
    3. Select items and add them to your basket
    """)
    
    if st.button("🔍 Go to Search & Compare", use_container_width=True):
        st.switch_page("pages/02_🛒_Search_and_Compare.py")

else:
    # Non-empty basket - show summary metrics
    st.subheader("📊 Basket Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Items", summary["count_items"])
    
    with col2:
        st.metric("Total Cost", f"€{summary['total_price']:.2f}")
    
    with col3:
        st.metric("Retailers", summary["unique_retailer_count"])
    
    with col4:
        st.metric("Total Quantity", summary["total_quantity"])
    
    # Show totals by retailer if available
    if cart_data and cart_data.get("total_by_retailer"):
        st.divider()
        st.subheader("💰 Cost by Retailer")
        retailer_totals = cart_data["total_by_retailer"]
        cols = st.columns(len(retailer_totals))
        for idx, (retailer, total) in enumerate(retailer_totals.items()):
            with cols[idx]:
                st.metric(retailer.upper(), f"€{total:.2f}")
    
    st.divider()
    
    # Basket items table
    st.subheader("📋 Basket Items")
    
    # Convert basket to DataFrame for display
    basket_df = pd.DataFrame(basket)
    
    # Ensure required columns exist and normalize price
    if "price_eur" not in basket_df.columns and "price" in basket_df.columns:
        basket_df["price_eur"] = basket_df["price"]
    elif "price" not in basket_df.columns and "price_eur" in basket_df.columns:
        basket_df["price"] = basket_df["price_eur"]
    
    # Add formatted columns for display
    display_df = basket_df.copy()
    
    # Format price columns
    if "price_eur" in display_df.columns:
        display_df["Price (each)"] = display_df["price_eur"].apply(
            lambda x: f"€{float(x):.2f}" if pd.notna(x) else "N/A"
        )
    elif "price" in display_df.columns:
        display_df["Price (each)"] = display_df["price"].apply(
            lambda x: f"€{float(x):.2f}" if pd.notna(x) else "N/A"
        )
    
    # Use line_total if available, otherwise calculate (price * quantity)
    if "line_total" in display_df.columns:
        display_df["Total"] = display_df["line_total"].apply(
            lambda x: f"€{float(x):.2f}" if pd.notna(x) else "N/A"
        )
    elif "price_eur" in display_df.columns and "quantity" in display_df.columns:
        display_df["Total"] = (
            display_df["price_eur"] * display_df["quantity"]
        ).apply(lambda x: f"€{float(x):.2f}")
    elif "price" in display_df.columns and "quantity" in display_df.columns:
        display_df["Total"] = (
            display_df["price"] * display_df["quantity"]
        ).apply(lambda x: f"€{float(x):.2f}")
    elif "price_eur" in display_df.columns:
        display_df["Total"] = display_df["price_eur"].apply(lambda x: f"€{float(x):.2f}")
    elif "price" in display_df.columns:
        display_df["Total"] = display_df["price"].apply(lambda x: f"€{float(x):.2f}")
    
    # Format health tags
    if "health_tag" in display_df.columns:
        def format_health_tag(tag):
            if tag == "healthy":
                return "🥦 Healthy"
            elif tag == "unhealthy":
                return "⚠️ Less healthy"
            elif tag == "neutral":
                return "⚪ Neutral"
            else:
                return "❔ Unknown"
        
        display_df["Health"] = display_df["health_tag"].apply(format_health_tag)
    
    # Create removal column for data editor
    display_df["remove"] = False
    
    # Select columns for display
    display_columns = []
    if "remove" in display_df.columns:
        display_columns.append("remove")
    if "name" in display_df.columns:
        display_columns.append("name")
    if "retailer" in display_df.columns:
        display_columns.append("retailer")
    if "Price (each)" in display_df.columns:
        display_columns.append("Price (each)")
    if "quantity" in display_df.columns:
        display_columns.append("quantity")
    if "Total" in display_df.columns:
        display_columns.append("Total")
    if "Health" in display_df.columns:
        display_columns.append("Health")
    
    # Display editable table with removal checkboxes
    edited_df = st.data_editor(
        display_df[display_columns],
        column_config={
            "remove": st.column_config.CheckboxColumn(
                "Remove",
                help="Check items to remove from basket",
                default=False,
                width="small"
            ),
            "name": st.column_config.TextColumn("Product Name", disabled=True),
            "retailer": st.column_config.TextColumn("Retailer", disabled=True),
            "Price (each)": st.column_config.TextColumn("Price", disabled=True),
            "quantity": st.column_config.NumberColumn(
                "Quantity",
                format="%d",
                disabled=True,  # TODO: Enable quantity editing in future
                help="Quantity (editing coming soon)"
            ),
            "Total": st.column_config.TextColumn("Total", disabled=True),
            "Health": st.column_config.TextColumn("Health", disabled=True),
        },
        use_container_width=True,
        hide_index=True,
        key="basket_editor"
    )
    
    # Handle removals
    items_to_remove = edited_df[edited_df["remove"] == True]
    
    if len(items_to_remove) > 0:
        st.divider()
        col1, col2 = st.columns([3, 1])
        with col1:
            remove_button = st.button(
                f"🗑️ Remove {len(items_to_remove)} Selected Item(s)",
                type="secondary",
                use_container_width=True
            )
        
        if remove_button:
            # Remove items via backend API
            removed_count = 0
            for idx in items_to_remove.index:
                item = basket[idx]
                retailer = item.get("retailer", "")
                product_id = item.get("product_id", "")
                quantity = item.get("quantity", 1)
                
                if retailer and product_id:
                    result = remove_from_cart_backend(
                        session_id=session_id,
                        retailer=retailer,
                        product_id=product_id,
                        qty=quantity  # Remove entire quantity
                    )
                    if result is not None:
                        removed_count += 1
            
            if removed_count > 0:
                st.success(f"✅ Removed {removed_count} item(s) from basket!")
            else:
                st.error("Failed to remove items. Please try again.")
            st.rerun()
    
    st.divider()
    
    # Basket actions
    st.subheader("⚙️ Basket Actions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ Clear Entire Basket", type="secondary", use_container_width=True):
            # Clear basket by removing all items
            cleared_count = 0
            for item in basket:
                retailer = item.get("retailer", "")
                product_id = item.get("product_id", "")
                quantity = item.get("quantity", 1)
                
                if retailer and product_id:
                    result = remove_from_cart_backend(
                        session_id=session_id,
                        retailer=retailer,
                        product_id=product_id,
                        qty=quantity  # Remove entire quantity
                    )
                    if result is not None:
                        cleared_count += 1
            
            if cleared_count > 0:
                st.success("✅ Basket cleared!")
            else:
                st.info("Basket was already empty.")
            st.rerun()
    
    with col2:
        if st.button("🔍 Add More Items", use_container_width=True):
            st.switch_page("pages/02_🛒_Search_and_Compare.py")
    
    st.divider()
    
    # Health and cost insights
    st.subheader("💡 Insights")
    
    # Calculate health breakdown
    healthy_count = sum(1 for item in basket if item.get("health_tag") == "healthy")
    unhealthy_count = sum(1 for item in basket if item.get("health_tag") == "unhealthy")
    neutral_count = summary["count_items"] - healthy_count - unhealthy_count
    
    if summary["count_items"] > 0:
        health_percentage = (healthy_count / summary["count_items"]) * 100
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Health Breakdown:**")
            if health_percentage >= 70:
                st.success(f"🎉 {health_percentage:.0f}% healthy items - great balance!")
            elif health_percentage >= 50:
                st.info(f"👍 {health_percentage:.0f}% healthy items - good start!")
            else:
                st.warning(f"💪 {health_percentage:.0f}% healthy items - consider adding more healthy options")
            
            st.caption(f"🥦 {healthy_count} healthy | ⚠️ {unhealthy_count} less healthy | ⚪ {neutral_count} neutral")
        
        with col2:
            st.markdown("**Cost Insights:**")
            avg_item_price = summary["total_price"] / summary["total_quantity"] if summary["total_quantity"] > 0 else 0
            st.caption(f"Average price per item: €{avg_item_price:.2f}")
            st.caption(f"Items from {summary['unique_retailer_count']} different retailer(s)")
    
    st.caption("💡 **Tip:** Small changes add up – try balancing cost and health for a sustainable shopping approach.")
    
    st.divider()
    
    # Future enhancements section
    st.caption("""
    **Planned features:**
    - ✅ Add/remove items (current)
    - 🔜 Edit quantities per item
    - 🔜 Weekly planner mode: assign items to specific days/meals
    - 🔜 Price optimization: suggest cheaper alternatives across retailers
    - 🔜 Health score tracking: see your basket's health score over time
    - 🔜 Swap suggestions: get healthier or cheaper alternatives
    - 🔜 Multi-retailer optimization: split basket across retailers for best price
    - 🔜 Export to shopping list
    - 🔜 Save/load basket presets
    """)
    
    # TODO: Future enhancements:
    #   - Quantity editing directly in the table
    #   - Weekly planner with drag-and-drop to days
    #   - Price optimization algorithm
    #   - Health swap suggestions
    #   - Integration with backend cart API (sync basket with server)
