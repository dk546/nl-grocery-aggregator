"""
Database persistence layer for carts and price history.

This module provides an optional Postgres-backed persistence layer that can be
enabled by setting the DATABASE_URL environment variable. If DATABASE_URL is not
set, the module provides a no-op interface that allows the code to fall back
to in-memory storage (for carts) or JSONL files (for price history).

When DATABASE_URL is set:
- Carts are stored in Postgres tables
- Price history is stored in Postgres tables

When DATABASE_URL is not set:
- db_is_enabled() returns False
- All DB operations are skipped, allowing fallback to in-memory/file storage
"""

import os
import logging
import time
import json
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
DB_ENABLED = bool(DATABASE_URL)

# SQLAlchemy imports (optional - only used if DB_ENABLED)
if DB_ENABLED:
    try:
        from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Index, Text
        from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
        from sqlalchemy.sql import func
        SQLALCHEMY_AVAILABLE = True
    except ImportError:
        logger.warning("DATABASE_URL is set but SQLAlchemy is not installed. Install with: pip install sqlalchemy psycopg2-binary")
        SQLALCHEMY_AVAILABLE = False
        DB_ENABLED = False
else:
    SQLALCHEMY_AVAILABLE = False

# Base class for SQLAlchemy models (only used if DB_ENABLED)
Base = declarative_base() if (DB_ENABLED and SQLALCHEMY_AVAILABLE) else None

# Database engine and session factory (only created if DB_ENABLED)
engine = None
SessionLocal = None

if DB_ENABLED and SQLALCHEMY_AVAILABLE:
    try:
        # Create engine with connection pooling
        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,  # Verify connections before using
            echo=False,  # Set to True for SQL query logging
        )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        logger.info("Database connection initialized (DATABASE_URL is set)")
    except Exception as e:
        logger.error(f"Failed to initialize database connection: {e}")
        DB_ENABLED = False
        engine = None
        SessionLocal = None


