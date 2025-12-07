"""
Search and Compare Page - Core Product Search Functionality.

This is the main page for searching and comparing products across retailers.
Users can filter by retailer, sort by price/health/retailer, and filter by health tag.
Results are displayed in a clean comparison table with price and health information.
Users can select products and add them to their shopping basket.
"""

import sys
from pathlib import Path

# Ensure the streamlit_app directory is in the Python path
streamlit_app_dir = Path(__file__).parent.parent
if str(streamlit_app_dir) not in sys.path:
    sys.path.insert(0, str(streamlit_app_dir))

# Add project root to path to import api.config
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pandas as pd
import streamlit as st
from datetime import datetime

from utils.session import get_or_create_session_id
from utils.api_client import search_products, add_to_cart_backend, view_cart_backend, get_cart_summary, get_price_history
from utils.ui_components import (
    render_product_summary, render_basket_summary_chip
)
from utils.sponsored_data import get_sponsored_deals_for_search
from utils.retailers import RETAILER_OPTIONS, DEFAULT_RETAILERS, get_retailer_display_name
from ui.style import inject_global_css, section_header, pill_tag, image_card, render_footer

# Inject global CSS styling
inject_global_css()

# Page header
section_header(
    title="Search & compare groceries",
    eyebrow="COMPARE SUPERMARKETS",
    help_text="Search across Albert Heijn, Jumbo, Dirk and Picnic, then add the best options to your basket."
)

# Get session ID for cart operations (persists across page navigations)
session_id = get_or_create_session_id()

# Show basket summary chip if user has items in basket
cart_summary = get_cart_summary(session_id)
if cart_summary:
    render_basket_summary_chip(cart_summary)

# Define options mappings (needed both inside and outside form)
# Use centralized retailer configuration
retailer_options = RETAILER_OPTIONS

sort_options = {
    "Price (low to high)": "price_asc",
    "Price (high to low)": "price_desc",
    "Price per unit (low to high)": "price_per_unit_asc",
    "Price per unit (high to low)": "price_per_unit_desc",
    "Health (healthy first)": "health",
    "Retailer (alphabetical)": "retailer"
}

# Initialize form state from session_state (persists across page navigations)
if "search_query" not in st.session_state:
    st.session_state["search_query"] = ""
if "search_retailers" not in st.session_state:
    st.session_state["search_retailers"] = DEFAULT_RETAILERS  # Default: all
if "search_sort_by" not in st.session_state:
    st.session_state["search_sort_by"] = "Price (low to high)"
if "search_health_filter" not in st.session_state:
    st.session_state["search_health_filter"] = "all"
if "search_size" not in st.session_state:
    st.session_state["search_size"] = 20
if "search_page" not in st.session_state:
    st.session_state["search_page"] = 1

