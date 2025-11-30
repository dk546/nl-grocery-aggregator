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
from utils.ui_components import render_header

render_header("🍳 Recipes & Ideas", "Healthy inspiration for your next grocery basket")

# Get session ID for basket operations (persists across page navigations)
session_id = get_or_create_session_id()

# Introduction
st.markdown("""
Discover delicious and healthy recipes that you can prepare with ingredients
from Dutch supermarkets. Filter by meal type or dietary preferences to find
your perfect meal inspiration! 🥗
""")

st.caption("💡 **Tip:** Start with one or two simple recipes and gradually build healthier habits. Small changes add up over time!")

st.divider()

# Filters section
st.subheader("🔍 Filter Recipes")

col1, col2, col3 = st.columns(3)

with col1:
    meal_types = ["All"] + recipes_data.get_meal_types()
    selected_meal_type = st.selectbox(
        "Meal Type",
        options=meal_types,
        index=0,
        help="Filter recipes by meal type"
    )

with col2:
    tag_options = ["All"] + recipes_data.get_tag_options()
    selected_tag = st.selectbox(
        "Dietary Preference / Tag",
        options=tag_options,
        index=0,
        help="Filter by tags like 'vegetarian', 'quick', 'high-protein', etc."
    )

with col3:
    search_text = st.text_input(
        "Search",
        placeholder="Search recipes...",
        help="Search in recipe titles and descriptions",
        key="recipe_search"
    )

st.divider()

# Get filtered recipes
filtered_recipes = recipes_data.filter_recipes(
    meal_type=selected_meal_type if selected_meal_type != "All" else None,
    tag=selected_tag if selected_tag != "All" else None,
    search_text=search_text if search_text and search_text.strip() else None
)

# Display results
if not filtered_recipes:
    st.warning("🔍 No recipes match your filters. Try adjusting them or clearing the text search.")
    if st.button("Clear All Filters", type="secondary"):
        st.session_state.recipe_search = ""
        st.rerun()
else:
    # Show count
    st.success(f"📚 Found {len(filtered_recipes)} recipe(s) matching your criteria")

    st.divider()

    # Display recipe cards
    for recipe in filtered_recipes:
        with st.container():
            # Recipe card header
            col_title, col_meta = st.columns([3, 1])
            
            with col_title:
                st.subheader(f"🍽️ {recipe.title}")
            
            with col_meta:
                st.caption(f"⏱️ {recipe.prep_time_minutes} min")
            
            # Description
            st.markdown(f"*{recipe.description}*")
            
            # Metadata badges
            col_badge1, col_badge2, col_badge3 = st.columns(3)
            
            with col_badge1:
                st.caption(f"📅 **Meal:** {recipe.meal_type}")
            
            with col_badge2:
                difficulty_emoji = "🟢" if recipe.difficulty == "Easy" else "🟡" if recipe.difficulty == "Medium" else "🔴"
                st.caption(f"{difficulty_emoji} **Difficulty:** {recipe.difficulty}")
            
            with col_badge3:
                tags_display = ", ".join(recipe.tags)
                st.caption(f"🏷️ **Tags:** {tags_display}")
            
            # Expandable section for ingredients and instructions
            with st.expander("📋 View Ingredients and Instructions", expanded=False):
                # Ingredients section
                st.markdown("### 🛒 Ingredients")
                ingredients_list = "\n".join([f"• {ing}" for ing in recipe.ingredients])
                st.markdown(ingredients_list)
                
                st.markdown("---")
                
                # Instructions section
                st.markdown("### 👨‍🍳 Instructions")
                for idx, instruction in enumerate(recipe.instructions, 1):
                    st.markdown(f"**{idx}.** {instruction}")
                
                st.markdown("---")
                
                # "Add ingredients to basket" button
                if st.button(
                    "🛒 Add Ingredients to Basket",
                    key=f"add_ingredients_{recipe.id}",
                    use_container_width=True,
                    type="primary"
                ):
                    handle_add_recipe_to_basket(recipe, session_id)
            
            st.divider()

st.divider()


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
        retailers: Optional list of retailer codes (e.g., ["ah", "jumbo", "picnic"])
    
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
            f"✅ Added {found_count} product(s) to your basket for **'{recipe.title}'**. "
            f"Could not find matches for: {', '.join(missing[:5])}"
            + (f" (and {len(missing) - 5} more)" if len(missing) > 5 else "")
        )
    else:
        st.success(
            f"✅ Added all {found_count} ingredient(s) for **'{recipe.title}'** to your basket!"
        )
    
    # Offer link to view basket
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🧺 View My Basket", key=f"view_basket_{recipe.id}", use_container_width=True):
            st.switch_page("pages/03_🧺_My_Basket.py")


# Additional information section
st.subheader("💡 Recipe Tips")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    **🥗 Making Healthy Choices:**
    - Start simple with recipes that have fewer ingredients
    - Look for recipes tagged "quick" if you're short on time
    - Meal-prep friendly recipes can save time during busy weeks
    """)

with col2:
    st.markdown("""
    **🛒 Shopping Smart:**
    - Check ingredient lists before you shop
    - Buy seasonal vegetables for better prices
    - Consider batch cooking for meal-prep recipes
    """)

st.divider()

# Future enhancements section
st.caption("""
**🔮 Coming Soon:**
- Add all recipe ingredients to basket with one click
- Recipe ratings and reviews from the community
- Meal planning calendar integration
- Nutritional information per recipe
- Estimated cost per serving based on current prices
- Save favorite recipes to your profile
- Share recipes with friends
""")

# TODO: Future enhancements:
#   - Deep integration with Search & Compare: clicking "Find Ingredients" should
#     navigate to Search & Compare with ingredients pre-populated
#   - "Add Recipe to Meal Plan" functionality
#   - Shopping list generation from selected recipes
#   - Recipe cost estimation based on current product prices
#   - User recipe submission and community features
#   - Recipe dietary filters (vegan, gluten-free, etc.) as separate checkboxes
#   - Recipe favorites/bookmarking
#   - Recipe sharing functionality
