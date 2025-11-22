from typing import List, Dict, Any, Iterable, Optional

from .connectors.ah_connector import AHRetailConnector
from .connectors.jumbo_connector import JumboRetailConnector
from .connectors.picnic_connector import PicnicRetailConnector
from .health import tag_health  # if you split it out



RETAILER_MAP = {
    "ah": AHRetailConnector,
    "jumbo": JumboRetailConnector,
    "picnic": PicnicRetailConnector,
}


def get_connectors(retailers: Iterable[str]):
    for r in retailers:
        cls = RETAILER_MAP.get(r)
        if not cls:
            continue
        try:
            yield cls()
        except Exception as e:
            # Log and skip problematic connector
            print(f"Error initializing connector {r}: {e}")


def aggregated_search(
    query: str,
    retailers: Iterable[str],
    size_per_retailer: int = 10,
    page: int = 0,
    sort_by: str = "price",
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    for connector in get_connectors(retailers):
        try:
            items = connector.search_products(query=query, size=size_per_retailer, page=page)
            for item in items:
                item["health_tag"] = tag_health(item)
            results.extend(items)
        except Exception as e:
            print(f"Error searching {connector.retailer}: {e}")

    # TODO: de-duplicate using EAN/barcode if we can extract it later.
    if sort_by == "price":
        results.sort(key=lambda p: (p.get("price_eur") or 999999))
    return results
