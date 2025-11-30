"""
Tests for unit and quantity normalization utilities.

This module tests the helper functions in aggregator.utils.units for parsing
and normalizing product quantities and units across different formats.
"""

import pytest

from aggregator.utils.units import (
    parse_quantity_and_unit,
    canonicalize_unit,
    compute_price_per_unit,
)


class TestCanonicalizeUnit:
    """Test cases for canonicalize_unit function."""
    
    def test_canonicalize_volume_units(self):
        """Test volume unit canonicalization."""
        assert canonicalize_unit("l") == "L"
        assert canonicalize_unit("L") == "L"
        assert canonicalize_unit("liter") == "L"
        assert canonicalize_unit("ltr") == "L"
        assert canonicalize_unit("ml") == "mL"
        assert canonicalize_unit("milliliter") == "mL"
    
    def test_canonicalize_mass_units(self):
        """Test mass unit canonicalization."""
        assert canonicalize_unit("kg") == "kg"
        assert canonicalize_unit("kilogram") == "kg"
        assert canonicalize_unit("g") == "g"
        assert canonicalize_unit("gram") == "g"
        assert canonicalize_unit("gr") == "g"
    
    def test_canonicalize_piece_units(self):
        """Test piece/unit canonicalization."""
        assert canonicalize_unit("st") == "piece"
        assert canonicalize_unit("stuk") == "piece"
        assert canonicalize_unit("stuks") == "piece"
        assert canonicalize_unit("piece") == "piece"
        assert canonicalize_unit("pieces") == "piece"
        assert canonicalize_unit("pcs") == "piece"
        assert canonicalize_unit("x") == "piece"
    
    def test_canonicalize_unknown_units(self):
        """Test that unknown units are returned as-is."""
        assert canonicalize_unit("unknown") == "unknown"
        assert canonicalize_unit("") == ""
        assert canonicalize_unit("foo") == "foo"


class TestParseQuantityAndUnit:
    """Test cases for parse_quantity_and_unit function."""
    
    def test_parse_simple_formats(self):
        """Test parsing simple quantity formats."""
        qty, unit = parse_quantity_and_unit("1 kg")
        assert qty == 1.0
        assert unit == "kg"
        
        qty, unit = parse_quantity_and_unit("500 g")
        assert qty == 500.0
        assert unit == "g"
        
        qty, unit = parse_quantity_and_unit("1L")
        assert qty == 1.0
        assert unit == "L"
        
        qty, unit = parse_quantity_and_unit("250ml")
        assert qty == 250.0
        assert unit == "mL"
        
        qty, unit = parse_quantity_and_unit("3 stuks")
        assert qty == 3.0
        assert unit == "piece"
    
    def test_parse_multi_pack_formats(self):
        """Test parsing multi-pack formats."""
        qty, unit = parse_quantity_and_unit("2 x 330 ml")
        assert qty == 660.0
        assert unit == "mL"
        
        qty, unit = parse_quantity_and_unit("6-pack x 250ml")
        assert qty == 1500.0
        assert unit == "mL"
        
        qty, unit = parse_quantity_and_unit("3x 500g")
        assert qty == 1500.0
        assert unit == "g"
    
    def test_parse_european_number_format(self):
        """Test parsing with European number format (comma as decimal separator)."""
        qty, unit = parse_quantity_and_unit("1,5 kg")
        assert qty == 1.5
        assert unit == "kg"
        
        qty, unit = parse_quantity_and_unit("2,5 x 500ml")
        assert qty == 1250.0
        assert unit == "mL"
    
    def test_parse_invalid_formats(self):
        """Test parsing invalid or unparseable formats."""
        qty, unit = parse_quantity_and_unit("")
        assert qty is None
        assert unit is None
        
        qty, unit = parse_quantity_and_unit("invalid")
        assert qty is None
        assert unit is None
        
        qty, unit = parse_quantity_and_unit(None)
        assert qty is None
        assert unit is None


class TestComputePricePerUnit:
    """Test cases for compute_price_per_unit function."""
    
    def test_compute_price_per_kg_from_grams(self):
        """Test computing price per kg from grams."""
        price_per_unit, unit = compute_price_per_unit(2.00, 500.0, "g")
        assert price_per_unit == 4.0
        assert unit == "kg"
        
        price_per_unit, unit = compute_price_per_unit(1.50, 250.0, "g")
        assert price_per_unit == 6.0
        assert unit == "kg"
    
    def test_compute_price_per_kg_from_kg(self):
        """Test computing price per kg when already in kg."""
        price_per_unit, unit = compute_price_per_unit(3.00, 1.0, "kg")
        assert price_per_unit == 3.0
        assert unit == "kg"
        
        price_per_unit, unit = compute_price_per_unit(2.50, 2.0, "kg")
        assert price_per_unit == 1.25
        assert unit == "kg"
    
    def test_compute_price_per_liter_from_ml(self):
        """Test computing price per L from mL."""
        price_per_unit, unit = compute_price_per_unit(1.20, 500.0, "mL")
        assert price_per_unit == 2.4
        assert unit == "L"
        
        price_per_unit, unit = compute_price_per_unit(0.99, 330.0, "mL")
        assert abs(price_per_unit - 3.0) < 0.01  # Approximate
        assert unit == "L"
    
    def test_compute_price_per_liter_from_liters(self):
        """Test computing price per L when already in L."""
        price_per_unit, unit = compute_price_per_unit(1.50, 1.0, "L")
        assert price_per_unit == 1.5
        assert unit == "L"
        
        price_per_unit, unit = compute_price_per_unit(2.00, 1.5, "L")
        assert abs(price_per_unit - 1.333) < 0.01  # Approximate
        assert unit == "L"
    
    def test_compute_price_per_piece(self):
        """Test computing price per piece."""
        price_per_unit, unit = compute_price_per_unit(3.00, 6.0, "piece")
        assert price_per_unit == 0.5
        assert unit == "piece"
        
        price_per_unit, unit = compute_price_per_unit(4.50, 4.0, "piece")
        assert price_per_unit == 1.125
        assert unit == "piece"
    
    def test_compute_price_per_unit_invalid_inputs(self):
        """Test compute_price_per_unit with invalid inputs."""
        price_per_unit, unit = compute_price_per_unit(0.0, 500.0, "g")
        assert price_per_unit is None
        assert unit is None
        
        price_per_unit, unit = compute_price_per_unit(2.00, None, "g")
        assert price_per_unit is None
        assert unit is None
        
        price_per_unit, unit = compute_price_per_unit(2.00, 500.0, None)
        assert price_per_unit is None
        assert unit is None
        
        price_per_unit, unit = compute_price_per_unit(2.00, 0.0, "g")
        assert price_per_unit is None
        assert unit is None
    
    def test_compute_price_per_unit_unknown_unit(self):
        """Test compute_price_per_unit with unknown units."""
        price_per_unit, unit = compute_price_per_unit(2.00, 500.0, "unknown")
        assert price_per_unit is None
        assert unit is None

