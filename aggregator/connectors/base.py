"""
Base connector abstract class for retailer integrations.

This module defines the abstract base class that all retailer connectors must implement.
It ensures a consistent interface across different retailer APIs, making it easy to add
new retailers to the aggregator system.

All connectors must:
- Implement the retailer attribute (e.g., "ah", "jumbo", "picnic")
- Provide a search_products method that normalizes products into a unified format
- Provide a get_delivery_slots method for delivery slot information (if supported)
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseConnector(ABC):
    """
    Abstract base class for all retailer connectors.
    
    This class defines the interface that all retailer connectors must implement,
    ensuring consistency across different retailer APIs. Each connector handles
    the specifics of its retailer's API while normalizing data into a common format.
    
    Attributes:
        retailer: String identifier for the retailer (e.g., "ah", "jumbo", "picnic")
    """
    retailer: str

    @abstractmethod
    def search_products(self, query: str, size: int = 10, page: int = 0) -> List[Dict[str, Any]]:
        """
        Search for products on the retailer's platform.
        
        Args:
            query: Search query string (e.g., "melk", "brood")
            size: Number of results to return per page
            page: Page number (0-indexed) for pagination
            
        Returns:
            List of normalized product dictionaries. Each dictionary should contain:
            - retailer: Retailer identifier (str)
            - id: Product identifier (str)
            - name: Product name (str)
            - price_eur: Price in euros (float)
            - unit: Unit description (str, optional)
            - unit_size: Size information (str, optional)
            - image_url: URL to product image (str, optional)
            - url: Product URL on retailer website (str, optional)
            - raw: Raw product data from retailer API (dict, optional)
        """
        pass

    @abstractmethod
    def get_delivery_slots(self) -> Any:
        """
        Retrieve available delivery slots for the retailer.
        
        Returns:
            Delivery slots structure (connector-specific format).
            Can be a list of slot dictionaries or any format supported by the retailer API.
            Returns empty list if delivery slots are not supported or not available.
        """
        pass
