from sqlalchemy import Column, String, Text, Date, DateTime, DECIMAL
from sqlalchemy.dialects.mysql import CHAR
from database import Base
import uuid
from datetime import datetime, timezone


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    idempotency_key = Column(CHAR(36), unique=True, nullable=False, index=True)
    amount = Column(DECIMAL(10, 2), nullable=False)   # Never use float for money
    category = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)