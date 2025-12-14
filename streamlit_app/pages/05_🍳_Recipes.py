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
from pathlib import Path

from utils import recipes_data
from utils.session import get_or_create_session_id
from utils.api_client import search_products, add_to_cart_backend
from utils.profile import get_profile_by_key, HOUSEHOLD_PROFILES
from streamlit_app.utils.recipes_data import Recipe
from ui.styles import load_global_styles
from ui.layout import page_header, section, card
from ui.style import render_footer  # Keep footer function
from ui.style import pill_tag  # Keep pill_tag helper
from ui.feedback import show_empty_state, working_spinner

# Assets directory for recipe images
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


def get_recipes_by_id() -> Dict[str, Recipe]:
    """
    Get a dictionary mapping recipe IDs to Recipe objects.
    
    Returns:
        Dictionary with recipe IDs as keys and Recipe objects as values
    """
    recipes = recipes_data.get_all_recipes()
    return {r.id: r for r in recipes}


def get_recipe_image_path(recipe: Recipe) -> Optional[Path]:
    """
    Get the image path for a recipe if available.
    
    Args:
        recipe: Recipe object with optional image_filename
        
    Returns:
        Path to image file if exists, None otherwise
    """
    if recipe.image_filename:
        path = ASSETS_DIR / recipe.image_filename
        return path if path.exists() else None
    return None


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
    
    with working_spinner("Working…"):
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
load_global_styles()

