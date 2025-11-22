"""
Sandbox: test AppiePy (Albert Heijn product API).

Run:
    python sandbox/sandbox_ah.py
"""

from pprint import pprint

from appiepy import Product


def test_single_product() -> None:
    # TODO: replace this with any real AH product URL you like
    url = "https://www.ah.nl/producten/product/wi193679/lay-s-paprika"

    print(f"Fetching product from AH: {url}")
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
