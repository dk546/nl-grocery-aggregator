"""
Sandbox script for testing aggregated search across all retailers.

This script tests the aggregated_search function which searches across
AH, Jumbo, and Picnic, normalizes results, adds health tags, and merges them.

Prerequisites:
- For AH/Jumbo: APIFY_TOKEN must be set in .env file
- For Picnic: PICNIC_USERNAME and PICNIC_PASSWORD must be set in .env file
- Required packages: apify-client, python-picnic-api

Run:
    python -m sandbox.sandbox_search
"""

from pprint import pprint

from aggregator.search import aggregated_search


def run():
    """Test aggregated search across all retailers."""
    try:
        query = "melk"
        retailers = ["ah", "jumbo", "picnic"]
        size_per_retailer = 5
        
        print("=" * 80)
        print(f"Testing Aggregated Search")
        print("=" * 80)
        print(f"\nQuery: '{query}'")
        print(f"Retailers: {', '.join(retailers)}")
        print(f"Size per retailer: {size_per_retailer}")
        print("\nRunning aggregated search...\n")
        
        results = aggregated_search(
            query=query,
            retailers=retailers,
            size_per_retailer=size_per_retailer,
            page=0,
            sort_by="price"
        )
        
        print(f"Total results: {len(results)}")
        
        if results:
            print("\n=== Results Sorted by Price ===")
            for i, product in enumerate(results, 1):
                retailer = product.get("retailer", "unknown")
                name = product.get("name", "N/A")
                price = product.get("price_eur", 0)
                health = product.get("health_tag", "neutral")
                print(f"{i:2d}. [{retailer:6s}] €{price:6.2f} | {health:9s} | {name}")
            
            print("\n=== Breakdown by Retailer ===")
            by_retailer = {}
            for product in results:
                retailer = product.get("retailer", "unknown")
                by_retailer[retailer] = by_retailer.get(retailer, 0) + 1
            
            for retailer, count in sorted(by_retailer.items()):
                print(f"  {retailer}: {count} products")
            
            print("\n=== Breakdown by Health Tag ===")
            by_health = {}
            for product in results:
                health = product.get("health_tag", "neutral")
                by_health[health] = by_health.get(health, 0) + 1
            
            for health, count in sorted(by_health.items()):
                print(f"  {health}: {count} products")
            
            # Print full details for first product
            if len(results) > 0:
                print("\n=== Full Details (First Product - Lowest Price) ===")
                pprint(results[0])
        else:
            print("\n⚠️  No results found. This might indicate:")
            print("  - Missing or invalid APIFY_TOKEN (for AH/Jumbo)")
            print("  - Missing or invalid Picnic credentials (for Picnic)")
            print("  - Actor access issues")
            print("  - Network connectivity issues")
        
        print("\n" + "=" * 80)
        
    except Exception as exc:
        print(f"\n❌ Error during aggregated search: {exc}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run()
