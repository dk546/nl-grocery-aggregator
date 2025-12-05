"""
Recipes & Ideas Page - Healthy Recipe Inspiration Hub.

This page provides recipe suggestions and ideas for healthy meals. Users can
browse, filter, and explore recipes. Future integration will allow adding
recipe ingredients directly to the shopping basket.
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
from typing import List, Dict, Any, Optional

from utils import recipes_data
from utils.session import get_or_create_session_id
from utils.api_client import search_products, add_to_cart_backend
from utils.profile import get_profile_by_key, HOUSEHOLD_PROFILES
from ui.style import (
    inject_global_css,
    section_header,
    pill_tag,
    hero_banner,
    image_card,
    get_random_asset_image,
    render_footer,
)


def health_tag_to_score(health_tag: Optional[str]) -> float:
    """
    Convert health_tag to numeric score for sorting.
    
    Returns:
        Score: healthy=2.0, neutral=1.0, unhealthy=0.0, unknown/missing=0.5
    """
    if not health_tag:
        return 0.5
    health_tag_lower = str(health_tag).lower()
    if health_tag_lower == "healthy":
        return 2.0
    elif health_tag_lower == "neutral":
        return 1.0
    elif health_tag_lower == "unhealthy":
        return 0.0
    else:
        return 0.5  # Unknown gets neutral score


def pick_best_product_for_ingredient(
    ingredient: str,
    retailers: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Search products for a single ingredient and return the 'best' product.
    
    Selection rule:
    - Prefer the highest health_score (derived from health_tag).
    - If there's a tie in health_score, pick the lowest price.
    - If no products are found at all, return None.
    
    Args:
        ingredient: Ingredient name to search for
        retailers: Optional list of retailer codes (e.g., ["ah", "jumbo", "picnic", "dirk"])
    
    Returns:
        Best product dict with fields like product_id, retailer, name, price_eur, etc.
        or None if no products found.
    """
    try:
        # Search products - use health_filter=None to get all products for comparison
        results_dict = search_products(
            query=ingredient,
            retailers=retailers,
            health_filter=None,  # Get all results to compare
            size=10,  # Get up to 10 results per retailer
            page=0,
        )
        
        if not results_dict or "results" not in results_dict:
            return None
        
        products = results_dict.get("results", [])
        
        if not products:
            return None
        
        # Convert to DataFrame for easier sorting
        df = pd.DataFrame(products)
        
        # Create health_score column from health_tag
        if "health_tag" in df.columns:
            df["health_score"] = df["health_tag"].apply(health_tag_to_score)
        else:
            df["health_score"] = 0.5  # Default neutral score
        
        # Ensure price_eur is numeric
        if "price_eur" in df.columns:
            df["price_eur"] = pd.to_numeric(df["price_eur"], errors="coerce").fillna(9999.0)
        else:
            df["price_eur"] = 9999.0  # High value so missing prices sort last
        
        # Sort by health_score (descending) then price (ascending)
        df = df.sort_values(["health_score", "price_eur"], ascending=[False, True])
        
        # Return best product as dict
        best_row = df.iloc[0].to_dict()
        return best_row
        
    except Exception:
        # Best-effort: return None on any error
        return None


