"""
DEPRECATED: This sandbox script uses the old appiepy library.

We have standardized on Apify scrapers for supermarket data.
Use sandbox/sandbox_ah_connector.py instead to test the AH connector via Apify.

This file is kept for reference only and may not work if appiepy is not installed.

Run:
    python sandbox/sandbox_ah.py
"""

from pprint import pprint

try:
    from appiepy import Product
except ImportError:
    print("⚠️  appiepy is not installed. This script is deprecated.")
    print("Use sandbox/sandbox_ah_connector.py instead to test AH connector via Apify.")
    Product = None


def test_single_product() -> None:
    """Test fetching a single product using appiepy (deprecated)."""
    if Product is None:
        print("Cannot run test - appiepy is not available.")
        return
    
    # TODO: replace this with any real AH product URL you like
    url = "https://www.ah.nl/producten/product/wi193679/lay-s-paprika"

    print(f"Fetching product from AH: {url}")
    print("⚠️  Note: This uses the deprecated appiepy library.")
    print("    Use sandbox/sandbox_ah_connector.py to test via Apify instead.\n")
    
    product = Product(url)

    print("\n=== Raw product dict (first few keys) ===")
    data = product.__dict__
    for key in list(data.keys())[:10]:
        print(f"{key}: {data[key]}")

    print("\n=== Pretty print full product ===")
    pprint(data)


if __name__ == "__main__":
    try:
        test_single_product()
    except Exception as exc:
        print(f"Error while testing AppiePy: {exc}")
        print("\nNote: This script is deprecated. Use sandbox/sandbox_ah_connector.py instead.")
