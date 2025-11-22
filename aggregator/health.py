from typing import Dict, Any


UNHEALTHY_KEYWORDS = ["chips", "snoep", "chocolate", "cola", "bier", "wine"]
HEALTHY_KEYWORDS = ["groente", "fruit", "salade", "volkoren", "whole grain", "noten"]


def tag_health(product: Dict[str, Any]) -> str:
    name = (product.get("name") or "").lower()
    if any(k in name for k in HEALTHY_KEYWORDS):
        return "healthy"
    if any(k in name for k in UNHEALTHY_KEYWORDS):
        return "unhealthy"
    return "neutral"
