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

from streamlit_app.utils.recipes_data import get_all_recipes, Recipe
from streamlit_app.utils.meal_plan import (
    DAYS_OF_WEEK,
    init_meal_plan,
    get_meal_plan,
    add_meal_to_day,
    clear_meal_plan,
)
from streamlit_app.utils.session import get_or_create_session_id
from ui.style import inject_global_css, render_footer

# Inject global CSS styling
inject_global_css()

# Page header
st.markdown("## 🗓 Meal Planner")
st.caption("Plan simple meals for your week using recipes you've marked as planned.")

# Initialize meal plan
init_meal_plan()

# Build recipes lookup
all_recipes = get_all_recipes()
recipes_by_id: Dict[str, Recipe] = {r.id: r for r in all_recipes}

# Get planned recipes from session
planned_ids = st.session_state.get("planned_recipes", set())
planned_list = [
    recipes_by_id[rid] for rid in planned_ids if rid in recipes_by_id
]

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

# Right column: Weekly calendar view
with right_col:
    st.markdown("### This week's plan")

    meal_plan = get_meal_plan()

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

