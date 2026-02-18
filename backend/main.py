from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from decimal import Decimal
from typing import Optional

import models
import crud
import schemas
from database import engine, get_db

# Create all tables on startup if they don't exist
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Expense Tracker API",
    description="A personal finance expense tracker API with idempotent expense creation.",
    version="1.0.0",
)

# CORS — allow Streamlit Cloud and local dev to reach this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Tighten this in production if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "Expense Tracker API is running."}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}


@app.post(
    "/expenses",
    response_model=schemas.ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Expenses"],
    summary="Create a new expense (idempotent)",
)
def create_expense(
    expense_in: schemas.ExpenseCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new expense entry.

    - **Idempotent**: If you send the same `idempotency_key` more than once
      (e.g., due to a retry on a slow network), the API will return the original
      record without creating a duplicate.
    - If `idempotency_key` is omitted, a new UUID is auto-generated.
    """
    expense, was_created = crud.create_expense(db, expense_in)

    if not was_created:
        # Return 200 (not 201) to signal idempotent replay
        from fastapi.responses import JSONResponse
        from fastapi.encoders import jsonable_encoder
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder(schemas.ExpenseResponse.model_validate(expense)),
        )

    return expense


@app.get(
    "/expenses",
    response_model=schemas.ExpenseListResponse,
    tags=["Expenses"],
    summary="List expenses with optional filter and sort",
)
def list_expenses(
    category: Optional[str] = Query(default=None, description="Filter by category (partial match)"),
    sort_date_desc: bool = Query(default=True, description="Sort by date descending (newest first)"),
    db: Session = Depends(get_db),
):
    """
    Retrieve all expenses.

    - Filter by `category` (case-insensitive partial match).
    - Sort by date: `sort_date_desc=true` (default) = newest first.
    - Response includes a running `total` of the filtered/sorted result set.
    """
    expenses = crud.get_expenses(db, category=category, sort_desc=sort_date_desc)
    # Convert to Pydantic
    expenses_pydantic = [schemas.ExpenseResponse.model_validate(e) for e in expenses]
    total = sum((e.amount for e in expenses_pydantic), Decimal("0.00"))
    return schemas.ExpenseListResponse(expenses=expenses_pydantic, total=total, count=len(expenses_pydantic))


@app.get(
    "/expenses/categories",
    response_model=list[str],
    tags=["Expenses"],
    summary="Get all distinct categories",
)
def list_categories(db: Session = Depends(get_db)):
    """Returns all unique categories currently in the database, for use in filter dropdowns."""
    return crud.get_all_categories(db)