def handle_add_recipe_to_basket(recipe: recipes_data.Recipe, session_id: str) -> None:
    """
    Add all recipe ingredients to the basket by finding the best products for each.
    
    Args:
        recipe: Recipe object with ingredients list
        session_id: Session ID for basket operations
    """
    ingredients: List[str] = recipe.ingredients
    
    if not ingredients:
        st.warning("This recipe doesn't have a structured ingredient list yet.")
        return
    
    missing: List[str] = []
    chosen_products: List[Dict[str, Any]] = []
    
    with st.spinner("🔍 Finding the best ingredients for your basket..."):
        for ingredient in ingredients:
            # Clean ingredient string (remove parenthetical notes like "(optional)")
            clean_ingredient = ingredient.split("(")[0].strip()
            
            best = pick_best_product_for_ingredient(clean_ingredient)
            
            if best is None:
                missing.append(ingredient)
            else:
                # Extract product_id (may be in format "retailer:id" or just "id")
                product_id = best.get("id", "")
                retailer = best.get("retailer", "")
                
                # Handle product_id format - backend expects just the ID part
                if ":" in product_id:
                    product_id_clean = product_id.split(":")[-1]
                else:
                    product_id_clean = product_id
                
                # Map best product into the basket item payload
                chosen_products.append({
                    "product": best,
                    "product_id": product_id_clean,
                    "retailer": retailer,
                    "name": best.get("name", ""),
                    "price_eur": best.get("price_eur") or best.get("price", 0.0),
                    "image_url": best.get("image_url"),
                    "health_tag": best.get("health_tag"),
                })
        
        # Add each product to basket individually
        if chosen_products:
            added_count = 0
            failed_count = 0
            
            for product_data in chosen_products:
                try:
                    result = add_to_cart_backend(
                        session_id=session_id,
                        retailer=product_data["retailer"],
                        product_id=product_data["product_id"],
                        name=product_data["name"],
                        price_eur=product_data["price_eur"],
                        quantity=1,
                        image_url=product_data.get("image_url"),
                        health_tag=product_data.get("health_tag"),
                    )
                    
                    if result is not None:
                        added_count += 1
                    else:
                        failed_count += 1
                        
                except Exception:
                    failed_count += 1
    
    # Success / partial-success messaging
    found_count = len(chosen_products)
    total_ingredients = len(ingredients)
    
    if found_count == 0:
        st.warning(
            "❌ None of the ingredients could be matched to supermarket products yet. "
            "Try a different recipe or check back later."
        )
        return
    
    if missing:
        st.success(
            f"✅ Added {found_count} product(s) for **'{recipe.title}'**. "
            f"Could not find matches for: {', '.join(missing[:5])}"
            + (f" (and {len(missing) - 5} more)" if len(missing) > 5 else "")
        )
    else:
        st.success(
            f"✅ Added all {found_count} ingredient(s) for **'{recipe.title}'** to your basket!"
        )
    
    # Show caption suggesting to check My Basket
    st.caption("💡 Check **My Basket** in the sidebar to review your items.")
    
    # Offer link to view basket
    col1, col2 = st.columns([3, 1])
    with col2:
        try:
            st.page_link("pages/03_🧺_My_Basket.py", label="🧺 View My Basket", icon="🧺")
        except (AttributeError, TypeError):
            # Fallback for older Streamlit versions
            if st.button("🧺 View My Basket", key=f"view_basket_{recipe.id}", width='stretch'):
                st.switch_page("pages/03_🧺_My_Basket.py")


# Inject global CSS styling
inject_global_css()

# Hero banner image
hero_banner(slot_key="recipes_hero")

# Page header
section_header(
    title="Recipes for your household",
    eyebrow="MEAL IDEAS",
    help_text="Discover simple recipes and scale portions to match your household profile."
)

# Household profile context
profile_key = st.session_state.get("household_profile_key")
profile = HOUSEHOLD_PROFILES.get(profile_key) if profile_key else None
if profile:
    st.caption(f"Currently set to **{profile.label.lower()}** • we'll adjust servings by ~{profile.serving_multiplier}×.")

# Get session ID for basket operations (persists across page navigations)
session_id = get_or_create_session_id()

# Filters-on-left, cards-on-right layout
filters_col, grid_col = st.columns([1, 3], gap="large")

# Left column: Filters
with filters_col:
    st.caption("Filter recipes by ingredient, style, or prep time.")
    
    # Search text input
    search_text = st.text_input(
        "Search",
        value=st.session_state.get("recipe_search", ""),
        placeholder="e.g. pasta, curry, salad…",
        key="recipe_search"
    )
    
    # Meal type filter
    meal_types = ["All"] + recipes_data.get_meal_types()
    selected_meal_type = st.selectbox(
        "Meal Type",
        options=meal_types,
        index=0,
        help="Filter recipes by meal type"
    )
    
    # Dietary preference filter
    tag_options = ["All"] + recipes_data.get_tag_options()
    selected_tag = st.selectbox(
        "Dietary Preference / Tag",
        options=tag_options,
        index=0,
        help="Filter by tags like 'vegetarian', 'quick', 'high-protein', etc."
    )
    
    st.markdown("---")
    image_card("recipes_side", caption="Inspiration for simple, healthy meals.")

