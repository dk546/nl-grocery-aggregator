"""
Meal Planner Page - Weekly Meal Planning.

This page allows users to assign planned recipes to days of the week,
creating a simple weekly meal plan. The meal plan is session-based and
integrates with the Recipes page and shopping workflow.
"""

import sys
from pathlib import Path
from typing import Dict

# Ensure the streamlit_app directory is in the Python path
streamlit_app_dir = Path(__file__).parent.parent
if str(streamlit_app_dir) not in sys.path:
    sys.path.insert(0, str(streamlit_app_dir))

# Add project root to path to import api.config
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import streamlit as st
from typing import List

from streamlit_app.utils.recipes_data import get_all_recipes, Recipe
from streamlit_app.utils.meal_plan import (
    DAYS_OF_WEEK,
    init_meal_plan,
    get_meal_plan,
    add_meal_to_day,
    clear_meal_plan,
)
from streamlit_app.utils.session import get_or_create_session_id
from streamlit_app.utils.api_client import add_to_cart_backend
from streamlit_app.utils.retailers import RETAILER_DISPLAY_NAMES, ALL_RETAILER_CODES
from aggregator.events import log_meal_plan_sent_to_cart
from ui.styles import load_global_styles
from ui.layout import page_header, section
from ui.style import render_footer  # Keep footer function

# Inject global CSS styling
load_global_styles()

# Page header
page_header(
    title="🗓 Meal Planner",
    subtitle="Plan your weekly meals and automatically add ingredients to your basket."
)
st.caption("Plan simple meals for your week using recipes you've marked as planned.")

# Initialize meal plan
init_meal_plan()

# Initialize preferred retailer for meal plan
if "meal_plan_retailer" not in st.session_state:
    st.session_state["meal_plan_retailer"] = "ah"  # default

# Build recipes lookup
all_recipes = get_all_recipes()
recipes_by_id: Dict[str, Recipe] = {r.id: r for r in all_recipes}

# Get planned recipes from session
planned_ids = st.session_state.get("planned_recipes", set())
planned_list = [
    recipes_by_id[rid] for rid in planned_ids if rid in recipes_by_id
]

# Compute shopping summary from meal plan
meal_plan = get_meal_plan()

# Flatten recipe IDs from the plan (count duplicates)
recipe_ids_in_plan: List[str] = []
for day in DAYS_OF_WEEK:
    recipe_ids_in_plan.extend(meal_plan.get(day, []))

planned_recipes_in_plan: List[Recipe] = [
    recipes_by_id[rid] for rid in recipe_ids_in_plan if rid in recipes_by_id
]

recipe_count = len(planned_recipes_in_plan)
total_estimated_price = sum(
    getattr(r, "estimated_price_eur", 0.0) or 0.0 for r in planned_recipes_in_plan
)

# Two-column layout
left_col, right_col = st.columns([2, 3])

# Left column: Planned recipes list
with left_col:
    if not planned_list:
        st.info(
            "You don't have any planned recipes yet. "
            "Go to the **Recipes** page and click **Plan this recipe** to start building a meal plan."
        )
    else:
        st.markdown("### Planned recipes")
        st.caption("Assign each planned recipe to a day of the week.")

        for recipe in planned_list:
            st.markdown(f"**{recipe.title}**")
            day = st.selectbox(
                "Day",
                options=["(none)"] + DAYS_OF_WEEK,
                key=f"planner_day_select_{recipe.id}",
            )
            if st.button("Assign to day", key=f"planner_assign_{recipe.id}"):
                if day == "(none)":
                    st.warning("Please select a day before assigning.")
                else:
                    add_meal_to_day(day, recipe.id)

                    # Log analytics (best-effort)
                    try:
                        session_id = get_or_create_session_id()
                    except Exception:
                        session_id = None

                    try:
                        from aggregator.events import log_meal_planned_on_day
                        log_meal_planned_on_day(
                            session_id=session_id,
                            recipe_id=recipe.id,
                            day=day
                        )
                    except Exception:
                        pass

                    st.success(f"Assigned **{recipe.title}** to **{day}**.")
            
            # Add "Find ingredients" button for each recipe
            if st.button("Find ingredients for this recipe", key=f"find_ing_{recipe.id}"):
                # Set a shared session key with the recipe title as search query
                st.session_state["recipe_search_query"] = recipe.title
                
                st.info(
                    "Opened the recipe search query for this recipe. "
                    "Now click on **🛒 Search & Compare** in the sidebar to see results."
                )

