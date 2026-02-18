from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models import Expense
from schemas import ExpenseCreate
from typing import Optional
import uuid
from sqlalchemy.exc import IntegrityError, OperationalError, DatabaseError
import time

MAX_DB_RETRIES = 3

def save_expense_with_retry(db, expense):
    """Retry saving expense for transient DB errors."""
    for attempt in range(MAX_DB_RETRIES):
        try:
            db.add(expense)
            db.commit()
            db.refresh(expense)
            return expense
        except (OperationalError, DatabaseError) as e:
            db.rollback()
            if attempt < MAX_DB_RETRIES - 1:
                # Exponential backoff: 1, 2, 4 seconds
                time.sleep(2 ** attempt)
            else:
                # Give up after last attempt
                raise e

def create_expense(db: Session, expense_in: ExpenseCreate) -> tuple[Expense, bool]:
    """
    Create a new expense. If idempotency_key already exists, return the existing
    record without creating a duplicate. Returns (expense, was_created).
    """
    existing = (
        db.query(Expense)
        .filter(Expense.idempotency_key == expense_in.idempotency_key)
        .first()
    )
    if existing:
        return existing, False  

    new_expense = Expense(
        id=str(uuid.uuid4()),
        idempotency_key=expense_in.idempotency_key,
        amount=expense_in.amount,
        category=expense_in.category.strip(),
        description=expense_in.description,
        date=expense_in.date,
    )

    try:
        saved_expense = save_expense_with_retry(db,new_expense)
        return saved_expense, True
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(Expense)
            .filter(Expense.idempotency_key == expense_in.idempotency_key)
            .first()
        )
        return existing, False


def get_expenses(
    db: Session,
    category: Optional[str] = None,
    sort_desc: bool = True,
) -> list[Expense]:
    """
    Fetch expenses with optional category filter, sorted by date.
    sort_desc=True means newest first.
    """
    query = db.query(Expense)

    if category:
        query = query.filter(Expense.category.ilike(f"%{category.strip()}%"))

    if sort_desc:
        query = query.order_by(Expense.date.desc(), Expense.created_at.desc())
    else:
        query = query.order_by(Expense.date.asc(), Expense.created_at.asc())

    return query.all()


def get_all_categories(db: Session) -> list[str]:
    """Return distinct categories for filter dropdown."""
    rows = db.query(Expense.category).distinct().order_by(Expense.category).all()
    return [r[0] for r in rows]