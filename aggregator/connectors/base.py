from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseConnector(ABC):
    retailer: str

    @abstractmethod
    def search_products(self, query: str, size: int = 10, page: int = 0) -> List[Dict[str, Any]]:
        """Return a list of normalized product dicts"""

    @abstractmethod
    def get_delivery_slots(self) -> Any:
        """Return delivery slots structure (connector-specific)"""
