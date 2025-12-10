"""
Meal Planning Utility Module.

This module provides session-based meal planning functionality. It manages
a weekly meal plan where recipes can be assigned to days of the week.

All state is stored in st.session_state["meal_plan"] as a dictionary
mapping day names to lists of recipe IDs.
"""

from typing import Dict, List
import streamlit as st

DAYS_OF_WEEK = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def init_meal_plan() -> None:
    """
    Initialize the meal_plan in session state if it doesn't exist.
    
    Creates a dictionary with each day of the week mapped to an empty list.
    """
    if "meal_plan" not in st.session_state:
        st.session_state["meal_plan"] = {
            day: [] for day in DAYS_OF_WEEK
        }


def get_meal_plan() -> Dict[str, List[str]]:
    """
    Get the current meal plan from session state.
    
    Ensures the meal plan is initialized before returning.
    
    Returns:
        Dictionary mapping day names to lists of recipe IDs
    """
    init_meal_plan()
    return st.session_state["meal_plan"]


def add_meal_to_day(day: str, recipe_id: str) -> None:
    """
    Add a recipe to a specific day in the meal plan.
    
    Args:
        day: Day of the week (must be in DAYS_OF_WEEK)
        recipe_id: Recipe ID to add
    
    Raises:
        ValueError: If day is not in DAYS_OF_WEEK
    """
    if day not in DAYS_OF_WEEK:
        raise ValueError(f"Invalid day: {day}. Must be one of {DAYS_OF_WEEK}")
    
    init_meal_plan()
    meal_plan = st.session_state["meal_plan"]
    
    # Add recipe_id to the day's list if not already present
    if recipe_id not in meal_plan[day]:
        meal_plan[day].append(recipe_id)


def clear_meal_plan() -> None:
    """
    Clear the entire meal plan, resetting all days to empty lists.
    """
    init_meal_plan()
    st.session_state["meal_plan"] = {
        day: [] for day in DAYS_OF_WEEK
    }

