import streamlit as st
import requests
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
import os
import time

# ── Config ────────────────────────────────────────────────────────────────────
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Expense Tracker",
    page_icon="💸",
    layout="centered",
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def post_expense(payload: dict) -> tuple[bool, str, dict | None]:
    """POST /expenses. Returns (success, message, data)."""
    try:
        resp = requests.post(f"{API_BASE}/expenses", json=payload, timeout=10)
        if resp.status_code in (200, 201):
            return True, "Expense saved successfully!", resp.json()
        else:
            detail = resp.json().get("detail", resp.text)
            return False, f"API error {resp.status_code}: {detail}", None
    except requests.exceptions.ConnectionError:
        return False, "Could not connect to the API. Please try again.", None
    except requests.exceptions.Timeout:
        return False, "Request timed out. Your expense may have been saved — please refresh before retrying.", None
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", None

MAX_RETRIES = 3

def post_expense_with_retry(payload: dict) -> tuple[bool, str, dict | None]:
    """
    Calls `post_expense` with retries and exponential backoff.
    """
    for attempt in range(MAX_RETRIES):
        success, message, data = post_expense(payload)
        if success or attempt == MAX_RETRIES - 1:
            return success, message, data
        # Exponential backoff: 2, 4, 8 seconds...
        time.sleep(2 ** attempt)

def fetch_expenses(category: str = "", sort_desc: bool = True) -> tuple[bool, str, dict | None]:
    """GET /expenses. Returns (success, message, data)."""
    params = {"sort_date_desc": str(sort_desc).lower()}
    if category and category != "All":
        params["category"] = category
    try:
        resp = requests.get(f"{API_BASE}/expenses", params=params, timeout=10)
        if resp.status_code == 200:
            return True, "", resp.json()
        else:
            return False, f"API error {resp.status_code}: {resp.text}", None
    except requests.exceptions.ConnectionError:
        return False, "Could not connect to the API.", None
    except requests.exceptions.Timeout:
        return False, "Request timed out while loading expenses.", None
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", None


def fetch_categories() -> list[str]:
    """GET /expenses/categories."""
    try:
        resp = requests.get(f"{API_BASE}/expenses/categories", timeout=10)
        if resp.status_code == 200:
            return ["All"] + resp.json()
        return ["All"]
    except Exception:
        return ["All"]


def format_inr(amount) -> str:
    try:
        return f"₹{Decimal(str(amount)):,.2f}"
    except (InvalidOperation, TypeError):
        return f"₹{amount}"


# ── Session state init ─────────────────────────────────────────────────────────
if "idempotency_key" not in st.session_state:
    st.session_state.idempotency_key = str(uuid.uuid4())

if "submit_result" not in st.session_state:
    st.session_state.submit_result = None # (success: bool, message: str)

if "submitting" not in st.session_state:
    st.session_state.submitting = False

if "pending_expenses" not in st.session_state:
    st.session_state.pending_expenses = []  # List of dicts

# ── Page ───────────────────────────────────────────────────────────────────────
st.title("💸 Expense Tracker")
st.caption("Track your personal expenses. All amounts in ₹.")

st.divider()