# Search form with all controls
with st.form("search_form", clear_on_submit=False):
    # First row: search input and action button
    top_col1, top_col2 = st.columns([3, 1], gap="medium")
    
    with top_col1:
        # Query input (required) - restore from session_state
        query = st.text_input(
            "What are you looking for?",
            value=st.session_state["search_query"],
            placeholder="e.g. volkoren pasta, havermout, kipfilet…",
            help="Enter product name or keywords in Dutch",
            key="search_query_input"
        )
    
    with top_col2:
        # Submit button
        submitted = st.form_submit_button("🔍 Search products", type="primary", width='stretch')
        st.caption("We'll fetch results from all selected retailers.")
    
    # Second row: filters
    filt_col1, filt_col2, filt_col3 = st.columns([2, 2, 1], gap="medium")
    
    with filt_col1:
        # Retailer selection with friendly labels - restore from session_state
        selected_retailer_labels = st.multiselect(
            "Retailers",
            options=list(retailer_options.keys()),
            default=st.session_state["search_retailers"],
            help="Select which retailers to search",
            key="search_retailers_input"
        )
        st.caption("Tip: start with all supermarkets, then narrow down if needed.")
        
        # Convert friendly labels to retailer codes
        retailers = [retailer_options[label] for label in selected_retailer_labels]
    
    with filt_col2:
        # Health filter - restore from session_state
        health_options = ["all", "healthy", "unhealthy"]
        health_index = 0
        if st.session_state["search_health_filter"] in health_options:
            health_index = health_options.index(st.session_state["search_health_filter"])
        
        health_filter_option = st.selectbox(
            "Health Filter",
            options=health_options,
            index=health_index,
            format_func=lambda x: {
                "all": "All Products",
                "healthy": "🥦 Healthy Only",
                "unhealthy": "⚠️ Less Healthy Only"
            }.get(x, x),
            help="Filter results by health category",
            key="search_health_filter_input"
        )
        st.caption("Health tags are approximate and meant as a gentle guide.")
        
        # Convert "all" to None for API (don't send health_filter param)
        health_filter = None if health_filter_option == "all" else health_filter_option
    
    with filt_col3:
        # Find index of saved sort_by value
        sort_index = 0
        if st.session_state["search_sort_by"] in sort_options.keys():
            sort_index = list(sort_options.keys()).index(st.session_state["search_sort_by"])
        
        sort_by_label = st.selectbox(
            "Sort By",
            options=list(sort_options.keys()),
            index=sort_index,
            help="How to sort the results",
            key="search_sort_by_input"
        )
        sort_by = sort_options[sort_by_label]
        
        # Pagination controls - restore from session_state
        size = st.number_input(
            "Results per Retailer",
            min_value=1,
            max_value=50,
            value=st.session_state["search_size"],
            help="Number of results per retailer (max 50)",
            key="search_size_input"
        )
        
        # Page input is 1-indexed for user, will convert to 0-indexed for API
        page_user = st.number_input(
            "Page",
            min_value=1,
            value=st.session_state["search_page"],
            help="Page number (starting from 1)",
            key="search_page_input"
        )
    
    # Update session_state when form is submitted (persists across navigation)
    if submitted:
        st.session_state["search_query"] = query
        st.session_state["search_retailers"] = selected_retailer_labels
        st.session_state["search_sort_by"] = sort_by_label
        st.session_state["search_health_filter"] = health_filter_option
        st.session_state["search_size"] = size
        st.session_state["search_page"] = page_user

# Check for existing results in session_state (persists after rerun)
has_stored_results = "search_results" in st.session_state and st.session_state["search_results"]

# Handle form submission (outside form context - variables from form are accessible)
if submitted:
    # Use values from session_state (which were just updated) to ensure consistency
    query = st.session_state.get("search_query", "")
    selected_retailer_labels = st.session_state.get("search_retailers", [])
    retailers = [retailer_options[label] for label in selected_retailer_labels]
    sort_by_label = st.session_state.get("search_sort_by", "Price (low to high)")
    sort_by = sort_options.get(sort_by_label, "price_asc")
    health_filter_option = st.session_state.get("search_health_filter", "all")
    health_filter = None if health_filter_option == "all" else health_filter_option
    size = st.session_state.get("search_size", 20)
    page_user = st.session_state.get("search_page", 1)
    
    # Validate query
    if not query or not query.strip():
        st.warning("⚠️ Please enter a search query.")
        # Clear stored results on validation error
        if "search_results" in st.session_state:
            del st.session_state["search_results"]
    elif not retailers:
        st.warning("⚠️ Please select at least one retailer.")
        # Clear stored results on validation error
        if "search_results" in st.session_state:
            del st.session_state["search_results"]
    else:
        # Convert page from 1-indexed (user) to 0-indexed (API)
        page = page_user - 1
        
        # Perform search
        with st.spinner(f"🔍 Searching for '{query.strip()}' across {len(retailers)} retailer(s)..."):
            results = search_products(
                query=query.strip(),
                retailers=retailers if retailers else None,
                sort_by=sort_by,
                health_filter=health_filter,
                size=size,
                page=page
            )
        
        # Handle search results
        if results is None:
            st.error("❌ Could not reach the backend. Please check your connection and try again.")
            # Clear stored results on error
            if "search_results" in st.session_state:
                del st.session_state["search_results"]
            if "search_connectors_status" in st.session_state:
                del st.session_state["search_connectors_status"]
        else:
            # Extract results and connector status
            products = results.get("results", [])
            connectors_status = results.get("connectors_status", {})
            
            # Store results in session_state so they persist after rerun
            st.session_state["search_results"] = products
            st.session_state["search_connectors_status"] = connectors_status

