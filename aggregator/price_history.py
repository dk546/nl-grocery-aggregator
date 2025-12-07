"""
Price history tracking module (demo feature).

This module provides functionality to record and retrieve price history for products.
This is a demo feature that uses a local JSONL file for storage.

Note: Data resets when the backend restarts (ephemeral file system on Render).
"""

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

# Price history file (JSONL format)
PRICE_HISTORY_FILE = Path("price_history.jsonl")


@dataclass
class PricePoint:
    """A single price point in the history."""
    ts: float  # Timestamp
    price_eur: float  # Price in euros


def record_prices_for_products(products: List[dict]) -> None:
    """
    Record prices for a list of products to the price history file.
    
    This is a demo feature that writes to a local JSONL file. Data will be lost
    when the backend restarts (especially on Render's ephemeral file system).
    
    Args:
        products: List of product dictionaries with at least 'id', 'retailer', and 'price_eur' fields
    """
    try:
        if not products:
            return
        
        # Ensure the file exists (create if needed)
        PRICE_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        with PRICE_HISTORY_FILE.open("a", encoding="utf-8") as f:
            current_time = time.time()
            for p in products:
                # Skip if missing required fields
                if not p.get("id") or not p.get("retailer"):
                    continue
                
                price_eur = p.get("price_eur") or p.get("price")
                if price_eur is None or price_eur <= 0:
                    continue
                
                try:
                    price_eur = float(price_eur)
                except (ValueError, TypeError):
                    continue
                
                record = {
                    "ts": current_time,
                    "product_id": str(p["id"]),
                    "retailer": str(p["retailer"]),
                    "price_eur": price_eur,
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        
        logger.debug("Recorded prices for %d products to price history", len(products))
    except Exception as e:
        # Fail silently; this is a demo helper
        logger.debug("Error recording price history: %s", str(e), exc_info=True)


def get_price_history(product_id: str, retailer: str, limit: int = 30) -> List[PricePoint]:
    """
    Get price history for a specific product.
    
    Args:
        product_id: Product identifier (may include retailer prefix like "ah:123" or just "123")
        retailer: Retailer identifier (ah, jumbo, picnic, dirk)
        limit: Maximum number of points to return (default: 30)
        
    Returns:
        List of PricePoint objects, sorted by timestamp (oldest first)
    """
    points: List[PricePoint] = []
    
    try:
        if not PRICE_HISTORY_FILE.exists():
            return []
        
        # Normalize product_id - handle both "retailer:id" and just "id" formats
        product_id_clean = product_id.split(":")[-1] if ":" in product_id else product_id
        
        with PRICE_HISTORY_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line.strip())
                    if not rec:
                        continue
                    
                    # Match by retailer and product_id (handle both formats)
                    rec_product_id = str(rec.get("product_id", ""))
                    rec_product_id_clean = rec_product_id.split(":")[-1] if ":" in rec_product_id else rec_product_id
                    rec_retailer = str(rec.get("retailer", ""))
                    
                    if rec_product_id_clean == product_id_clean and rec_retailer == retailer:
                        ts = float(rec.get("ts", 0))
                        price = float(rec.get("price_eur", 0))
                        
                        if ts > 0 and price > 0:
                            points.append(PricePoint(ts=ts, price_eur=price))
                except (json.JSONDecodeError, ValueError, KeyError, TypeError):
                    # Skip malformed lines
                    continue
        
        # Sort by timestamp (oldest first) and limit
        points.sort(key=lambda p: p.ts)
        return points[:limit] if len(points) > limit else points
        
    except Exception as e:
        logger.debug("Error reading price history: %s", str(e), exc_info=True)
        return []