# Add recipe tag pill CSS and planned badge CSS
st.markdown(
    """
    <style>
    .recipe-tag {
        display: inline-block;
        background-color: #eef2ff;
        border-radius: 999px;
        padding: 2px 8px;
        margin: 0 4px 4px 0;
        font-size: 0.75rem;
        color: #1f2933;
        white-space: nowrap;
    }
    
    .recipe-planned-badge {
        display: inline-block;
        background-color: #22c55e;
        color: white;
        border-radius: 999px;
        padding: 2px 8px;
        font-size: 0.75rem;
        float: right;
        margin-top: 4px;
    }
    
    .recipe-claim {
        display: inline-block;
        background-color: #f5f5f4;  /* warm beige */
        border-radius: 999px;
        padding: 2px 10px;
        margin: 0 4px 4px 0;
        font-size: 0.75rem;
        color: #44403c;
        white-space: nowrap;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Category chips configuration
CATEGORY_CHIPS = [
    ("All", None),
    ("Quick", "quick"),
    ("High protein", "high-protein"),
    ("Vegetarian", "vegetarian"),
    ("Budget-friendly", "budget-friendly"),
    ("Family", "family-friendly"),
    ("Healthy", "healthy"),
]

# Page header with basket button
page_header(
    title="Recipes",
    subtitle="Simple, healthy meal ideas tailored to your household.",
    right=_render_basket_button
)

# Short caption + optional expander
profile_key = st.session_state.get("household_profile_key", "single")
profile = get_profile_by_key(profile_key)
st.caption(f"Recipes scaled for **{profile.label.lower()}** household.")

with st.expander("How recipes work", expanded=False):
    st.markdown("""
    - Browse recipes by meal type, dietary preferences, or search terms
    - View ingredients and cooking steps for any recipe
    - Add recipe ingredients to your shopping basket with one click
    """)

# Get session ID for basket operations (persists across page navigations)
session_id = get_or_create_session_id()

# Prepare basket button function for header
from ui.layout import get_basket_count

def _render_basket_button():
    basket_count = get_basket_count(session_id)
    basket_label = f"🧺 Basket ({basket_count})" if basket_count > 0 else "🧺 Basket"
    if st.button(basket_label, key="header_basket_btn_recipes", use_container_width=True):
        st.switch_page("pages/03_🧺_My_Basket.py")

# Initialize planned recipes tracking
if "planned_recipes" not in st.session_state:
    st.session_state["planned_recipes"] = set()

# Initialize category chip selection
if "selected_category_tag" not in st.session_state:
    st.session_state["selected_category_tag"] = None  # None = All

# Category chip bar
st.markdown("#### Categories")
chip_cols = st.columns(len(CATEGORY_CHIPS))

for idx, (label, tag) in enumerate(CATEGORY_CHIPS):
    is_active = st.session_state["selected_category_tag"] == tag
    button_label = f"● {label}" if is_active else label
    
    if chip_cols[idx].button(button_label, key=f"chip_{idx}"):
        st.session_state["selected_category_tag"] = tag

st.markdown("")  # Spacing

# Filters-on-left, cards-on-right layout
filters_col, grid_col = st.columns([1, 3], gap="large")

# Left column: Filters
with filters_col:
    st.markdown("### Filters")
    
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
    
    st.caption("Filter by ingredient, diet, time or style.")

# Determine effective tag filter (chip takes precedence over dropdown)
chip_tag = st.session_state.get("selected_category_tag")
if chip_tag is not None:
    # Chip takes precedence over dropdown
    effective_tag_filter = chip_tag
else:
    # Use dropdown value if no chip is selected
    effective_tag_filter = selected_tag if selected_tag != "All" else None

# Cache recipe filtering
@st.cache_data(ttl=300)  # Cache for 5 minutes (recipes don't change often)
def get_filtered_recipes_cached(
    meal_type: Optional[str],
    tag: Optional[str],
    search_text: Optional[str]
) -> List[Recipe]:
    """Get filtered recipes with caching."""
    return recipes_data.filter_recipes(
        meal_type=meal_type,
        tag=tag,
        search_text=search_text
    )

# Get filtered recipes (cached)
recipes = get_filtered_recipes_cached(
    meal_type=selected_meal_type if selected_meal_type != "All" else None,
    tag=effective_tag_filter,
    search_text=search_text if search_text and search_text.strip() else None
)

def render_recipe_card(recipe: Recipe, profile, session_id: str) -> None:
    """
    Render a compact recipe card.
    
    Args:
        recipe: Recipe object to display
        profile: HouseholdProfile object for serving hints
        session_id: Session ID for event logging
    """
    with card():
        # Title
        st.markdown(f"**{recipe.title}**")
        
        # 1-line summary (description)
        if getattr(recipe, "description", None):
            st.caption(recipe.description[:100] + "..." if len(recipe.description) > 100 else recipe.description)
        
        # Tags as pills (compact)
        if getattr(recipe, "tags", None) and recipe.tags:
            tags_html = " ".join(
                f"<span class='recipe-tag'>{tag}</span>" for tag in sorted(recipe.tags)[:5]  # Limit to 5 tags
            )
            st.markdown(tags_html, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
        
        # Add ingredients button
        if st.button("Add ingredients", key=f"add_ing_{recipe.id}", use_container_width=True):
            # Handle adding ingredients to basket
            added_count = handle_add_recipe_to_basket(recipe, session_id)
            if added_count > 0:
                st.toast("✅ Added to basket", icon="✅")
                st.rerun()
            else:
                st.toast("⚠️ Error", icon="⚠️")
        
        # Details expander (serves as "View" functionality - always available, collapsed by default)
        with st.expander("View ingredients & steps", expanded=False):
                # Log recipe viewed event once per session
                viewed_flag_key = f"recipe_{recipe.id}_viewed"
                if not st.session_state.get(viewed_flag_key, False):
                    try:
                        from aggregator.events import log_recipe_viewed
                        log_recipe_viewed(
                            session_id=session_id,
                            recipe_id=recipe.id,
                            recipe_name=recipe.title,
                            associated_items_count=len(recipe.ingredients),
                        )
                    except Exception:
                        pass
                    st.session_state[viewed_flag_key] = True
                
                # Meta info
                meal_type_display = getattr(recipe, "meal_type", "Unknown")
                prep_time = getattr(recipe, "prep_time_minutes", None)
                if prep_time:
                    st.caption(f"{meal_type_display} • {prep_time} min")
                
                # Ingredients
                st.markdown("**Ingredients**")
                for item in recipe.ingredients:
                    st.markdown(f"- {item}")
                
                # Steps
                st.markdown("**Steps**")
                if hasattr(recipe, "instructions") and recipe.instructions:
                    for i, step in enumerate(recipe.instructions, start=1):
                        st.markdown(f"{i}. {step}")
                else:
                    st.caption("Instructions not available.")
                
                # Price if available
                if getattr(recipe, "estimated_price_eur", None) is not None:
                    st.markdown(f"**Estimated cost:** €{recipe.estimated_price_eur:.2f}")


def render_planned_summary() -> None:
    """
    Render a summary panel showing all planned recipes for the week.
    """
    st.markdown("### 🗒️ Planned recipes")
    
    planned_ids = st.session_state.get("planned_recipes", set())
    if not planned_ids:
        st.caption(
            "No recipes planned yet. Click **Plan this recipe** on any card to start a simple meal plan."
        )
        return
    
    recipes_by_id = get_recipes_by_id()
    planned_recipes = [recipes_by_id[rid] for rid in planned_ids if rid in recipes_by_id]
    
    st.caption(f"You have planned **{len(planned_recipes)}** recipe(s) this week.")
    
    for r in planned_recipes:
        price_str = (
            f"€{r.estimated_price_eur:.2f}"
            if getattr(r, "estimated_price_eur", None) is not None
            else "Price TBD"
        )
        prep_time = getattr(r, "prep_time_minutes", "N/A")
        meal_type = getattr(r, "meal_type", "Unknown")
        
        st.markdown(
            f"- **{r.title}**  \n"
            f"  {price_str} · {prep_time} min · {meal_type}"
        )
    
    # Small hint linking to other pages
    st.markdown(
        """
        <small>
        Tip: Use the <b>🗓 Meal Planner</b> page (in the sidebar) to assign these recipes to days of the week.
        <br><br>
        Later, you can use these planned recipes to build your basket and analyze health:
        <br>- Go to <b>🧺 My Basket</b> to assemble ingredients
        <br>- Go to <b>📊 Health Insights</b> to see how healthy your groceries look
        </small>
        """,
        unsafe_allow_html=True,
    )
    
    # Demo-only clear button
    if st.button("Clear all planned recipes"):
        st.session_state["planned_recipes"] = set()
        st.info("Cleared all planned recipes for this session.")


# Right column: Recipe cards grid + Planned summary
with grid_col:
    # Split right column into grid (left) and summary (right)
    grid_content_col, summary_col = st.columns([3, 1], gap="large")
    
    with grid_content_col:
        if not recipes:
            show_empty_state(
                title="No recipes found",
                subtitle="Try clearing the filters or searching for 'pasta', 'kipfilet', or 'havermout'.",
                action_label="Clear filters",
                action_page_path=None  # Stay on same page
            )
        else:
            # Results count
            st.markdown(f"**Found {len(recipes)} recipe(s)**")
            
            # Limit to 9 recipes for 3x3 grid
            max_cards = 9
            recipes_to_show = recipes[:max_cards]
            
            # Create 3-column grid
            cols = st.columns(3, gap="large")
            
            for idx, recipe in enumerate(recipes_to_show):
                col = cols[idx % 3]
                with col:
                    render_recipe_card(recipe, profile, session_id)
    
    with summary_col:
        render_planned_summary()

# Footer
render_footer()
