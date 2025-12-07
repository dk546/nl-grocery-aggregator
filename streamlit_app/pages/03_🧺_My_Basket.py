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
from utils.api_client import (
    view_cart_backend,
    remove_from_cart_backend,
    update_cart_item_quantity,
    add_to_cart_backend,
    get_basket_savings,
    list_basket_templates,
    save_basket_template,
    apply_basket_template,
    delete_basket_template,
    get_price_history,
)
from utils.profile import HOUSEHOLD_PROFILES, get_profile_by_key
from utils.preferences import (
    get_user_preferences_from_session,
    PREFERENCE_HEALTH_BALANCED,
    PREFERENCE_HEALTH_FIRST,
    PREFERENCE_BUDGET_FIRST,
)
from utils.retailers import get_retailer_display_name
from ui.style import inject_global_css, section_header, pill_tag, image_card, render_footer

# Inject global CSS styling
inject_global_css()

# Page header
section_header(
    title="Your basket",
    eyebrow="SMART WEEKLY SHOPPING",
    help_text="Review your items, explore cheaper swaps, and check totals per supermarket."
)

# Get session ID for cart operations (using shared helper from app.py)
session_id = get_or_create_session_id()

# Initialize session state for applied savings tracking
if "applied_savings_total" not in st.session_state:
    st.session_state["applied_savings_total"] = 0.0

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
    st.info(
        "Your basket is empty. Start by adding items from **Search & Compare**.\n\n"
        "Tip: Try searching for *volkoren pasta*, *havermout*, or *paprika* to begin your weekly shop."
    )
    st.stop()

# Calculate health breakdown early (for metrics)
healthy_count = sum(1 for item in basket if item.get("health_tag") == "healthy")
unhealthy_count = sum(1 for item in basket if item.get("health_tag") == "unhealthy")
neutral_count = summary["count_items"] - healthy_count - unhealthy_count

# Household profile context (for later use)
profile_key = st.session_state.get("household_profile_key")
profile = HOUSEHOLD_PROFILES.get(profile_key) if profile_key else None
weekly_budget = profile.typical_weekly_budget_hint if profile and profile.typical_weekly_budget_hint else None

# Top metrics band (now with 5 columns for budget)
metrics_cols = st.columns([1, 1, 1, 1, 1], gap="large")

with metrics_cols[0]:
    st.metric("Items", summary["count_items"])

with metrics_cols[1]:
    st.metric("Total cost", f"€{summary['total_price']:.2f}")

with metrics_cols[2]:
    st.metric("Retailers", summary["unique_retailer_count"])

with metrics_cols[3]:
    st.metric("Healthy items", healthy_count)

with metrics_cols[4]:
    if weekly_budget:
        basket_total = summary['total_price']
        used_ratio = basket_total / weekly_budget
        used_pct = min(used_ratio * 100, 999)
        st.metric("Weekly budget used", f"{used_pct:.0f}%")
    else:
        st.metric("Weekly budget used", "—")

if weekly_budget and profile:
    st.caption(
        f"Based on a typical weekly budget of ~€{weekly_budget:.0f} for your **{profile.label.lower()}** household."
    )

# Continue shopping CTA (when basket has items)
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    try:
        st.page_link(
            "pages/02_🛒_Search_and_Compare.py",
            label="🔍 Continue shopping",
            icon="🔍",
            use_container_width=True,
        )
    except (AttributeError, TypeError):
        st.button("🔍 Continue shopping (go to Search & Compare)", use_container_width=True)

st.divider()

# Main layout: wide center for basket, side column for insights
main_col, side_col = st.columns([2.2, 1], gap="large")

