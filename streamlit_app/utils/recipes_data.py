"""
Recipes Data Module.

This module contains a curated collection of healthy recipes. Currently uses a
static, hard-coded list of recipes, but is designed to be easily replaced or
extended with external data sources.

# NOTE: This is a v1 implementation with static data. The recipes are kept simple
    and healthy-ish to align with the app's theme of supporting healthier grocery choices.

# TODO: Future enhancements:
    - Load recipes from JSON/YAML configuration files
    - Sync with external recipe APIs (e.g., Spoonacular, Edamam)
    - Support localization (translations, ingredient names per region)
    - User-contributed recipes
    - Recipe ratings and reviews
    - Nutritional information per recipe
    - Estimated cost per serving based on current prices
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Recipe:
    """
    Recipe data model.
    
    Attributes:
        id: Unique identifier for the recipe
        title: Recipe name/title
        description: Short description of the recipe
        meal_type: Type of meal (e.g., "Breakfast", "Lunch", "Dinner", "Snack")
        difficulty: Difficulty level (e.g., "Easy", "Medium", "Hard")
        prep_time_minutes: Preparation time in minutes
        tags: List of tags/categories (e.g., ["high protein", "quick", "budget"])
        ingredients: List of ingredient names (simple strings)
        instructions: List of step-by-step instruction strings
    """
    id: str
    title: str
    description: str
    meal_type: str
    difficulty: str
    prep_time_minutes: int
    tags: List[str]
    ingredients: List[str]
    instructions: List[str]


# Curated recipe collection
_RECIPES = [
    Recipe(
        id="recipe_001",
        title="Overnight Oats with Fresh Fruit",
        description="A nutritious and convenient breakfast that's ready when you wake up. Perfect for meal prep!",
        meal_type="Breakfast",
        difficulty="Easy",
        prep_time_minutes=10,
        tags=["quick", "vegetarian", "meal-prep", "budget-friendly"],
        ingredients=[
            "rolled oats",
            "greek yogurt",
            "milk",
            "honey",
            "banana",
            "berries",
            "nuts (optional)"
        ],
        instructions=[
            "Mix rolled oats, greek yogurt, and milk in a jar or container",
            "Add a drizzle of honey and stir well",
            "Cover and refrigerate overnight (at least 4 hours)",
            "In the morning, top with sliced banana, fresh berries, and nuts if desired",
            "Enjoy cold or at room temperature"
        ]
    ),
    Recipe(
        id="recipe_002",
        title="Chickpea & Veggie Power Bowl",
        description="A colorful, protein-packed bowl with roasted vegetables and creamy chickpeas.",
        meal_type="Lunch",
        difficulty="Easy",
        prep_time_minutes=25,
        tags=["high-protein", "vegetarian", "healthy", "one-pot"],
        ingredients=[
            "chickpeas",
            "sweet potato",
            "bell peppers",
            "red onion",
            "olive oil",
            "lemon",
            "spinach",
            "feta cheese"
        ],
        instructions=[
            "Preheat oven to 200°C",
            "Drain and rinse chickpeas, then pat dry",
            "Cut sweet potato, bell peppers, and red onion into chunks",
            "Toss vegetables and chickpeas with olive oil and spread on baking sheet",
            "Roast for 20-25 minutes until vegetables are tender",
            "Serve over fresh spinach, drizzle with lemon juice, and top with feta"
        ]
    ),
    Recipe(
        id="recipe_003",
        title="Baked Salmon with Roasted Vegetables",
        description="Simple and elegant: tender salmon with colorful roasted vegetables. Rich in omega-3s!",
        meal_type="Dinner",
        difficulty="Easy",
        prep_time_minutes=30,
        tags=["high-protein", "healthy", "gluten-free"],
        ingredients=[
            "salmon fillets",
            "asparagus",
            "cherry tomatoes",
            "zucchini",
            "olive oil",
            "lemon",
            "garlic",
            "herbs (dill or parsley)"
        ],
        instructions=[
            "Preheat oven to 190°C",
            "Place salmon fillets on a baking sheet lined with parchment paper",
            "Arrange asparagus, cherry tomatoes, and sliced zucchini around the salmon",
            "Drizzle everything with olive oil and lemon juice",
            "Season with minced garlic, salt, and herbs",
            "Bake for 15-20 minutes until salmon is cooked through and vegetables are tender",
            "Serve immediately with extra lemon wedges"
        ]
    ),
    Recipe(
        id="recipe_004",
        title="Hearty Lentil Soup",
        description="Warming and comforting soup packed with protein and fiber. Perfect for batch cooking!",
        meal_type="Lunch",
        difficulty="Easy",
        prep_time_minutes=35,
        tags=["vegetarian", "budget-friendly", "meal-prep", "high-protein"],
        ingredients=[
            "red lentils",
            "carrots",
            "celery",
            "onion",
            "garlic",
            "vegetable broth",
            "tomatoes",
            "cumin",
            "paprika"
        ],
        instructions=[
            "Chop carrots, celery, and onion into small pieces",
            "Heat olive oil in a large pot and sauté vegetables until softened",
            "Add minced garlic and spices, cook for 1 minute",
            "Add rinsed lentils and vegetable broth",
            "Bring to a boil, then reduce heat and simmer for 20-25 minutes",
            "Add diced tomatoes and cook for another 5 minutes",
            "Season with salt and pepper. Serve hot with fresh herbs"
        ]
    ),
    Recipe(
        id="recipe_005",
        title="Greek Yogurt Parfait",
        description="Layered with fruit and granola for a protein-rich snack or light breakfast.",
        meal_type="Snack",
        difficulty="Easy",
        prep_time_minutes=5,
        tags=["quick", "high-protein", "vegetarian", "budget-friendly"],
        ingredients=[
            "greek yogurt",
            "granola",
            "honey",
            "berries",
            "banana"
        ],
        instructions=[
            "In a glass or bowl, layer greek yogurt and granola",
            "Add a drizzle of honey between layers",
            "Top with fresh berries and sliced banana",
            "Repeat layers if desired",
            "Enjoy immediately"
        ]
    ),
    Recipe(
        id="recipe_006",
        title="Simple Veggie Stir-Fry",
        description="Quick and colorful stir-fry that comes together in minutes. Customize with your favorite vegetables!",
        meal_type="Dinner",
        difficulty="Easy",
        prep_time_minutes=15,
        tags=["quick", "vegetarian", "budget-friendly", "healthy"],
        ingredients=[
            "mixed vegetables (bell peppers, broccoli, carrots)",
            "soy sauce",
            "garlic",
            "ginger",
            "sesame oil",
            "rice or noodles"
        ],
        instructions=[
            "Cut vegetables into bite-sized pieces",
            "Heat sesame oil in a large pan or wok over high heat",
            "Add minced garlic and ginger, stir for 30 seconds",
            "Add vegetables and stir-fry for 5-7 minutes until crisp-tender",
            "Add soy sauce and cook for another minute",
            "Serve over cooked rice or noodles"
        ]
    ),
    Recipe(
        id="recipe_007",
        title="Veggie Omelette",
        description="A protein-packed breakfast or quick dinner. Load it up with your favorite vegetables!",
        meal_type="Breakfast",
        difficulty="Easy",
        prep_time_minutes=10,
        tags=["quick", "high-protein", "vegetarian", "budget-friendly"],
        ingredients=[
            "eggs",
            "mushrooms",
            "spinach",
            "tomatoes",
            "cheese",
            "olive oil"
        ],
        instructions=[
            "Whisk eggs in a bowl with a pinch of salt and pepper",
            "Heat olive oil in a non-stick pan over medium heat",
            "Sauté mushrooms and spinach until softened",
            "Pour eggs into the pan and let set slightly",
            "Add chopped tomatoes and cheese on one half",
            "When eggs are almost set, fold in half and cook for another minute",
            "Slide onto plate and serve hot"
        ]
    ),
    Recipe(
        id="recipe_008",
        title="Wholegrain Pasta with Tomato & Beans",
        description="A satisfying pasta dish with protein-rich beans and fresh tomatoes. Comforting and nutritious!",
        meal_type="Dinner",
        difficulty="Easy",
        prep_time_minutes=20,
        tags=["vegetarian", "high-protein", "budget-friendly", "family-friendly"],
        ingredients=[
            "wholegrain pasta",
            "cannellini beans",
            "cherry tomatoes",
            "garlic",
            "olive oil",
            "basil",
            "parmesan cheese"
        ],
        instructions=[
            "Cook pasta according to package directions",
            "Meanwhile, heat olive oil in a large pan",
            "Add halved cherry tomatoes and sauté until they start to burst",
            "Add minced garlic and cook for 1 minute",
            "Add drained cannellini beans and heat through",
            "Toss with cooked pasta and fresh basil",
            "Serve with grated parmesan cheese"
        ]
    ),
]


def get_all_recipes() -> List[Recipe]:
    """
    Get all available recipes.
    
    Returns:
        List of all Recipe objects
    """
    return _RECIPES.copy()


def get_meal_types() -> List[str]:
    """
    Get unique meal types across all recipes.
    
    Returns:
        Sorted list of unique meal types
    """
    meal_types = {recipe.meal_type for recipe in _RECIPES}
    return sorted(list(meal_types))


def get_tag_options() -> List[str]:
    """
    Get all unique tags used across recipes.
    
    Returns:
        Sorted list of unique tags (deduplicated)
    """
    all_tags = set()
    for recipe in _RECIPES:
        all_tags.update(recipe.tags)
    return sorted(list(all_tags))


def filter_recipes(
    meal_type: Optional[str] = None,
    tag: Optional[str] = None,
    search_text: Optional[str] = None
) -> List[Recipe]:
    """
    Filter recipes by meal type, tag, and/or search text.
    
    Args:
        meal_type: Filter by meal type (e.g., "Breakfast"). If None or empty, no filtering.
        tag: Filter by tag (e.g., "quick"). If None or empty, no filtering.
        search_text: Search in title and description (case-insensitive). If None or empty, no filtering.
    
    Returns:
        Filtered list of Recipe objects matching all criteria
    """
    recipes = _RECIPES.copy()
    
    if meal_type and meal_type != "All":
        recipes = [r for r in recipes if r.meal_type == meal_type]
    
    if tag and tag != "All":
        recipes = [r for r in recipes if tag in r.tags]
    
    if search_text and search_text.strip():
        search_lower = search_text.lower()
        recipes = [
            r for r in recipes
            if search_lower in r.title.lower() or search_lower in r.description.lower()
        ]
    
    return recipes

