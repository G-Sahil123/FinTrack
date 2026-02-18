# 💸 Expense Tracker

A minimal full-stack personal finance tool built with **FastAPI + PostgreSQL** (backend) and **Streamlit** (frontend).

---

## Features

- Add expenses with amount, category, description, and date
- View all expenses in a sortable, filterable list (newest first by default)
- Filter by category (partial match, case-insensitive)
- Running total displayed after every filter/sort
- Summary view: total per category
- Idempotent expense creation — safe to retry on network failures
- Client and server-side validation (no negative or zero amounts, no blank categories)
- Error and loading states throughout the UI

---

## Project Structure

```
FINTRACK/
├── backend/
│   ├── main.py          
│   ├── database.py     
│   ├── models.py        
│   ├── schemas.py       
│   ├── crud.py          
│   ├── requirements.txt
├── frontend/
│   ├── app.py           
│   ├── requirements.txt
└── README.md
```

---

## Local Development

### 1. Backend

```bash
cd backend

pip install -r requirements.txt
uvicorn main:app --reload
```

API will be available at `http://localhost:8000`.
Interactive docs at `http://localhost:8000/docs`.

### 2. Frontend

```bash
cd frontend
pip install -r requirements.txt

# Set the backend URL
export API_BASE_URL=http://localhost:8000

streamlit run app.py
```

---

## Deployment

### Backend → Render

1. Push this repo to GitHub.
2. Go to [render.com](https://render.com) → New Web Service → connect your repo.
3. Set **Root Directory** to `backend`.
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Add environment variable `DATABASE_URL` in the Render dashboard (Settings → Environment).
7. Deploy.

### Frontend → Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io) → New app.
2. Point to `frontend/app.py` in your repo.
3. In **Secrets**, add:
   ```
   API_BASE_URL = "https://your-render-service.onrender.com"
   ```
4. Deploy.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `POST` | `/expenses` | Create a new expense |
| `GET` | `/expenses` | List expenses (with optional filters) |
| `GET` | `/expenses/categories` | List all distinct categories |

### POST /expenses — Request body

```json
{
  "idempotency_key": "uuid-string (optional, auto-generated if omitted)",
  "amount": "499.00",
  "category": "Food",
  "description": "Lunch at cafe",
  "date": "2026-02-19"
}
```

### GET /expenses — Query params

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `category` | string | — | Partial category filter |
| `sort_date_desc` | bool | `true` | Newest first |

---

## Key Design Decisions

**Idempotency** — The frontend generates a `uuid4` per form session and sends it with every POST. If a user clicks "Save" twice due to a slow network, or the page refreshes mid-request, the second identical request returns the original record without creating a duplicate. The key rotates after a successful save.

**Money handling** — `DECIMAL(10,2)` in MySQL, Python `Decimal` everywhere. `float` is never used for amounts because floating-point arithmetic is unsuitable for financial data.

**No float in JSON** — Amounts are serialised as strings in the API response to avoid JSON float precision issues. The Streamlit frontend wraps them in `Decimal()` before any arithmetic.

**Validation layers** — Client-side in Streamlit (immediate UX feedback) + server-side in Pydantic (source of truth). The backend rejects negative/zero amounts even if the frontend is bypassed.

**Pool pre-ping** — `pool_pre_ping=True` in SQLAlchemy ensures stale DB connections are detected and recycled, which matters on free-tier cloud databases that close idle connections.

---

## Trade-offs / What Was Intentionally Not Done

- **No authentication** — Out of scope for the assignment. In production, add JWT or OAuth2.
- **No pagination** — Kept simple; acceptable for a personal tool with modest data.
- **No soft delete** — No delete endpoint implemented; add if needed.
- **CORS is wide open** — `allow_origins=["*"]` is fine for this scope. Restrict to your Streamlit domain in production.