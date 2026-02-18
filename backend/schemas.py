from pydantic import BaseModel, Field, field_validator
from decimal import Decimal
from datetime import date, datetime
from typing import Optional
import uuid


class ExpenseCreate(BaseModel):
    idempotency_key: str = Field(default_factory=lambda: str(uuid.uuid4()))
    amount: Decimal = Field(..., gt=0, decimal_places=2, description="Must be a positive value")
    category: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=1000)
    date: date

    @field_validator("category")
    @classmethod
    def category_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Category cannot be blank or whitespace")
        return v.strip()

    @field_validator("amount", mode="before")
    @classmethod
    def amount_must_be_positive(cls, v):
        val = Decimal(str(v))
        if val <= 0:
            raise ValueError("Amount must be greater than zero")
        return val


class ExpenseResponse(BaseModel):
    id: str
    idempotency_key: str
    amount: Decimal
    category: str
    description: Optional[str]
    date: date
    created_at: datetime

    model_config = {"from_attributes": True}


class ExpenseListResponse(BaseModel):
    expenses: list[ExpenseResponse]
    total: Decimal
    count: int