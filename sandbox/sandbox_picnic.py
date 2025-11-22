"""
Sandbox script for testing Picnic API using python-picnic-api package.

HOW PICNIC API WORKS:
--------------------
- Uses python-picnic-api library which handles authentication and API calls
- Requires credentials: username, password, and country_code (default: NL)
- Credentials are loaded from .env file at project root:
    PICNIC_USERNAME=your_username
    PICNIC_PASSWORD=your_password
    PICNIC_COUNTRY_CODE=NL

API METHODS TESTED:
-------------------
1. search(query) - Searches for products by query string
2. get_delivery_slots() - Retrieves available delivery time slots

ERROR HANDLING:
---------------
All API calls are wrapped in try/except blocks with clear error messages.
If credentials are missing or invalid, you'll see specific error messages.

INTERPRETING OUTPUT:
--------------------
- "Script started" - Script initialization
- "Loaded environment variables" - Successfully loaded .env file
- "Creating PicnicAPI client..." - Initializing API client
- "PicnicAPI client created ✅" - Successfully authenticated
- "Searching for 'melk'..." - Starting product search
- "Search completed ✅" - Successfully retrieved results
- Product output shows sample results (max 5 items)
- Delivery slots output shows available time slots (max 5)
"""

import os
import sys
from typing import List, Dict, Any
from pprint import pprint

print("Script started ✅")

# Load environment variables from .env file at project root
try:
    from dotenv import load_dotenv
    
    # Load .env from project root (parent of sandbox/)
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    load_dotenv(env_path)
    print(f"Loaded environment variables from: {env_path} ✅")
except ImportError:
    print("❌ python-dotenv not installed. Install with: pip install python-dotenv")
    sys.exit(1)
except Exception as e:
    print(f"⚠️  Warning: Could not load .env file: {e}")
    print("   Continuing with environment variables from system...")

# Import Picnic API
try:
    from python_picnic_api import PicnicAPI
    print("Imported PicnicAPI ✅")
except ImportError as e:
    print(f"❌ Failed to import PicnicAPI: {e}")
    print("   Install with: pip install python-picnic-api")
    sys.exit(1)


def test_picnic_search(picnic: PicnicAPI):
    """Test Picnic product search with error handling."""
    print("\n" + "=" * 80)
    print("Testing Picnic Product Search")
    print("=" * 80)
    
    try:
        print("Searching for 'melk'...")
        results: List[Dict[str, Any]] = picnic.search("melk")
        print("Search completed ✅")
        
        print(f"\nProducts found: {len(results)}")
        
        if results:
            print("\nFirst 5 products (sample):")
            for i, product in enumerate(results[:5], 1):
                print(f"\n  Product {i}:")
                # Extract key fields for readability
                product_info = {
                    "name": product.get("name") or product.get("title") or "N/A",
                    "id": product.get("id") or "N/A",
                    "price": product.get("price") or product.get("unit_price") or "N/A",
                    "unit": product.get("unit") or product.get("unit_size") or "N/A",
                }
                pprint(product_info, indent=4)
                print("-" * 80)
        else:
            print("⚠️  No products found")
            
    except Exception as e:
        print(f"❌ Search failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


def test_picnic_delivery_slots(picnic: PicnicAPI):
    """Test Picnic delivery slots retrieval with error handling."""
    print("\n" + "=" * 80)
    print("Testing Picnic Delivery Slots")
    print("=" * 80)
    
    try:
        print("Calling get_delivery_slots()...")
        slots = picnic.get_delivery_slots()
        print("Delivery slots retrieved ✅")
        
        if isinstance(slots, list):
            print(f"\nDelivery slots found: {len(slots)}")
            
            if slots:
                print("\nFirst 5 delivery slots (sample):")
                for i, slot in enumerate(slots[:5], 1):
                    print(f"\n  Slot {i}:")
                    # Extract key fields for readability
                    slot_info = {
                        "slot_id": slot.get("slot_id") or slot.get("id") or "N/A",
                        "start_time": slot.get("start_time") or slot.get("start") or "N/A",
                        "end_time": slot.get("end_time") or slot.get("end") or "N/A",
                        "available": slot.get("available", "N/A"),
                    }
                    pprint(slot_info, indent=4)
                    print("-" * 80)
            else:
                print("⚠️  No delivery slots available")
        else:
            print(f"⚠️  Unexpected response type: {type(slots)}")
            print("Raw response (first 500 chars):")
            print(str(slots)[:500])
            
    except Exception as e:
        print(f"❌ get_delivery_slots() failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("PICNIC SANDBOX TEST")
    print("=" * 80)
    
    # Get credentials from environment
    username = os.getenv("PICNIC_USERNAME")
    password = os.getenv("PICNIC_PASSWORD")
    country_code = os.getenv("PICNIC_COUNTRY_CODE", "NL")
    
    # Validate credentials
    if not username:
        print("❌ PICNIC_USERNAME not found in environment variables")
        print("   Please create a .env file in the project root with:")
        print("   PICNIC_USERNAME=your_username")
        print("   PICNIC_PASSWORD=your_password")
        print("   PICNIC_COUNTRY_CODE=NL")
        sys.exit(1)
    
    if not password:
        print("❌ PICNIC_PASSWORD not found in environment variables")
        print("   Please create a .env file in the project root with:")
        print("   PICNIC_USERNAME=your_username")
        print("   PICNIC_PASSWORD=your_password")
        print("   PICNIC_COUNTRY_CODE=NL")
        sys.exit(1)
    
    print(f"\nCredentials loaded:")
    print(f"  Username: {username}")
    print(f"  Country Code: {country_code}")
    print(f"  Password: {'*' * len(password)} (hidden)")
    
    # Create Picnic API client
    try:
        print("\nCreating PicnicAPI client...")
        picnic = PicnicAPI(
            username=username,
            password=password,
            country_code=country_code,
        )
        print("PicnicAPI client created ✅")
    except Exception as e:
        print(f"❌ Failed to create PicnicAPI client: {type(e).__name__}: {e}")
        print("   This usually means authentication failed. Check your credentials.")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Run tests
    test_picnic_search(picnic)
    test_picnic_delivery_slots(picnic)
    
    print("\n" + "=" * 80)
    print("Done ✅")
    print("=" * 80)
