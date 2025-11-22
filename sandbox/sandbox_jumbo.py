"""
Sandbox: placeholder for Jumbo API tests.

NOTE:
- python-jumbo-api is an archived project that wraps the Jumbo mobile API.
- This sandbox is a template; the underlying API may have changed.
- It's okay if this fails or returns empty results – it's for exploration only.

Run:
    python sandbox/sandbox_jumbo.py
"""

from pprint import pprint

# If python-jumbo-api doesn't install or work, we can comment this out later.
try:
    from jumbo_api import Jumbo
except ImportError:
    Jumbo = None


def test_jumbo() -> None:
    if Jumbo is None:
        print("python-jumbo-api is not installed or could not be imported.")
        return

    print("Creating Jumbo client...")

    # The library focuses on orders/slots; product search is limited.
    # We'll just inspect what the client can do and print basic info.
    client = Jumbo()

    print("\n=== Jumbo API client created ===")
    print("Available attributes/methods:")
    pprint([m for m in dir(client) if not m.startswith("_")])

    # Depending on what the client supports, you might try:
    # slots = client.timeslots(postcode='1234AB', housenumber='1')
    # pprint(slots)


if __name__ == "__main__":
    try:
        test_jumbo()
    except Exception as exc:
        print(f"Error while testing Jumbo API: {exc}")
