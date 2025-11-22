"""
Sandbox script for testing AH connector using Apify actor.

This script tests the AHConnector which uses Apify's harvestedge/my-actor
scraper to search for Albert Heijn products.

Prerequisites:
- APIFY_TOKEN must be set in .env file at project root
- apify-client must be installed (pip install apify-client)

Run:
    python -m sandbox.sandbox_ah_connector
"""

from pprint import pprint

from aggregator.connectors.ah_connector import AHConnector


def main():
    """Test AH connector with a simple search query."""
    try:
        print("Initializing AH connector with Apify...")
        connector = AHConnector()
        print("AH connector initialized successfully ✅\n")
        
        query = "melk"
        print(f"Searching for '{query}' (size=5, page=0)...")
        results = connector.search_products(query, size=5, page=0)
        
        print(f"\nGot {len(results)} AH results")
        
        if results:
            print("\n=== Product Summary ===")
            for i, p in enumerate(results, 1):
                print(f"{i}. {p['name']} | €{p['price_eur']:.2f}")
            
            # Print full details for first product
            if len(results) > 0:
                print("\n=== Full Details (First Product) ===")
                pprint(results[0])
                
                # Print raw data for inspection
                if len(results) > 1:
                    print("\n=== Raw Data Sample (First Product) ===")
                    pprint(results[0].get("raw", {}))
        else:
            print("No results found. Check:")
            print("  - APIFY_TOKEN is set correctly in .env")
            print("  - The actor harvestedge/my-actor is accessible")
            print("  - Your Apify account has sufficient credits")
        
        print("\n" + "=" * 80)
        
    except RuntimeError as e:
        print(f"\n❌ Runtime Error: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure APIFY_TOKEN is set in .env file at project root")
        print("  2. Check that the token is valid and has access to the actor")
        print("  3. Verify apify-client is installed: pip install apify-client")
    except Exception as exc:
        print(f"\n❌ Unexpected error: {exc}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
