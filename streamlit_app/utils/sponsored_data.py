"""
Sponsored deals data and filtering logic for monetization.

This module provides a static configuration of sponsored products that can be
displayed alongside search results. In a production deployment, this would be
replaced with real ad inventory from an advertising platform.

For MVP, sponsored deals are simple static configurations filtered by:
- Search query keywords (simple substring matching)
- Selected retailers
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SponsoredDeal:
    """Represents a sponsored product deal."""
    id: str
    title: str
    retailer: str  # "ah", "jumbo", "picnic", "dirk"
    price_eur: float
    promo_text: str
    image_url: Optional[str] = None
    product_url: Optional[str] = None  # External link to retailer/product page
    tags: Optional[List[str]] = None  # Categories, e.g. ["healthy", "budget", "dairy"]
    keywords: Optional[List[str]] = None  # For simple matching with search query


# Static mock inventory – adjust as you like
# In production, this would be replaced with dynamic ad inventory from an ad platform
SPONSORED_DEALS: List[SponsoredDeal] = [
    SponsoredDeal(
        id="s1",
        title="AH Organic Wholegrain Pasta 500g",
        retailer="ah",
        price_eur=0.99,
        promo_text="Sponsored: Organic pasta at a sharp price.",
        image_url=None,
        product_url="https://www.ah.nl/producten/product/wi12345",  # Placeholder URL
        tags=["pasta", "organic", "budget"],
        keywords=["pasta", "spaghetti", "macaroni", "noodles"],
    ),
    SponsoredDeal(
        id="s2",
        title="Jumbo Fresh Chicken Fillet 1kg",
        retailer="jumbo",
        price_eur=5.49,
        promo_text="Sponsored: Family pack chicken fillet.",
        image_url=None,
        product_url="https://www.jumbo.com/product/123456",  # Placeholder URL
        tags=["meat", "protein"],
        keywords=["kip", "kipfilet", "chicken", "kip filet"],
    ),
    SponsoredDeal(
        id="s3",
        title="Picnic Seasonal Fruit Mix",
        retailer="picnic",
        price_eur=3.29,
        promo_text="Sponsored: Fresh fruit mix for the week.",
        image_url=None,
        product_url="https://picnic.app/product/fruitmix",  # Placeholder URL
        tags=["fruit", "healthy"],
        keywords=["fruit", "appel", "banaan", "druiven", "fruitmix"],
    ),
    SponsoredDeal(
        id="s4",
        title="AH Dutch Milk 1L",
        retailer="ah",
        price_eur=1.19,
        promo_text="Sponsored: Fresh Dutch milk.",
        image_url=None,
        product_url="https://www.ah.nl/producten/product/wi67890",
        tags=["dairy", "healthy"],
        keywords=["melk", "milk", "zuivel"],
    ),
    SponsoredDeal(
        id="s5",
        title="Jumbo Wholegrain Bread",
        retailer="jumbo",
        price_eur=1.79,
        promo_text="Sponsored: Fresh wholegrain bread.",
        image_url=None,
        product_url="https://www.jumbo.com/product/789012",
        tags=["bread", "healthy"],
        keywords=["brood", "bread", "volkoren"],
    ),
]


def get_sponsored_deals_for_search(
    query: Optional[str] = None,
    retailer_codes: Optional[List[str]] = None,
    max_deals: int = 3,
) -> List[SponsoredDeal]:
    """
    Filter sponsored deals based on current search context.
    
    Very simple filter:
    - Only deals from selected retailers (if provided)
    - If query is present, prefer deals whose keywords match the query
    - Fallback to top N deals if nothing matches
    
    Args:
        query: Search query string (optional)
        retailer_codes: List of retailer codes to filter by (optional)
        max_deals: Maximum number of deals to return (default: 3)
        
    Returns:
        List of SponsoredDeal objects matching the criteria
    """
    if retailer_codes is None:
        retailer_codes = []
    
    query = (query or "").strip().lower()
    has_query = bool(query)
    
    # First, filter by retailer selection
    candidates = [
        d for d in SPONSORED_DEALS
        if not retailer_codes or d.retailer in retailer_codes
    ]
    
    if not candidates:
        return []
    
    if has_query:
        def matches_query(deal: SponsoredDeal) -> bool:
            """Check if deal matches the search query."""
            if deal.keywords:
                for kw in deal.keywords:
                    if kw and kw.lower() in query:
                        return True
            # Loose fallback: query substring in title
            return query in deal.title.lower()
        
        matched = [d for d in candidates if matches_query(d)]
        if matched:
            return matched[:max_deals]
    
    # Fallback: top N candidates (e.g., "always-on" sponsorship)
    return candidates[:max_deals]

