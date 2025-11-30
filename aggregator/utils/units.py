"""
Unit and quantity normalization utilities.

This module provides pure helper functions for parsing and normalizing product
quantities and units across different connector formats. All functions are
stateless and have no side effects (no I/O, no network calls).

# NOTE: These helpers normalize the various unit formats used by different
    retailers into a canonical format for consistent comparison and display.
"""

import re
from typing import Optional, Tuple


# Canonical unit mappings
_CANONICAL_UNITS = {
    # Volume
    "l": "L",
    "liter": "L",
    "ltr": "L",
    "litre": "L",
    "ml": "mL",
    "milliliter": "mL",
    "millilitre": "mL",
    
    # Mass
    "kg": "kg",
    "kilogram": "kg",
    "g": "g",
    "gram": "g",
    "gr": "g",
    
    # Pieces/units
    "st": "piece",
    "stuk": "piece",
    "stuks": "piece",
    "piece": "piece",
    "pieces": "piece",
    "pcs": "piece",
    "pc": "piece",
    "x": "piece",  # Common in "6 x 250ml"
}


def canonicalize_unit(unit: str) -> str:
    """
    Normalize unit strings to canonical form.
    
    Converts synonyms and variants to a canonical set:
    - Volume: "l", "liter", "ltr" -> "L"; "ml", "milliliter" -> "mL"
    - Mass: "kg", "kilogram" -> "kg"; "g", "gram", "gr" -> "g"
    - Pieces: "st", "stuk", "stuks", "piece", "pieces", "pcs", "x" -> "piece"
    
    Args:
        unit: Unit string to normalize (case-insensitive)
        
    Returns:
        Canonical unit string (L, mL, kg, g, piece), or original string if not recognized
        
    Examples:
        >>> canonicalize_unit("ltr")
        'L'
        >>> canonicalize_unit("STUKS")
        'piece'
        >>> canonicalize_unit("unknown")
        'unknown'
    """
    if not unit:
        return unit
    
    unit_lower = unit.lower().strip()
    return _CANONICAL_UNITS.get(unit_lower, unit)


def parse_quantity_and_unit(raw_size_str: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Parse quantity and unit from size strings.
    
    Handles various formats such as:
    - "1 kg", "500 g", "2 x 330 ml", "6-pack x 250ml", "3 stuks", etc.
    
    Args:
        raw_size_str: Size string to parse (e.g., "1 kg", "2 x 330 ml", "6-pack x 250ml")
        
    Returns:
        Tuple of (quantity, unit) where:
        - quantity: Numeric quantity (float) or None if parsing fails
        - unit: Canonical unit string (kg, g, L, mL, piece) or None if parsing fails
        
    Examples:
        >>> parse_quantity_and_unit("1 kg")
        (1.0, 'kg')
        >>> parse_quantity_and_unit("2 x 330 ml")
        (660.0, 'mL')
        >>> parse_quantity_and_unit("6-pack x 250ml")
        (1500.0, 'mL')
        >>> parse_quantity_and_unit("3 stuks")
        (3.0, 'piece')
    """
    if not raw_size_str or not isinstance(raw_size_str, str):
        return None, None
    
    raw_size_str = raw_size_str.strip()
    if not raw_size_str:
        return None, None
    
    # Pattern 1: Multi-pack formats like "2 x 330 ml", "6-pack x 250ml", "3x 500g"
    multi_pack_pattern = r"(\d+(?:[\.,]\d+)?)\s*(?:-?pack\s*)?[xX×]\s*(\d+(?:[\.,]\d+)?)\s*([a-zA-Z]+)"
    match = re.search(multi_pack_pattern, raw_size_str, re.IGNORECASE)
    if match:
        try:
            multiplier = float(match.group(1).replace(",", "."))
            quantity = float(match.group(2).replace(",", "."))
            unit_str = match.group(3)
            total_quantity = multiplier * quantity
            canonical_unit = canonicalize_unit(unit_str)
            return total_quantity, canonical_unit
        except (ValueError, IndexError):
            pass
    
    # Pattern 2: Simple formats like "1 kg", "500 g", "1L", "250ml", "3 stuks"
    simple_pattern = r"(\d+(?:[\.,]\d+)?)\s*([a-zA-Z]+)"
    match = re.search(simple_pattern, raw_size_str, re.IGNORECASE)
    if match:
        try:
            quantity = float(match.group(1).replace(",", "."))
            unit_str = match.group(2)
            canonical_unit = canonicalize_unit(unit_str)
            return quantity, canonical_unit
        except (ValueError, IndexError):
            pass
    
    # If no pattern matches, return None
    return None, None


def compute_price_per_unit(
    price: float,
    quantity: Optional[float],
    quantity_unit: Optional[str],
) -> Tuple[Optional[float], Optional[str]]:
    """
    Compute price per canonical unit.
    
    Converts price to standard units:
    - For mass: price per kg (converts grams to kg)
    - For volume: price per L (converts mL to L)
    - For pieces: price per piece
    
    Args:
        price: Total price in EUR
        quantity: Total quantity (e.g., 500, 1.5, 6)
        quantity_unit: Unit for quantity (kg, g, L, mL, piece)
        
    Returns:
        Tuple of (price_per_unit, unit_for_price_per_unit) where:
        - price_per_unit: Price per canonical unit (per kg, per L, or per piece)
        - unit_for_price_per_unit: Unit string ("kg", "L", or "piece")
        Returns (None, None) if not computable
        
    Examples:
        >>> compute_price_per_unit(2.00, 500.0, "g")
        (4.0, 'kg')
        >>> compute_price_per_unit(1.50, 1.0, "L")
        (1.5, 'L')
        >>> compute_price_per_unit(3.00, 6.0, "piece")
        (0.5, 'piece')
    """
    if price <= 0 or quantity is None or quantity <= 0 or not quantity_unit:
        return None, None
    
    canonical_unit = canonicalize_unit(quantity_unit)
    
    # Convert to canonical units and compute price per unit
    if canonical_unit in ("g", "kg"):
        # Mass: convert to price per kg
        if canonical_unit == "g":
            quantity_kg = quantity / 1000.0
        else:  # kg
            quantity_kg = quantity
        if quantity_kg > 0:
            return price / quantity_kg, "kg"
    
    elif canonical_unit in ("mL", "L"):
        # Volume: convert to price per L
        if canonical_unit == "mL":
            quantity_l = quantity / 1000.0
        else:  # L
            quantity_l = quantity
        if quantity_l > 0:
            return price / quantity_l, "L"
    
    elif canonical_unit == "piece":
        # Pieces: price per piece
        return price / quantity, "piece"
    
    # Unknown unit, cannot compute
    return None, None