# Right column: Weekly calendar view
with right_col:
    st.markdown("### This week's plan")

    if all(len(meal_plan[day]) == 0 for day in DAYS_OF_WEEK):
        st.caption("No meals assigned yet. Use the left panel to assign recipes to days.")
    else:
        calendar_cols = st.columns(len(DAYS_OF_WEEK))

        for idx, day in enumerate(DAYS_OF_WEEK):
            with calendar_cols[idx]:
                st.markdown(f"**{day}**")
                if not meal_plan[day]:
                    st.caption("No recipe yet")
                else:
                    for rid in meal_plan[day]:
                        recipe = recipes_by_id.get(rid)
                        if recipe is None:
                            continue
                        price_str = (
                            f"€{recipe.estimated_price_eur:.2f}"
                            if getattr(recipe, "estimated_price_eur", None) is not None
                            else ""
                        )
                        st.markdown(f"- {recipe.title}")
                        if price_str:
                            st.caption(price_str)

    st.markdown("---")
    
    # Shopping summary section
    st.markdown("### Shopping summary (demo)")
    
    if recipe_count == 0:
        st.caption("No meals in this week's plan yet. Assign recipes to days first.")
    else:
        st.markdown(
            f"You have **{recipe_count} planned meal(s)** this week, "
            f"with an approximate total of **€{total_estimated_price:.2f}** "
            "(based on recipe estimates)."
        )
        
        # Preferred retailer selector
        st.markdown("#### Preferred retailer")
        current_retailer = st.session_state.get("meal_plan_retailer", "ah")
        retailer_code = st.selectbox(
            "Choose a primary retailer for this plan:",
            options=ALL_RETAILER_CODES,
            format_func=lambda code: RETAILER_DISPLAY_NAMES.get(code, code),
            index=ALL_RETAILER_CODES.index(current_retailer) if current_retailer in ALL_RETAILER_CODES else 0,
            key="meal_plan_retailer_select",
        )
        st.session_state["meal_plan_retailer"] = retailer_code
        
        if st.button("Send meal plan to My Basket (demo)"):
            send_errors = []
            session_id = None
            success_count = 0
            
            # Get session ID (best-effort)
            try:
                session_id = get_or_create_session_id()
            except Exception:
                session_id = "demo"
            
            # Add each recipe to cart as a placeholder item
            for r in planned_recipes_in_plan:
                try:
                    # Use the selected preferred retailer from session state
                    selected_retailer = st.session_state.get("meal_plan_retailer", "ah")
                    result = add_to_cart_backend(
                        session_id=session_id,
                        retailer=selected_retailer,  # Use user-selected retailer
                        product_id=f"meal-plan-{r.id}",  # Unique product ID for this meal plan item
                        name=f"[Meal plan] {r.title}",
                        price_eur=getattr(r, "estimated_price_eur", 0.0) or 0.0,
                        quantity=1,
                        image_url=None,  # Optional
                        health_tag=None,  # Optional
                    )
                    
                    # Check if the operation succeeded (returns dict on success, None on error)
                    if result is not None:
                        success_count += 1
                    else:
                        send_errors.append(r.title)
                except Exception:
                    # Catch any unexpected exceptions (shouldn't happen, but be safe)
                    send_errors.append(r.title)
            
            # Log analytics (best-effort)
            try:
                log_meal_plan_sent_to_cart(
                    session_id=session_id,
                    recipe_count=recipe_count,
                    total_estimated_price_eur=total_estimated_price,
                )
            except Exception:
                pass
            
            # Show success or warning message
            if len(send_errors) == 0:
                # All items succeeded
                st.success(
                    "Sent your weekly meal plan to My Basket as demo items. "
                    "Next, open 🧺 My Basket to review them, and then go to "
                    "📊 Health Insights to see how healthy your basket looks."
                )
            else:
                # Some or all items failed
                if success_count > 0:
                    # Partial success
                    failed_list = "\n".join([f"- {title}" for title in send_errors[:5]])
                    if len(send_errors) > 5:
                        failed_list += f"\n- ... and {len(send_errors) - 5} more"
                    
                    st.warning(
                        f"Tried to send your weekly meal plan to My Basket. "
                        f"**{success_count}** item(s) were added successfully, but "
                        f"**{len(send_errors)}** item(s) could not be added:\n\n"
                        f"{failed_list}\n\n"
                        f"You can still open 🧺 My Basket to review what was added."
                    )
                else:
                    # Complete failure
                    st.warning(
                        "Could not send your weekly meal plan to My Basket. "
                        "Please check your connection and try again. "
                        "You can still open 🧺 My Basket to manually add items."
                    )
    
    st.markdown("---")
    if st.button("Clear meal plan"):
        clear_meal_plan()
        st.info("Cleared the meal plan for this session.")

    st.markdown(
        """
        <small>
        Next steps:<br>
        • Go to <b>🧺 My Basket</b> to start assembling ingredients for your planned meals.<br>
        • Go to <b>📊 Health Insights</b> to see how healthy your grocery basket looks once you've added items.
        </small>
        """,
        unsafe_allow_html=True,
    )

# Footer
render_footer()

