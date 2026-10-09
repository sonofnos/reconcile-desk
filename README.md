# ReconcileDesk

A payment reconciliation and ledger dashboard: React/TypeScript frontend, Django/DRF backend, PostgreSQL. Built around the same discipline as the rest of this portfolio (double-entry posting, row-locked concurrency, idempotent writes), in the specific stack combination a target fintech role named.

Live: [reconcile-desk.vercel.app](https://reconcile-desk.vercel.app) (frontend) · [reconcile-desk-api.onrender.com](https://reconcile-desk-api.onrender.com) (API)

## What it does

- **Accounts and transfers.** Every balance change is a matched debit/credit pair in `LedgerEntry`, not a bare balance update. `services.post()` locks both accounts with `select_for_update()` in ascending id order (not from/to order), so two transfers sharing an account can't deadlock each other.
- **Idempotent writes.** Transfers and deposits require an `Idempotency-Key` header. The guard is a unique constraint on the key column, not a check-then-insert: two concurrent requests with the same key race to `INSERT`, the loser catches the `IntegrityError` and replays the winner's response instead of both proceeding.
- **Bank statement reconciliation.** Upload a CSV, each line is matched against the ledger by reference and classified `MATCHED`, `AMOUNT_MISMATCH`, or `MISSING_IN_LEDGER`.

## Stack

- **Backend**: Django 6, Django REST Framework, PostgreSQL (psycopg3), gunicorn
- **Frontend**: React 19, TypeScript, Vite, Axios
- **Tests**: pytest + pytest-django (9 tests, including a real concurrency test against Postgres, not sqlite), Vitest + Testing Library (3 tests)
- **CI**: GitHub Actions, backend tests run against a real `postgres:16-alpine` service container

## Concurrency, for real

`ledger/tests/test_concurrency.py` fires 15 threads at a single account funded for exactly one transfer, each on its own DB connection, and asserts exactly one succeeds and the balance never goes negative. It runs against real Postgres via `TransactionTestCase`, not an in-memory sqlite connection that would mask the row-locking behavior entirely.

## Running it

```bash
# Backend
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
docker compose up -d                 # Postgres
export DATABASE_URL="postgres://reconcile:reconcile@localhost:5435/reconcile_desk"
python manage.py migrate
python manage.py runserver 8234
python -m pytest                      # run tests

# Frontend
cd frontend
npm install
echo "VITE_API_BASE_URL=http://127.0.0.1:8234/api" > .env.local
npm run dev
npm test
```

## Real issues found while building this

- **The dark-mode theme made the whole app unreadable.** The Vite template's `index.css` already handles light/dark via CSS custom properties (`var(--text)`, `var(--bg)`), but `App.css` hardcoded `color: #1a1a1a` on the container, putting near-black text on a near-black background in dark mode. Caught by actually taking a headless-Chrome screenshot and reading the rendered DOM, not by trusting that "it builds" meant "it's usable." Fixed by removing the hardcoded color and letting the existing variable system handle both themes.
- **`django-admin startapp` scaffolds a `tests.py` file that collides with a `tests/` package.** Adding a `ledger/tests/` directory for multiple test files failed collection with an "import file mismatch" error until the auto-generated `ledger/tests.py` was deleted.
- **GCP Cloud Run was the original target platform for this app**, since that's what the role posting named specifically. The GCP billing account on hand turned out to be closed and needed a payment method re-added, a step requiring direct action in the Google Cloud Console that isn't appropriate to push through automatically. Deployed to Render (backend + Postgres) and Vercel (frontend) instead, rather than block on that or silently claim a GCP deployment that didn't happen.

## What's not here

No authentication/authorization layer (every endpoint is open; this is a focused concurrency/reconciliation demo, not a deployable product), no pagination on the accounts/statements endpoints, no real bank/processor integration (the reconciliation CSV format is a plausible but invented schema, stated plainly rather than implied to be a real provider's format).