# Display results if we have them (either from current submission or stored in session_state)
if submitted or has_stored_results:
    # Always get results from session_state (updated by submitted block above or from previous session)
    # This ensures results persist after rerun (e.g., after adding items to basket)
    products = st.session_state.get("search_results", [])
    connectors_status = st.session_state.get("search_connectors_status", {})
    
    # Get query and retailers from session_state for display
    query = st.session_state.get("search_query", "")
    selected_retailer_labels = st.session_state.get("search_retailers", [])
    retailers = [retailer_options[label] for label in selected_retailer_labels] if selected_retailer_labels else []
    
    # --- Sponsored Deals section (Instacart-style monetization MVP) ---
    sponsored_deals = get_sponsored_deals_for_search(
        query=query,
        retailer_codes=retailers if retailers else None,
        max_deals=3,
    )
    
    if sponsored_deals:
        st.markdown("### ⭐ Sponsored deals")
        st.caption(
            "These offers are sponsored placements. In a real deployment, brands or retailers "
            "could promote specific products here."
        )
        
        # Render sponsored cards in columns
        cols = st.columns(len(sponsored_deals))
        for col, deal in zip(cols, sponsored_deals):
            with col:
                with st.container(border=True):
                    st.markdown("**⭐ Sponsored**")
                    st.markdown(f"**{deal.title}**")
                    st.markdown(f"**€{deal.price_eur:.2f}**")
                    st.caption(deal.promo_text)
                    
                    retailer_label = get_retailer_display_name(deal.retailer)
                    
                    st.caption(f"🛒 {retailer_label}")
                    
                    if deal.product_url:
                        st.link_button(
                            "View product",
                            url=deal.product_url,
                            width='stretch',
                        )
                    else:
                        st.button(
                            "View product",
                            disabled=True,
                            width='stretch',
                            key=f"sponsored_{deal.id}",
                        )
    
    # Check for problematic connectors (non-ok status for selected retailers)
    problematic = {}
    if connectors_status and retailers:
        problematic = {
            retailer: status_val
            for retailer, status_val in connectors_status.items()
            if retailer in retailers and status_val not in {"ok", "skipped"}
        }
    
    # Show warning if some connectors failed
    if problematic:
        msg_parts = []
        for retailer, status_val in problematic.items():
            retailer_name = get_retailer_display_name(retailer)
            if status_val == "auth_error":
                msg_parts.append(f"{retailer_name}: authentication problem")
            elif status_val == "disabled":
                msg_parts.append(f"{retailer_name}: not configured")
            else:
                msg_parts.append(f"{retailer_name}: temporarily unavailable")
        
        msg = "⚠️ Some retailers could not be queried: " + "; ".join(msg_parts) + ". Showing available results only."
        st.warning(msg)
    
    # Show products table if we have any results
    if not products or len(products) == 0:
        if problematic:
            st.warning(f"🔍 No products found for '{query}'. Some retailers may be temporarily unavailable (see above).")
        else:
            st.warning(
                "We didn't find matching products for this search across your selected retailers. "
                "Try a broader term, check spelling, or enable more supermarkets."
            )
    else:
        # Convert results to DataFrame
        df = pd.DataFrame(products)
        
        # Standardize column names to match what render_product_table expects
        # Backend returns: id, retailer, name, price_eur, unit, unit_size, health_tag, is_cheapest, etc.
        # Ensure we have the expected columns
        if "price_eur" in df.columns:
            df["price"] = df["price_eur"]
        
        # Results summary header with side image
        main_col, side_col = st.columns([2.2, 1], gap="large")
        
        with main_col:
            num_products = len(products)
            retailers_used = sorted(set(p.get("retailer", "") for p in products if p.get("retailer")))
            
            st.markdown("### Results")
            st.caption(f"Showing **{num_products}** products across **{len(retailers_used)}** retailer(s).")
            
            summary_cols = st.columns(3, gap="large")
        with summary_cols[0]:
            st.markdown("**💶 Cheapest overall**")
            st.caption("Look for the lowest total price per product.")
        with summary_cols[1]:
            st.markdown("**📏 Best per unit**")
            st.caption("Use unit price to compare different package sizes fairly.")
        with summary_cols[2]:
            st.markdown("**🥦 Health nudges**")
            st.caption("Health tags highlight better choices where available.")
        
        st.divider()
        
        # Display summary metrics
        st.subheader("📊 Summary")
        render_product_summary(df)
        
        # Display unified Product Comparison table with Add to Basket selection
        st.subheader("📋 Product Comparison")
        
        # Get current cart items from backend to show which are already added
        current_cart = view_cart_backend(session_id)
        basket_item_ids = set()
        if current_cart and current_cart.get("items"):
            basket_item_ids = {
                f"{item.get('retailer', '')}:{item.get('product_id', '')}"
                for item in current_cart["items"]
            }
        
        # Prepare unified DataFrame with all comparison columns + selection
        unified_df = df.copy()
        
        # Ensure product_id is in the DataFrame (for stable reference, will be hidden from display)
        # Do this BEFORE formatting retailer column, as we need original retailer code for product_id
        # Always format as "retailer:id" for consistency with basket_item_ids format
        if "product_id" not in unified_df.columns:
            if "id" in unified_df.columns and "retailer" in unified_df.columns:
                # Create product_id from retailer + id (using original retailer code)
                unified_df["product_id"] = unified_df.apply(
                    lambda row: f"{row.get('retailer', '')}:{row.get('id', '')}", 
                    axis=1
                )
            elif "id" in unified_df.columns:
                unified_df["product_id"] = unified_df["id"]
        
        # Format retailer column to use display names (for display only)
        if "retailer" in unified_df.columns:
            unified_df["retailer"] = unified_df["retailer"].apply(
                lambda r: get_retailer_display_name(r) if r else ""
            )
        
        # Add selection column (default: not selected)
        unified_df["add_to_basket"] = False
        
        # Add formatted columns for display (same as render_product_table logic)
        # Normalize price column
        if "price_eur" in unified_df.columns and "price" not in unified_df.columns:
            unified_df["price"] = unified_df["price_eur"]
        
        # Add cheapest indicator column (legacy support)
        if "is_cheapest" in unified_df.columns:
            unified_df["💰"] = unified_df["is_cheapest"].apply(
                lambda x: "💰" if x else ""
            )
        else:
            unified_df["💰"] = ""
        
        # Add Best Deals column
        def get_best_deals_label(row):
            is_total = False
            if "is_cheapest_total" in row and pd.notna(row.get("is_cheapest_total")):
                is_total = bool(row["is_cheapest_total"])
            elif "is_cheapest" in row and pd.notna(row.get("is_cheapest")):
                is_total = bool(row["is_cheapest"])
            
            is_unit = False
            if "is_cheapest_per_unit" in row and pd.notna(row.get("is_cheapest_per_unit")):
                is_unit = bool(row["is_cheapest_per_unit"])
            
            badges = []
            if is_total:
                badges.append("💰 Cheapest overall")
            if is_unit:
                badges.append("⚖️ Best per unit")
            return ", ".join(badges) if badges else ""
        
        unified_df["Best Deals"] = unified_df.apply(get_best_deals_label, axis=1)
        
        # Format health tags
        if "health_tag" in unified_df.columns:
            def format_health_tag(tag):
                if not tag:
                    return "❔ Unknown"
                tag_lower = str(tag).lower()
                if tag_lower == "healthy":
                    return "🥦 Healthy"
                elif tag_lower == "unhealthy":
                    return "⚠️ Less healthy"
                elif tag_lower == "neutral":
                    return "⚪ Neutral"
                else:
                    return "❔ Unknown"
            unified_df["Health"] = unified_df["health_tag"].apply(format_health_tag)
        else:
            unified_df["Health"] = "❔ Unknown"
        
        # Format price column
        if "price" in unified_df.columns:
            unified_df["Price"] = unified_df["price"].apply(
                lambda x: f"€{float(x):.2f}" if pd.notna(x) else "N/A"
            )
        elif "price_eur" in unified_df.columns:
            unified_df["Price"] = unified_df["price_eur"].apply(
                lambda x: f"€{float(x):.2f}" if pd.notna(x) else "N/A"
            )
        else:
            unified_df["Price"] = "N/A"
        
        # Format unit information
        if "unit_size" in unified_df.columns or "unit" in unified_df.columns:
            unit_info = []
            for idx, row in unified_df.iterrows():
                parts = []
                if pd.notna(row.get("unit_size")):
                    parts.append(str(row["unit_size"]))
                if pd.notna(row.get("unit")):
                    parts.append(str(row["unit"]))
                unit_info.append(" / ".join(parts) if parts else "")
            unified_df["Unit"] = unit_info
        else:
            unified_df["Unit"] = ""
        
        # Show info about already-added items
        # Note: product_id already contains original retailer code in format "retailer:id" or just "id"
        def is_in_basket(row):
            product_id = row.get("product_id") or row.get("id", "")
            # product_id is already in format "retailer:id" from when we created it (before formatting retailer column)
            if ":" in str(product_id):
                item_id = str(product_id)
            else:
                # If product_id doesn't have retailer prefix, get original retailer from original df
                idx = row.name if hasattr(row, 'name') else None
                if idx is not None and idx in df.index and "retailer" in df.columns:
                    original_retailer = df.loc[idx, "retailer"]
                    item_id = f"{original_retailer}:{product_id}" if original_retailer else str(product_id)
                else:
                    item_id = str(product_id)
            return item_id in basket_item_ids
        
        unified_df["in_basket"] = unified_df.apply(is_in_basket, axis=1)
        already_added_count = unified_df["in_basket"].sum()
        if already_added_count > 0:
            st.info(f"ℹ️ {already_added_count} item(s) are already in your basket.")
        
        # Add Status column to show which items are already in basket
        unified_df["Status"] = unified_df["in_basket"].apply(lambda x: "✅ In basket" if x else "")
        
        # Define column order for display (product_id will be hidden)
        display_columns = []
        if "💰" in unified_df.columns:
            display_columns.append("💰")
        display_columns.extend(["name", "retailer", "Price"])
        if "Unit" in unified_df.columns and unified_df["Unit"].notna().any():
            display_columns.append("Unit")
        if "Best Deals" in unified_df.columns:
            display_columns.append("Best Deals")
        if "Health" in unified_df.columns:
            display_columns.append("Health")
        display_columns.append("Status")  # Show status before add_to_basket
        display_columns.append("add_to_basket")  # Rightmost column
        
        # Build column configuration
        column_config = {
            "💰": st.column_config.TextColumn(
                "Cheapest",
                help="💰 indicates this is the cheapest option for this product",
                width="small"
            ),
            "name": st.column_config.TextColumn(
                "Product Name",
                help="Product name from retailer"
            ),
            "retailer": st.column_config.TextColumn(
                "Retailer",
                help="Retailer: Albert Heijn, Jumbo, Picnic, or Dirk"
            ),
            "Price": st.column_config.TextColumn(
                "Price",
                help="Price in euros (€)",
                width="small"
            ),
            "Unit": st.column_config.TextColumn(
                "Unit",
                help="Product size/unit information",
                disabled=True
            ),
            "Best Deals": st.column_config.TextColumn(
                "Best Deals",
                help="💰 Cheapest overall, ⚖️ Best per unit",
                disabled=True
            ),
            "Health": st.column_config.TextColumn(
                "Health",
                help="Health category: Healthy, Less healthy, or Neutral",
                disabled=True
            ),
            "Status": st.column_config.TextColumn(
                "Status",
                help="Shows if item is already in your basket",
                disabled=True,
                width="small"
            ),
            "add_to_basket": st.column_config.CheckboxColumn(
                "Add to basket",
                help="Select items you want to add to your basket",
                default=False,
                width="small"
            )
        }
        
        # Render unified table with st.data_editor (allows checkbox editing)
        # Create a mapping from row index to product_id for stable reference
        # We'll use this mapping instead of including product_id in the visible table
        index_to_product_id = unified_df["product_id"].to_dict()
        
        # Render table without product_id column (cleaner UI)
        table_df = unified_df[display_columns].copy()
        
        edited_df = st.data_editor(
            table_df,
            column_config=column_config,
            width='stretch',
            hide_index=True,
            key="product_comparison_table"
        )
        
        # Count selected items
        selected_count = edited_df["add_to_basket"].sum() if "add_to_basket" in edited_df.columns else 0
        
        # Add to basket button (below table)
        if selected_count > 0:
            add_button = st.button(
                f"➕ Add {selected_count} Selected Item(s) to Basket",
                type="primary",
                width='stretch'
            )
            
            if add_button:
                # Get selected rows
                selected_mask = edited_df["add_to_basket"] == True
                selected_rows = edited_df[selected_mask]
                
                added_count = 0
                skipped_count = 0
                
                # Process each selected row using index mapping to product_id
                for idx, selected_row in selected_rows.iterrows():
                    # Get product_id from index mapping (stable reference)
                    product_id_ref = index_to_product_id.get(idx)
                    if not product_id_ref:
                        skipped_count += 1
                        continue
                    
                    # Find matching product in original products list using product_id
                    matching_product = None
                    for product in products:
                        # Match by product_id (handle both "retailer:id" and "id" formats)
                        prod_id = product.get("id") or product.get("product_id", "")
                        retailer = product.get("retailer", "")
                        
                        # Compare: product_id_ref could be "retailer:id" or just "id"
                        if str(product_id_ref) == str(prod_id):
                            matching_product = product
                            break
                        elif ":" in str(product_id_ref) and str(product_id_ref) == f"{retailer}:{prod_id}":
                            matching_product = product
                            break
                        elif ":" not in str(product_id_ref) and str(prod_id).split(":")[-1] == str(product_id_ref):
                            matching_product = product
                            break
                    
                    if not matching_product:
                        skipped_count += 1
                        continue
                    
                    product = matching_product
                    
                    # Check if already in basket (skip if yes)
                    prod_id = product.get("id") or product.get("product_id", "")
                    retailer = product.get("retailer", "")
                    item_id = f"{retailer}:{prod_id}" if ":" not in str(prod_id) else str(prod_id)
                    
                    if item_id in basket_item_ids:
                        skipped_count += 1
                        continue
                    
                    # Extract product ID (handle both id formats like "ah:123" or just "123")
                    product_id_clean = str(prod_id).split(":")[-1] if ":" in str(prod_id) else str(prod_id)
                    
                    # Add to cart via backend API
                    result = add_to_cart_backend(
                        session_id=session_id,
                        retailer=retailer,
                        product_id=product_id_clean,
                        name=product.get("name", ""),
                        price_eur=product.get("price_eur") or product.get("price", 0.0),
                        quantity=1,
                        image_url=product.get("image_url"),
                        health_tag=product.get("health_tag")
                    )
                    
                    if result is not None:
                        added_count += 1
                    else:
                        skipped_count += 1
                
                # Show success message
                if added_count > 0:
                    st.success(f"✅ Added {added_count} item(s) to your basket!")
                    if skipped_count > 0:
                        st.info(f"ℹ️ {skipped_count} item(s) were already in your basket and were skipped.")
                    st.caption("💡 View your basket on the **My Basket** page in the sidebar.")
                    
                    # After adding items, trigger a rerun to refresh cart status
                    # But since results are stored in session_state, the table will remain visible
                    st.rerun()
                else:
                    st.warning("⚠️ All selected items were already in your basket.")
        else:
            st.caption("👆 Select items using the checkboxes in the rightmost column and click 'Add Selected Item(s) to Basket' above.")
        
        # Price History Demo section
        st.markdown("---")
        st.markdown("### 📈 Price History (Demo)")
        st.caption("View price trends for products. This is a demo feature - data resets when the backend restarts.")
        
        # Product selector for price history
        if len(products) > 0:
            product_options = [
                f"{p.get('name', 'Unknown')} ({get_retailer_display_name(p.get('retailer', ''))})"
                for p in products[:20]  # Limit to first 20 products
            ]
            
            selected_product_idx = st.selectbox(
                "Select a product to view price history:",
                options=range(len(product_options)),
                format_func=lambda x: product_options[x] if x < len(product_options) else "",
                key="price_history_product_select"
            )
            
            if selected_product_idx is not None and selected_product_idx < len(products):
                selected_product = products[selected_product_idx]
                product_id = selected_product.get("id") or selected_product.get("product_id", "")
                retailer = selected_product.get("retailer", "")
                
                if product_id and retailer:
                    # Fetch price history
                    history_data = get_price_history(retailer, product_id)
                    
                    if history_data and history_data.get("points"):
                        points = history_data["points"]
                        
                        # Create DataFrame for chart
                        history_df = pd.DataFrame([
                            {
                                "Date": datetime.fromtimestamp(p["ts"]).strftime("%Y-%m-%d %H:%M"),
                                "Price (€)": p["price_eur"]
                            }
                            for p in points
                        ])
                        
                        st.line_chart(history_df.set_index("Date")["Price (€)"])
                        st.caption(f"Showing {len(points)} price point(s) for this product.")
                        st.info("💡 This is a demo feature. Price data is based on recent searches and will reset when the backend restarts.")
                    else:
                        st.info("No price history available yet for this product. This demo history is built from recent searches and resets when the backend restarts.")
        
        # TODO: Future enhancements:
        #   - Support adding quantities (currently adds 1 of each)
        #   - Add "Add all results to basket" quick action
        #   - Quick-add buttons next to each row
        
        with side_col:
            image_card("search_side", caption="Healthy, budget-friendly picks from all supermarkets.")

else:
    # Initial state - show helpful information
    st.info(
        "Start by typing a product above – for example **\"volkoren pasta\"**, "
        "**\"halfvolle melk\"** or **\"kikkererwten\"**. "
        "We'll compare prices across your selected supermarkets."
    )
    
    # Show example searches
    with st.expander("🔍 Example Searches"):
        example_queries = [
            "melk",
            "brood",
            "appels",
            "kipfilet",
            "yoghurt",
            "kaas",
            "tomaten"
        ]
        
        cols = st.columns(3)
        for idx, example in enumerate(example_queries):
            with cols[idx % 3]:
                if st.button(example, key=f"example_{idx}", width='stretch'):
                    # Update session state and trigger search
                    st.session_state["search_query"] = example
                    # Clear stored results to force new search
                    if "search_results" in st.session_state:
                        del st.session_state["search_results"]
                    st.rerun()  # Rerun to trigger form submission with new query

# Footer
render_footer()