# SQLAlchemy ORM Models (only used if DB_ENABLED)
if DB_ENABLED and SQLALCHEMY_AVAILABLE and Base is not None:
    
    class CartSession(Base):
        """Cart session table - one row per session_id."""
        __tablename__ = "cart_sessions"
        
        id = Column(Integer, primary_key=True, index=True)
        session_id = Column(String(255), unique=True, index=True, nullable=False)
        created_at = Column(DateTime, server_default=func.now(), nullable=False)
        updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
        
        # Relationship to cart items
        items = relationship("CartItemRow", back_populates="cart_session", cascade="all, delete-orphan")
    
    class CartItemRow(Base):
        """Cart items table - stores individual items in carts."""
        __tablename__ = "cart_items"
        
        id = Column(Integer, primary_key=True, index=True)
        cart_session_id = Column(Integer, ForeignKey("cart_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
        retailer = Column(String(50), nullable=False)
        product_id = Column(String(255), nullable=False)
        name = Column(String(500), nullable=False)
        price_eur = Column(Float, nullable=False)
        quantity = Column(Integer, nullable=False, default=1)
        image_url = Column(String(1000), nullable=True)
        health_tag = Column(String(50), nullable=True)
        
        # Relationship to cart session
        cart_session = relationship("CartSession", back_populates="items")
        
        # Index for faster lookups
        __table_args__ = (
            Index("idx_cart_item_key", "cart_session_id", "retailer", "product_id"),
        )
    
    class PriceHistoryRow(Base):
        """Price history table - stores price points for products."""
        __tablename__ = "price_history"
        
        id = Column(Integer, primary_key=True, index=True)
        product_id = Column(String(255), nullable=False, index=True)
        retailer = Column(String(50), nullable=False, index=True)
        ts = Column(Float, nullable=False, index=True)  # Unix timestamp
        price_eur = Column(Float, nullable=False)
        created_at = Column(DateTime, server_default=func.now(), nullable=False)
        
        # Composite index for faster queries
        __table_args__ = (
            Index("idx_price_history_lookup", "product_id", "retailer", "ts"),
        )
    
    class EventRow(Base):
        """Events table - stores analytics events for user actions."""
        __tablename__ = "events"
        
        id = Column(Integer, primary_key=True, index=True)
        ts = Column(DateTime, nullable=False, index=True)  # UTC timestamp
        session_id = Column(String(255), nullable=True, index=True)
        event_type = Column(String(100), nullable=False, index=True)
        payload = Column(Text, nullable=True)  # JSON string
        
        # Index for faster queries by event_type and timestamp
        __table_args__ = (
            Index("idx_event_type_ts", "event_type", "ts"),
        )


def db_is_enabled() -> bool:
    """
    Check if database persistence is enabled.
    
    Returns:
        True if DATABASE_URL is set and SQLAlchemy is available, False otherwise
    """
    return DB_ENABLED and SQLALCHEMY_AVAILABLE and engine is not None and SessionLocal is not None


def init_db() -> None:
    """
    Initialize database tables (create if they don't exist).
    
    This function is safe to call multiple times - it only creates tables
    that don't already exist.
    
    Raises:
        Exception: If database connection fails or table creation fails
    """
    if not db_is_enabled():
        logger.debug("Database not enabled, skipping init_db()")
        return
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized (or already exist)")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")
        raise


def get_db_session():
    """
    Get a database session.
    
    Returns:
        SQLAlchemy Session object
        
    Raises:
        RuntimeError: If database is not enabled
    """
    if not db_is_enabled():
        raise RuntimeError("Database is not enabled. Set DATABASE_URL environment variable.")
    
    return SessionLocal()


# ============================================================================
# Cart Repository Functions
# ============================================================================

def db_get_cart_items(session_id: str) -> List[dict]:
    """
    Get all cart items for a session from the database.
    
    Args:
        session_id: Session identifier
        
    Returns:
        List of cart item dictionaries matching CartItem model structure
    """
    if not db_is_enabled():
        return []
    
    db = get_db_session()
    try:
        # Find or create cart session
        cart_session = db.query(CartSession).filter(CartSession.session_id == session_id).first()
        
        if not cart_session:
            return []
        
        # Get all items for this session
        items = db.query(CartItemRow).filter(CartItemRow.cart_session_id == cart_session.id).all()
        
        # Convert to dict format matching CartItem model
        result = []
        for item in items:
            result.append({
                "retailer": item.retailer,
                "product_id": item.product_id,
                "name": item.name,
                "price_eur": item.price_eur,
                "quantity": item.quantity,
                "image_url": item.image_url,
                "health_tag": item.health_tag,
            })
        
        return result
    finally:
        db.close()


def db_replace_cart(session_id: str, items: List[dict]) -> None:
    """
    Replace all cart items for a session in the database.
    
    This clears existing items and inserts new ones (upsert pattern).
    
    Args:
        session_id: Session identifier
        items: List of cart item dictionaries matching CartItem model structure
    """
    if not db_is_enabled():
        return
    
    db = get_db_session()
    try:
        # Find or create cart session
        cart_session = db.query(CartSession).filter(CartSession.session_id == session_id).first()
        
        if not cart_session:
            cart_session = CartSession(session_id=session_id)
            db.add(cart_session)
            db.commit()
            db.refresh(cart_session)
        else:
            # Delete all existing items
            db.query(CartItemRow).filter(CartItemRow.cart_session_id == cart_session.id).delete()
        
        # Insert new items
        for item_data in items:
            cart_item = CartItemRow(
                cart_session_id=cart_session.id,
                retailer=item_data.get("retailer", ""),
                product_id=item_data.get("product_id", ""),
                name=item_data.get("name", ""),
                price_eur=float(item_data.get("price_eur", 0.0)),
                quantity=int(item_data.get("quantity", 1)),
                image_url=item_data.get("image_url"),
                health_tag=item_data.get("health_tag"),
            )
            db.add(cart_item)
        
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error replacing cart in database: {e}")
        raise
    finally:
        db.close()


def db_clear_cart(session_id: str) -> None:
    """
    Clear all cart items for a session in the database.
    
    Args:
        session_id: Session identifier
    """
    if not db_is_enabled():
        return
    
    db = get_db_session()
    try:
        cart_session = db.query(CartSession).filter(CartSession.session_id == session_id).first()
        
        if cart_session:
            # Delete all items
            db.query(CartItemRow).filter(CartItemRow.cart_session_id == cart_session.id).delete()
            db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error clearing cart in database: {e}")
        raise
    finally:
        db.close()


# ============================================================================
# Price History Repository Functions
# ============================================================================

def db_record_price_points(points: List[Tuple[str, str, float]]) -> None:
    """
    Record price points in the database.
    
    Args:
        points: List of tuples (product_id, retailer, price_eur)
    """
    if not db_is_enabled():
        return
    
    if not points:
        return
    
    db = get_db_session()
    try:
        current_time = time.time()
        
        for product_id, retailer, price_eur in points:
            if not product_id or not retailer or price_eur <= 0:
                continue
            
            price_row = PriceHistoryRow(
                product_id=str(product_id),
                retailer=str(retailer),
                ts=current_time,
                price_eur=float(price_eur),
            )
            db.add(price_row)
        
        db.commit()
    except Exception as e:
        db.rollback()
        logger.debug(f"Error recording price points in database: {e}")
        # Fail silently for price history (non-critical)
    finally:
        db.close()


def db_get_price_history(product_id: str, retailer: str, limit: int = 30) -> List[dict]:
    """
    Get price history for a product from the database.
    
    Args:
        product_id: Product identifier (may include retailer prefix)
        retailer: Retailer identifier
        limit: Maximum number of points to return
        
    Returns:
        List of dictionaries with "ts" and "price_eur" keys
    """
    if not db_is_enabled():
        return []
    
    db = get_db_session()
    try:
        # Normalize product_id - handle both "retailer:id" and just "id" formats
        product_id_clean = product_id.split(":")[-1] if ":" in product_id else product_id
        
        # Query price history
        # Match by retailer and product_id (handle both formats)
        query = db.query(PriceHistoryRow).filter(
            PriceHistoryRow.retailer == retailer
        )
        
        # Filter by product_id (handle both full and clean formats)
        # We'll match if the stored product_id ends with the clean ID or vice versa
        results = query.all()
        
        # Filter in Python to handle product_id format variations
        matching_points = []
        for row in results:
            stored_id_clean = row.product_id.split(":")[-1] if ":" in row.product_id else row.product_id
            if stored_id_clean == product_id_clean and row.ts > 0 and row.price_eur > 0:
                matching_points.append({
                    "ts": row.ts,
                    "price_eur": row.price_eur,
                })
        
        # Sort by timestamp (oldest first), then take the most recent 'limit' items
        matching_points.sort(key=lambda p: p["ts"])
        return matching_points[-limit:] if len(matching_points) > limit else matching_points
        
    except Exception as e:
        logger.debug(f"Error getting price history from database: {e}")
        return []
    finally:
        db.close()


# ============================================================================
# Database Statistics Functions
# ============================================================================

def get_cart_sessions_count() -> int:
    """
    Get the total number of cart sessions in the database.
    
    Returns:
        Number of cart sessions (0 if DB is not enabled or on error)
    """
    if not db_is_enabled():
        return 0
    
    db = get_db_session()
    try:
        count = db.query(CartSession).count()
        return count
    except Exception as e:
        logger.debug(f"Error counting cart sessions: {e}")
        return 0
    finally:
        db.close()


def get_price_history_count() -> int:
    """
    Get the total number of price history records in the database.
    
    Returns:
        Number of price history records (0 if DB is not enabled or on error)
    """
    if not db_is_enabled():
        return 0
    
    db = get_db_session()
    try:
        count = db.query(PriceHistoryRow).count()
        return count
    except Exception as e:
        logger.debug(f"Error counting price history records: {e}")
        return 0
    finally:
        db.close()


# ============================================================================
# Events Repository Functions
# ============================================================================

def db_log_event(
    event_type: str,
    session_id: Optional[str],
    payload: Optional[Dict[str, Any]],
) -> None:
    """
    Insert a single event row into the database.
    
    This function is designed to fail silently - any errors are logged but
    do not propagate, ensuring analytics never break the application.
    
    Args:
        event_type: Event type/name (e.g., "search_performed", "cart_item_added")
        session_id: Session identifier (optional)
        payload: Event-specific data dictionary (will be stored as JSON string)
    """
    if not db_is_enabled():
        return
    
    db = None
    try:
        db = get_db_session()
        
        # Convert payload dict to JSON string
        payload_json = json.dumps(payload) if payload else None
        
        # Create UTC datetime from current time
        event_ts = datetime.utcnow()
        
        event_row = EventRow(
            ts=event_ts,
            session_id=session_id,
            event_type=event_type,
            payload=payload_json,
        )
        
        db.add(event_row)
        db.commit()
    except Exception as e:
        if db:
            try:
                db.rollback()
            except Exception:
                pass
        logger.debug(f"Error logging event to database: {e}")
        # Fail silently - analytics should never break the app
    finally:
        if db:
            try:
                db.close()
            except Exception:
                pass


def db_get_recent_events(limit: int = 100) -> List[Any]:
    """
    Return most recent events ordered by timestamp (descending).
    
    Args:
        limit: Maximum number of events to return (default: 100)
        
    Returns:
        List of EventRow objects, or empty list if DB disabled or on error
    """
    if not db_is_enabled():
        return []
    
    db = get_db_session()
    try:
        # EventRow is only available when DB_ENABLED is True
        if DB_ENABLED and SQLALCHEMY_AVAILABLE and Base is not None:
            events = db.query(EventRow).order_by(EventRow.ts.desc()).limit(limit).all()
            return events
        else:
            return []
    except Exception as e:
        logger.debug(f"Error getting recent events from database: {e}")
        return []
    finally:
        db.close()


def db_get_event_counts(
    since_hours: int = 24,
) -> Dict[str, int]:
    """
    Return a dictionary of event type counts over the last N hours.
    
    Args:
        since_hours: Number of hours to look back (default: 24)
        
    Returns:
        Dictionary mapping event_type to count, or empty dict if DB disabled or on error
    """
    if not db_is_enabled():
        return {}
    
    db = get_db_session()
    try:
        # Calculate cutoff time
        from datetime import timedelta
        cutoff_time = datetime.utcnow() - timedelta(hours=since_hours)
        
        # Query events since cutoff time
        events = db.query(EventRow).filter(EventRow.ts >= cutoff_time).all()
        
        # Count by event_type
        counts: Dict[str, int] = {}
        for event in events:
            event_type = event.event_type
            counts[event_type] = counts.get(event_type, 0) + 1
        
        return counts
    except Exception as e:
        logger.debug(f"Error getting event counts from database: {e}")
        return {}
    finally:
        db.close()