# Main column: Basket table + item actions
with main_col:
    st.markdown("### Basket summary")
    st.caption("All items currently in your basket. Adjust quantities or remove items here.")
    
    # Basket items table
    
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
                min_value=0,
                step=1,
                help="Change quantity (set to 0 to remove, or use Remove checkbox)"
            ),
            "Total": st.column_config.TextColumn("Total", disabled=True),
            "Health": st.column_config.TextColumn("Health", disabled=True),
        },
        use_container_width=True,
        hide_index=True,
        key="basket_editor"
    )
    
    st.markdown("### Basket actions")
    
    update_button = st.button(
        "💾 Update basket",
        type="primary",
        width='stretch'
    )
    
    if update_button:
        updated_count = 0
        removed_count = 0
        errors = []
        
        # Process each row
        for idx in edited_df.index:
            if idx < len(basket):
                original_item = basket[idx]
                edited_row = edited_df.loc[idx]
                
                retailer = original_item.get("retailer", "")
                product_id = original_item.get("product_id", "") or original_item.get("id", "")
                original_qty = int(original_item.get("quantity", 1))
                new_qty = int(edited_row.get("quantity", original_qty))
                remove_flag = bool(edited_row.get("remove", False))
                
                if not retailer or not product_id:
                    errors.append(f"Missing retailer/product_id for item at index {idx}")
                    continue
                
                try:
                    # Check if item should be removed
                    if remove_flag or new_qty == 0:
                        # Remove entire item
                        result = remove_from_cart_backend(
                            session_id=session_id,
                            retailer=retailer,
                            product_id=product_id,
                            qty=original_qty
                        )
                        if result is not None:
                            removed_count += 1
                        else:
                            errors.append(f"Failed to remove {original_item.get('name', 'item')}")
                    
                    # Check if quantity changed (and item not being removed)
                    elif new_qty != original_qty:
                        # Update quantity
                        result = update_cart_item_quantity(
                            session_id=session_id,
                            retailer=retailer,
                            product_id=product_id,
                            original_quantity=original_qty,
                            new_quantity=new_qty,
                            item_data=original_item
                        )
                        if result is not None:
                            updated_count += 1
                        else:
                            errors.append(f"Failed to update quantity for {original_item.get('name', 'item')}")
                
                except Exception as e:
                    errors.append(f"Error updating {original_item.get('name', 'item')}: {str(e)}")
        
        # Show feedback
        if updated_count > 0 or removed_count > 0:
            msg_parts = []
            if updated_count > 0:
                msg_parts.append(f"Updated {updated_count} item(s)")
            if removed_count > 0:
                msg_parts.append(f"removed {removed_count} item(s)")
            st.success(f"✅ {' and '.join(msg_parts)}!")
            if errors:
                st.warning(f"⚠️ {len(errors)} operation(s) failed. See details below.")
                for error in errors:
                    st.caption(f"• {error}")
            st.rerun()
        elif errors:
            st.error(f"❌ Failed to update basket. {len(errors)} error(s):")
            for error in errors:
                st.caption(f"• {error}")
        else:
            st.info("ℹ️ No changes detected. Adjust quantities or use Remove checkboxes, then click Update basket.")
    
    # Basket actions - Clear and Add More
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ Clear Entire Basket", type="secondary", width='stretch'):
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
        if st.button("🔍 Add More Items", width='stretch'):
            st.switch_page("pages/02_🛒_Search_and_Compare.py")
    
    # Price trend (demo) section
    st.markdown("---")
    st.markdown("### 📈 Price trends (demo)")
    st.caption("View price history for items in your basket. This is a demo feature built from recent searches.")
    
    if basket:
        # Create a selectbox to choose which item to view price history for
        product_options = [
            f"{item.get('name', 'Unknown Product')} ({get_retailer_display_name(item.get('retailer', ''))})"
            for item in basket
        ]
        
        selected_product_idx = st.selectbox(
            "Select an item to view price history:",
            options=range(len(product_options)),
            format_func=lambda x: product_options[x] if x < len(product_options) else "",
            key="price_history_product_select_basket"
        )
        
        if selected_product_idx is not None and selected_product_idx < len(basket):
            selected_item = basket[selected_product_idx]
            product_id = selected_item.get("product_id") or selected_item.get("id", "")
            retailer = selected_item.get("retailer", "")
            product_name = selected_item.get("name", "Unknown Product")
            
            if product_id and retailer:
                # Fetch price history
                try:
                    history_data = get_price_history(retailer, product_id)
                    
                    if history_data and history_data.get("points"):
                        points = history_data["points"]
                        
                        # Create DataFrame for chart
                        from datetime import datetime
                        
                        history_df = pd.DataFrame([
                            {
                                "Date": datetime.fromtimestamp(p["ts"]).strftime("%Y-%m-%d %H:%M"),
                                "Price (€)": p["price_eur"]
                            }
                            for p in points
                        ])
                        history_df["Date"] = pd.to_datetime(history_df["Date"])
                        history_df = history_df.set_index("Date")
                        
                        st.markdown(f"**Price history for {product_name} ({get_retailer_display_name(retailer)})**")
                        st.line_chart(history_df, y="Price (€)")
                        st.caption(
                            "💡 **Demo feature**: Price history is built from recent searches and resets when the backend restarts. "
                            "This is not persistent across deployments."
                        )
                    else:
                        st.info(
                            f"No price history yet for **{product_name}**. "
                            "Search for this item a few times to build up historical data. "
                            "This demo feature resets when the backend restarts."
                        )
                except Exception as e:
                    st.caption(f"Unable to load price history: {str(e)}")
            else:
                st.warning("Could not retrieve product ID or retailer for selected item.")
    else:
        st.info("Add items to your basket to view price trends.")

