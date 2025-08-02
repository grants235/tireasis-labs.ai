"""
Base model classes and mixins
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID

from ..core.database import Base


class UUIDMixin:
    """Mixin for UUID primary key"""
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)