# ── Section 1: Add Expense ─────────────────────────────────────────────────────
with st.expander("➕ Add New Expense", expanded=True):
    with st.form("add_expense_form", clear_on_submit=False):
        col1, col2 = st.columns(2)

        with col1:
            amount_str = st.text_input(
                "Amount (₹) *",
                placeholder="e.g. 499.00",
                help="Must be a positive number.",
            )

        with col2:
            category = st.text_input(
                "Category *",
                placeholder="e.g. Food, Transport, Utilities",
                max_chars=100,
            )

        description = st.text_area(
            "Description",
            placeholder="Optional: what was this expense for?",
            max_chars=1000,
            height=80,
        )

        expense_date = st.date_input(
            "Date *",
            value=date.today(),
            max_value=date.today(),
        )

        submitted = st.form_submit_button("Save Expense", type="primary", 
                use_container_width=True,disabled=st.session_state.submitting)

        if submitted:
            # ── Client-side validation ──
            st.session_state.submitting = True
            try:
                errors = []

                try:
                    amount_val = Decimal(amount_str.strip())
                    if amount_val <= 0:
                        errors.append("Amount must be greater than zero.")
                except (InvalidOperation, AttributeError):
                    errors.append("Amount must be a valid positive number (e.g. 250 or 99.99).")

                if not category.strip():
                    errors.append("Category is required.")

                if errors:
                    for err in errors:
                        st.error(err)
                else:
                    payload = {
                        "idempotency_key": st.session_state.idempotency_key,
                        "amount": str(amount_val),
                        "category": category.strip(),
                        "description": description.strip() or None,
                        "date": str(expense_date),
                    }
                    st.session_state.pending_expenses.append({
                        "id": str(uuid.uuid4()),
                        "idempotency_key": st.session_state.idempotency_key,
                        "amount": str(amount_val),
                        "category": category.strip(),
                        "description": description.strip() or None,
                        "date": str(expense_date),
                        "status": "Pending...",
                    })                    

                    with st.spinner("Saving..."):
                        success, message, _ = post_expense_with_retry(payload)

                    for i, exp in enumerate(st.session_state.pending_expenses):
                        if exp["idempotency_key"] == st.session_state.idempotency_key:
                            st.session_state.pending_expenses.pop(i)
                            break

                    if success:
                        # Rotate key so next submission is a fresh expense
                        st.session_state.submit_result = (success, message)
                        st.session_state.idempotency_key = str(uuid.uuid4())
                        st.rerun()
            finally:
                st.session_state.submitting = False

    # Show result outside the form so it persists after rerun
    if st.session_state.submit_result is not None:
        ok, msg = st.session_state.submit_result
        if ok:
            st.success(msg)
        else:
            st.error(msg)
        st.session_state.submit_result = None

st.divider()

# ── Section 2: Filters ─────────────────────────────────────────────────────────
st.subheader("📋 My Expenses")

col_f1, col_f2 = st.columns([2, 1])

with col_f1:
    categories = fetch_categories()
    selected_category = st.selectbox("Filter by Category", options=categories)

with col_f2:
    sort_order = st.selectbox("Sort by Date", options=["Newest First", "Oldest First"])

sort_desc = sort_order == "Newest First"

# ── Section 3: Expense List ────────────────────────────────────────────────────
with st.spinner("Loading expenses..."):
    ok, err_msg, data = fetch_expenses(
        category=selected_category,
        sort_desc=sort_desc,
    )

if not ok:
    st.error(f"⚠️ {err_msg}")
elif data:
    expenses = data.get("expenses", [])
    total = data.get("total", "0.00")
    count = data.get("count", 0)

    if count == 0:
        st.info("No expenses found for the selected filter.")
    else:
        # ── Total banner ──
        st.metric(
            label=f"Total ({count} expense{'s' if count != 1 else ''})",
            value=format_inr(total),
        )

        st.markdown("")

        # ── Per-category summary ──
        if selected_category == "All" and count > 0:
            with st.expander("📊 Summary by Category"):
                cat_totals: dict[str, Decimal] = {}
                for exp in expenses:
                    cat = exp["category"]
                    cat_totals[cat] = cat_totals.get(cat, Decimal("0")) + Decimal(str(exp["amount"]))

                summary_data = [
                    {"Category": cat, "Total": format_inr(amt)}
                    for cat, amt in sorted(cat_totals.items(), key=lambda x: -x[1])
                ]
                st.table(summary_data)

        # ── Expenses table ──
        # ── Pending expenses (optimistic UI) ──
        for exp in st.session_state.pending_expenses:
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    st.markdown(f"**{exp['category']}**")
                    if exp.get("description"):
                        st.caption(exp["description"])
                with c2:
                    st.markdown(f"**{format_inr(exp['amount'])}**")
                with c3:
                    st.caption(f"⏳ {exp['status']}")

        for exp in expenses:
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    st.markdown(f"**{exp['category']}**")
                    if exp.get("description"):
                        st.caption(exp["description"])
                with c2:
                    st.markdown(f"**{format_inr(exp['amount'])}**")
                with c3:
                    st.caption(f"📅 {exp['date']}")