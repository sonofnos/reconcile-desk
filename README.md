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
- **Tests**: pytest + pytest-django (11 tests, including a real concurrency test against Postgres, not sqlite), Vitest + Testing Library (3 tests)
- **Load testing**: k6, against a real 2M-row seeded dataset
- **CI**: GitHub Actions, backend tests run against a real `postgres:16-alpine` service container

## Concurrency, for real

`ledger/tests/test_concurrency.py` fires 15 threads at a single account funded for exactly one transfer, each on its own DB connection, and asserts exactly one succeeds and the balance never goes negative. It runs against real Postgres via `TransactionTestCase`, not an in-memory sqlite connection that would mask the row-locking behavior entirely.

## Scale, for real

`python manage.py seed_benchmark` loads a synthetic dataset (default: 5,000 accounts, 2,000,000 ledger entries) via a single set-based `INSERT ... SELECT generate_series(...)`, not a Python loop building 2 million ORM objects. On this machine it seeds 2M rows in about a minute.

`/api/transactions/search/` is a cross-account search by type and date range, the kind of query an ops/reporting screen runs constantly. Measured against the seeded dataset:

- **Without a supporting index**: 1,362ms per query (`EXPLAIN ANALYZE`, full index scan on `(account, created_at)` then filtering 54,740 rows by hand to find the 50 that matched).
- **With a composite index on `(type, -created_at)`**: 3.9ms. A ~350x improvement from one migration.
- **Load test** (`scripts/load_test.js`, k6, against gunicorn with `--workers 9 --threads 4 --worker-class gthread`, not `manage.py runserver`, which is single-threaded and would measure Django's dev server rather than the application): **~1,000 requests/second sustained, p95 under 200ms, zero failed requests**, against the full 2M-row dataset. Pushed further to a 1,500–3,000 req/s target, latency rose but the failure rate stayed at 0%: the system slows down under genuine overload rather than falling over. Measured on a single 10-core machine running both the load generator and the server at once, so the two were competing for the same CPU; dedicated hardware would likely do better.

The index alone wasn't the fix. The first load test, index already in place, topped out around 96 req/s with 13% failures. The bottleneck was gunicorn's default `sync` worker class, which handles one request at a time per process and has no way to overlap the wait on Postgres I/O. Switching to `gthread` got further but still stalled under 120 req/s until the real second bottleneck was found: Django's `Paginator` calls `.count()` to know the total page count, which scans every matching row even with a covering index. Replacing it with a fetch-`page_size + 1`-rows check, a plain `has_next` without a count, was what actually unlocked the throughput above.

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

# Scale benchmark (optional)
python manage.py seed_benchmark         # 5,000 accounts, 2M ledger entries
gunicorn config.wsgi:application --bind 127.0.0.1:8234 --workers 9 --threads 4 --worker-class gthread
cd .. && BASE_URL=http://127.0.0.1:8234 k6 run scripts/load_test.js

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

No authentication/authorization layer (every endpoint is open; this is a focused concurrency/reconciliation/scale demo, not a deployable product), no pagination on the accounts/statements list endpoints specifically (only transaction search, where it actually matters at scale), no real bank/processor integration (the reconciliation CSV format is a plausible but invented schema, stated plainly rather than implied to be a real provider's format).