# Side column: retailer totals, savings, templates, insights
with side_col:
    image_card("basket_side", caption="Turn this basket into simple, balanced meals.")
    
    # Smart Suggestions card
    suggestions = []
    try:
        from aggregator.savings import get_savings_opportunities_for_basket
        
        # Prepare basket items in the format expected by the savings helper
        basket_items_for_savings = []
        for item in basket:
            item_dict = {
                "retailer": item.get("retailer", ""),
                "product_id": item.get("product_id", ""),
                "name": item.get("name", ""),
                "price_eur": float(item.get("price_eur", item.get("price", 0.0))),
                "quantity": int(item.get("quantity", 1)),
                "line_total": float(item.get("line_total", item.get("price_eur", item.get("price", 0.0)) * item.get("quantity", 1))),
                "image_url": item.get("image_url"),
                "health_tag": item.get("health_tag"),
                "category": item.get("category"),
                "price_per_unit": item.get("price_per_unit"),
            }
            basket_items_for_savings.append(item_dict)
        
        suggestions = get_savings_opportunities_for_basket(basket_items_for_savings)
    except Exception as e:
        # Fail quietly; suggestions are a nice-to-have
        suggestions = []
    
    if suggestions:
        # Get user preferences and re-rank suggestions
        prefs = get_user_preferences_from_session()
        
        def _score_suggestion(sugg) -> float:
            """Score a suggestion based on user preferences."""
            base = 0.0
            s_type = getattr(sugg, "type", None) or getattr(sugg, "suggestion_type", None)
            
            # Default weights
            if prefs.health_focus == PREFERENCE_HEALTH_BALANCED:
                budget_w = 1.0
                health_w = 1.0
            elif prefs.health_focus == PREFERENCE_HEALTH_FIRST:
                budget_w = 0.7
                health_w = 1.5
            elif prefs.health_focus == PREFERENCE_BUDGET_FIRST:
                budget_w = 1.5
                health_w = 0.7
            else:
                budget_w = health_w = 1.0
            
            score = 0.0
            if s_type == "cheaper":
                score += budget_w
            elif s_type == "healthier":
                score += health_w
            elif s_type == "cheaper_and_healthier":
                score += budget_w + health_w
            
            # Optional: small boost for larger savings_amount
            savings = getattr(sugg, "savings_amount", None)
            if isinstance(savings, (int, float)):
                score += min(max(savings, 0.0), 5.0) * 0.1  # dampened boost
            
            return score
        
        # Re-rank suggestions by score (descending)
        suggestions = sorted(suggestions, key=_score_suggestion, reverse=True)
        
        st.markdown("### Smart suggestions")
        
        # Show preference-aware caption
        if prefs.health_focus == PREFERENCE_HEALTH_FIRST:
            st.caption("Sorted with your preference: **healthier choices first**.")
        elif prefs.health_focus == PREFERENCE_BUDGET_FIRST:
            st.caption("Sorted with your preference: **lowest prices first**.")
        else:
            st.caption("Sorted with a balance between health and price.")
        
        # Show at most 3 suggestions to avoid clutter
        for s in suggestions[:3]:
            st.markdown('<div class="nlga-card nlga-card--sidebar">', unsafe_allow_html=True)
            
            # 1) Title line
            # Use type to adjust icon/text
            suggestion_type = getattr(s, "type", "cheaper") or "cheaper"
            if suggestion_type == "cheaper_and_healthier":
                icon = "🌱"
            elif suggestion_type == "healthier":
                icon = "🥦"
            else:  # cheaper
                icon = "💶"
            st.markdown(f"**{icon} {s.title if hasattr(s, 'title') and s.title else 'Suggested swap'}**")
            
            # 2) Main swap description
            current_name = getattr(s, "current_item_name", None) or getattr(s, "from_item_name", "Current item")
            alt_name = getattr(s, "alternative_item_name", None) or getattr(s, "to_item_name", "Alternative item")
            st.markdown(f"{current_name} → **{alt_name}**")
            
            # 3) Savings / health delta (if available)
            savings = getattr(s, "savings_amount", None)
            health_delta = getattr(s, "health_delta", None)
            
            details_parts = []
            if savings is not None and savings > 0:
                details_parts.append(f"Save ~€{savings:.2f}")
            if health_delta:
                details_parts.append(health_delta)
            
            if details_parts:
                st.caption(" • ".join(details_parts))
            
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown("### Smart suggestions")
        st.caption("As your basket grows, we'll highlight cheaper or healthier alternatives here.")
    
    st.markdown("---")
    
    # Totals per supermarket
    if cart_data and cart_data.get("total_by_retailer"):
        section_header(
            title="Totals per supermarket",
            eyebrow="COST BREAKDOWN",
            help_text="See which retailer is currently cheapest for your whole basket."
        )
        retailer_totals = cart_data["total_by_retailer"]
        for retailer, amount in sorted(retailer_totals.items(), key=lambda x: x[1]):
            readable = get_retailer_display_name(retailer)
            st.markdown('<div class="nlga-card nlga-card--sidebar">', unsafe_allow_html=True)
            st.markdown(f"**{readable}**")
            st.caption(f"Estimated total: €{amount:.2f}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
    
    # Savings Finder
    if basket:
        section_header(
            title="Savings Finder",
            eyebrow="CHEAPER OPTIONS",
            help_text="Quick estimation of potential savings from cheaper swaps."
        )
        st.markdown('<div class="nlga-card nlga-card--sidebar">', unsafe_allow_html=True)
        
        st.caption("We'll look for cheaper alternatives to items in your basket.")
        
        # Check if user wants to analyze savings (store in session_state to preserve across reruns)
        if "check_savings" not in st.session_state:
            st.session_state["check_savings"] = False
        
        check_savings_button = st.button("🔎 Check for savings", width='stretch', type="primary")
        
        if check_savings_button:
            st.session_state["check_savings"] = True
        
        # Load savings data if requested
        savings_data = None
        if st.session_state.get("check_savings", False):
            with st.spinner("Looking for cheaper alternatives..."):
                savings_data = get_basket_savings(session_id)
                # Store in session_state to preserve across reruns (used by Weekly Savings Report)
                if savings_data:
                    st.session_state["savings_data"] = savings_data
                    st.session_state["basket_savings"] = savings_data
                else:
                    st.session_state["basket_savings"] = None
        elif "savings_data" in st.session_state:
            # Use cached savings data if available
            savings_data = st.session_state.get("savings_data")
            # Also update basket_savings for Weekly Savings Report
            st.session_state["basket_savings"] = savings_data
        
        # Display savings summary
        if savings_data is not None:
            suggestions = savings_data.get("suggestions", [])
            potential_savings_total = float(savings_data.get("potential_savings_total", 0.0))
            
            if suggestions:
                st.markdown(f"**🎯 Up to €{potential_savings_total:.2f} savings**")
                st.caption(f"{len(suggestions)} swap(s) available")
            else:
                st.caption("No cheaper alternatives found.")
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("---")
    
    # Saved baskets / templates
    section_header(
        title="Saved baskets",
        eyebrow="TEMPLATES",
        help_text="Reuse your favorite weekly shops with one click."
    )
    st.markdown('<div class="nlga-card nlga-card--sidebar">', unsafe_allow_html=True)
    
    # Load templates (cached in session_state)
    if "basket_templates" not in st.session_state:
        st.session_state["basket_templates"] = None
    
    if st.session_state["basket_templates"] is None:
        templates_data = list_basket_templates(session_id)
        st.session_state["basket_templates"] = templates_data or {"templates": []}
    
    templates = st.session_state["basket_templates"].get("templates", [])
    
    # Save current basket as template
    if basket:
        with st.form("save_basket_template_form", clear_on_submit=True):
            template_name = st.text_input(
                "Template name",
                value="Weekly groceries",
                help="Give this basket a name so you can re-use it later.",
            )
            save_submitted = st.form_submit_button("💾 Save as template", width='stretch')
        
        if save_submitted:
            if not template_name.strip():
                st.warning("Please enter a name for your template.")
            else:
                result = save_basket_template(session_id, template_name.strip())
                if result and result.get("template"):
                    st.success(f"✅ Saved: **{result['template']['name']}**")
                    # Refresh templates cache
                    st.session_state["basket_templates"] = list_basket_templates(session_id) or {"templates": []}
                    st.rerun()
                else:
                    st.error("Could not save template. Please try again.")
    else:
        st.caption("💡 You need items in your basket before you can save a template.")
    
    # List existing templates
    if templates:
        st.markdown("**Your templates:**")
        for t in templates[:3]:  # Show max 3 templates in sidebar
            tid = t.get("id")
            name = t.get("name", "Unnamed")
            item_count = len(t.get("items", []))
            
            col_apply, col_del = st.columns([2, 1])
            
            with col_apply:
                if st.button("🛒 Apply", key=f"apply_template_{tid}", width='stretch', use_container_width=True):
                    result = apply_basket_template(session_id, tid)
                    if result:
                        st.success(f"✅ Applied **{name}**")
                        st.session_state.pop("basket_savings", None)
                        st.session_state["basket_templates"] = list_basket_templates(session_id) or {"templates": []}
                        st.rerun()
                    else:
                        st.error("Could not apply template.")
            
            with col_del:
                if st.button("🗑️", key=f"delete_template_{tid}", width='stretch', use_container_width=True):
                    ok = delete_basket_template(session_id, tid)
                    if ok:
                        st.success(f"✅ Deleted")
                        st.session_state["basket_templates"] = list_basket_templates(session_id) or {"templates": []}
                        st.rerun()
            
            st.caption(f"{name} ({item_count} items)")
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Quick health summary
    section_header(
        title="Quick health summary",
        eyebrow="INSIGHTS",
        help_text="A lightweight breakdown of healthier vs. less healthy items."
    )
    st.markdown('<div class="nlga-card nlga-card--sidebar">', unsafe_allow_html=True)
    st.caption(f"🥦 Healthy items: {healthy_count}")
    st.caption(f"⚪ Neutral items: {neutral_count}")
    st.caption(f"⚠️ Less healthy: {unhealthy_count}")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # NLGA Plus card
    st.markdown('<div class="nlga-card nlga-card--sidebar">', unsafe_allow_html=True)
    st.markdown("#### ✨ NLGA Plus (coming soon)")
    st.caption(
        "Unlock weekly price history, automatic smart swaps, and personalized recipe suggestions "
        "based on what you usually buy."
    )
    st.markdown('</div>', unsafe_allow_html=True)

# Footer
render_footer()
    
