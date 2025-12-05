"""
Saved basket templates module for storing and retrieving reusable basket configurations.

This module provides an in-memory store for saving basket templates per session.
Templates are stored as simple dictionaries of basket items that can be reapplied
to recreate a saved shopping basket.

Note: This is a process-local, non-persistent implementation suitable for MVP.
In production, this should be replaced with a database-backed solution.
"""

from dataclasses import dataclass, field
from typing import Dict, List
import time
import uuid


@dataclass
class SavedBasketTemplate:
    """Represents a saved basket template."""
    id: str
    name: str
    created_at: float
    items: List[Dict]  # List of basket item dictionaries (same shape as cart items)


# In-memory store: session_id -> template_id -> SavedBasketTemplate
# In production, this would be replaced with a database (e.g., PostgreSQL, Redis)
_TEMPLATES_STORE: Dict[str, Dict[str, SavedBasketTemplate]] = {}


def list_templates_for_session(session_id: str) -> List[SavedBasketTemplate]:
    """
    List all saved templates for a session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        List of SavedBasketTemplate objects, sorted by creation time (newest first)
    """
    templates = list(_TEMPLATES_STORE.get(session_id, {}).values())
    # Sort by created_at descending (newest first)
    templates.sort(key=lambda t: t.created_at, reverse=True)
    return templates


def save_template_for_session(session_id: str, name: str, items: List[Dict]) -> SavedBasketTemplate:
    """
    Save a basket template for a session.
    
    Args:
        session_id: Session identifier
        name: Template name
        items: List of basket item dictionaries to save
        
    Returns:
        Saved SavedBasketTemplate object
    """
    templates = _TEMPLATES_STORE.setdefault(session_id, {})
    template_id = str(uuid.uuid4())
    template = SavedBasketTemplate(
        id=template_id,
        name=name.strip() or "Unnamed basket",
        created_at=time.time(),
        items=items,
    )
    templates[template_id] = template
    return template


def get_template_for_session(session_id: str, template_id: str) -> SavedBasketTemplate | None:
    """
    Retrieve a specific template for a session.
    
    Args:
        session_id: Session identifier
        template_id: Template identifier
        
    Returns:
        SavedBasketTemplate if found, None otherwise
    """
    return _TEMPLATES_STORE.get(session_id, {}).get(template_id)


def delete_template_for_session(session_id: str, template_id: str) -> None:
    """
    Delete a template for a session.
    
    Args:
        session_id: Session identifier
        template_id: Template identifier to delete
    """
    session_templates = _TEMPLATES_STORE.get(session_id)
    if not session_templates:
        return
    
    session_templates.pop(template_id, None)
    
    # Clean up empty session entries
    if not session_templates:
        _TEMPLATES_STORE.pop(session_id, None)