# Get filtered recipes (same logic as before)
filtered_recipes = recipes_data.filter_recipes(
    meal_type=selected_meal_type if selected_meal_type != "All" else None,
    tag=selected_tag if selected_tag != "All" else None,
    search_text=search_text if search_text and search_text.strip() else None
)

# Check if search/filters have been applied
has_searched = (selected_meal_type != "All" or selected_tag != "All" or (search_text and search_text.strip()))

# Right column: Recipe cards grid
with grid_col:
    if not has_searched:
        st.info(
            "Search for an ingredient or dish to see recipe ideas.\n\n"
            "Tip: Start with something you already buy, like **\"pasta\"**, "
            "**\"kipfilet\"** or **\"linzen\"**."
        )
        st.stop()
    
    if has_searched and not filtered_recipes:
        st.warning(
            "We didn't find recipes for this search. Try a broader term or relax your filters."
        )
        st.stop()
    
    # Recipe ideas grid
    st.markdown("### Recipe ideas")
    st.caption("Tap a recipe to see details and add ingredients to your basket.")
    
    grid_cols = st.columns(2, gap="large")
    
    for idx, recipe in enumerate(filtered_recipes):
        col = grid_cols[idx % 2]
        
        with col:
            # Use a stable random image from assets for each card
            slot_key = f"recipe_card_{idx}"
            image_path = get_random_asset_image(slot_key)
            
            st.markdown('<div class="nlga-card">', unsafe_allow_html=True)
            
            if image_path:
                st.markdown('<div class="nlga-recipe-card">', unsafe_allow_html=True)
                st.image(image_path, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Title
            st.markdown(f"#### {recipe.title}")
            
            # Tags row
            tags = getattr(recipe, "tags", None) or []
            if tags:
                tag_cols = st.columns(min(len(tags), 3))
                for t_idx, tag in enumerate(tags[:3]):
                    with tag_cols[t_idx]:
                        st.markdown(pill_tag(str(tag)), unsafe_allow_html=True)
            
            # Meta info row
            meta_cols = st.columns(3)
            
            with meta_cols[0]:
                if getattr(recipe, "prep_time_minutes", None) is not None:
                    st.caption(f"⏱️ ~{recipe.prep_time_minutes} min")
            
            with meta_cols[1]:
                if getattr(recipe, "servings", None) is not None:
                    st.caption(f"👨‍👩‍👧‍👦 Base: {recipe.servings} servings")
                else:
                    st.caption(f"👨‍👩‍👧‍👦 Base: 2 servings")
            
            with meta_cols[2]:
                if getattr(recipe, "health_label", None):
                    st.caption(f"🥦 {recipe.health_label}")
            
            # Expandable details area
            with st.expander("View details & add to basket"):
                # Description
                if getattr(recipe, "description", None):
                    st.markdown(recipe.description)
                
                # Ingredients section
                st.markdown("### 🛒 Ingredients")
                ingredients_list = "\n".join([f"• {ing}" for ing in recipe.ingredients])
                st.markdown(ingredients_list)
                
                st.markdown("---")
                
                # Instructions section
                st.markdown("### 👨‍🍳 Instructions")
                for inst_idx, instruction in enumerate(recipe.instructions, 1):
                    st.markdown(f"**{inst_idx}.** {instruction}")
                
                st.markdown("---")
                
                # Household-aware serving hint
                profile_key_current = st.session_state.get("household_profile_key")
                profile_current = get_profile_by_key(profile_key_current)
                if profile_current and hasattr(recipe, "servings") and recipe.servings:
                    adjusted_servings = int(recipe.servings * profile_current.serving_multiplier)
                    st.caption(f"For your household: ~{adjusted_servings} servings")
                elif profile_current:
                    # Use default base servings if recipe doesn't have servings field
                    base_servings_default = 2
                    adjusted_servings = int(base_servings_default * profile_current.serving_multiplier)
                    st.caption(f"For your household: ~{adjusted_servings} servings")
                
                # Add ingredients to basket button
                if st.button(
                    "🛒 Add ingredients to basket",
                    key=f"add_ingredients_{recipe.id}",
                    width='stretch',
                    type="primary"
                ):
                    handle_add_recipe_to_basket(recipe, session_id)
            
            st.markdown('</div>', unsafe_allow_html=True)

# Footer
render_footer()
