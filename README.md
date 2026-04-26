# The Mug Club

Operations dashboard for inventory, orders, finance, tasks, and recipes.

**Status: v0.2.3 (development).**

## Stack

- **Python 3.12** + **Flask**
- **PostgreSQL** on [**Supabase**](https://supabase.com/) (connection string as `DATABASE_URL`)
- **Hosting**: [**Render**](https://render.com/) Web Service (`gunicorn` via `Procfile`)

## Run locally

1. Create a Supabase project and copy the **Database** connection URI (use the `postgresql://` form; include `?sslmode=require` if prompted).
2. Copy `.env.example` to `.env` and set `DATABASE_URL` and `SECRET_KEY`.
3. Install and run:

```bash
pip install -r requirements.txt
set FLASK_DEBUG=1
set DATABASE_URL=postgresql://...
python app.py
```

Open `http://127.0.0.1:5000`.

## Deploy on Render

1. Create a **Supabase** database and note the connection string.
2. New **Web Service** on Render: connect this repo, build `pip install -r requirements.txt`, start command from `Procfile` (`gunicorn` binds to `$PORT`).
3. Set environment variables: `DATABASE_URL`, `SECRET_KEY` — paste the Supabase **URI** exactly (do not add `[ ]` around the hostname; only literal IPv6 uses brackets). If `urlparse` / startup fails with a host like `[something-invalid]`, fix the env value.

**Python version:** New Render services default to **Python 3.14**, while `psycopg2-binary` does not ship compatible wheels for 3.14 yet (you may see `ImportError: ... undefined symbol: _PyInterpreterState_Get`). This repo includes a root **`.python-version`** file set to `3.12.6` (see [Render’s Python version docs](https://render.com/docs/python-version)). If the dashboard still builds with 3.14, set **`PYTHON_VERSION`** = `3.12.6` on the service (that override takes precedence).

On first request that uses the database, the app applies `schema.sql` (if empty) and idempotent migrations. There is **no bundled seed data** — add members and tasks in-app, or insert via SQL.

**Supabase + Render:** Supabase’s **Session pooler** (under **Database → Connection string**) is **IPv4-proxied** and uses a host like `aws-REGION.pooler.supabase.com`, port **5432**, and user **`postgres.<project-ref>`** — use that URI for **`DATABASE_URL`** on Render when the direct `db.<ref>.supabase.co` host fails with IPv6 “Network is unreachable”. **Transaction** mode pooler (port **6543**) is another option. This app also resolves **IPv4 + `hostaddr`** for direct connections when an A record exists.

If Postgres returns **`FATAL: Tenant or user not found`**, the pooler username is wrong: it must be **`postgres.<project-ref>`**, not plain `postgres`. Copy the pooler URI from Supabase without swapping in the direct-connection user.

### Free tier: reducing cold starts (v0.2.3 plan)

Render free web services spin down after idle time. You cannot fully remove cold starts without a paid instance, but you can **shorten idle sleep**, **wake cheaply**, and **diagnose** lingering slowness.

Two keep-warm endpoints (no auth, both send `Cache-Control: no-store`):

- `GET /healthz` — returns plain `ok`, never opens Postgres. Keeps the Python web worker warm.
- `GET /warm` — runs `SELECT 1` through the same connection path as real requests. Keeps the Postgres connection + libpq IPv4 resolution warm and prints `elapsed_ms` for timing.

Recommended schedule (two monitors):

1. **/healthz** every **10 min** (light, cheap). UptimeRobot / Better Stack / a cron — anything that does a plain HTTP GET.
2. **/warm** every **15 min**. Because `/warm` talks to Postgres, it keeps Supabase from cold-starting the pooled connection that the first real page would otherwise pay for.

Troubleshooting plan when pings appear to "not work":

1. **Confirm the URL** — Render free services deploy to `https://<service>.onrender.com`. Open `/healthz` in your browser; you must see `ok`. If you see the dashboard / a redirect, the monitor may be hitting a different route.
2. **Confirm the monitor fires** — in UptimeRobot, check "Response Times" and the latest log. If the check is stuck at 12h cadence because the free plan doesn't accept <5 min intervals, that's fine — 5–14 min is enough.
3. **Watch Render logs in real time** — the first request after idle shows a ~30–60s spin-up line (`==> Your service is live`). A ping during that window does wake the service; subsequent pings keep it warm for the next 15 min window.
4. **Check response times** — `/warm` prints `elapsed_ms`. A cold worker typically reports >500 ms for the first hit; steady state is <100 ms. If `/warm` stays >500 ms consistently, the slow path is the database, not Python.
5. **Last resort** — Render's free web tier still has an **inactivity timeout** independent of request traffic on some account tiers. Upgrade the service to the paid tier if sub-second first-paint is a hard requirement.

## One-time data load (manual SQL-first)

The import flow is SQL-first (Supabase SQL editor), plus an in-app financial tracker importer:

1. Manually normalize names in your CSVs first (for example: `heavy cream` vs `whipping cream`, `honey buttercream` naming).
2. Open `database import/supabase_manual_insert.sql`.
3. Adjust values as needed and run in Supabase SQL editor.

This keeps ingestion simple and transparent with no extra runtime dependency/debug loop.

### Financial tracker import (1NF in v0.2.3)

Use **Finance → Import financial tracker CSV** to ingest
`database import/3_The Mug Club_Financials - Financial Tracker.csv`.
The importer:

- separates the cash inflow / outflow side-by-side tables in the raw sheet,
- skips non-standard header / preamble rows,
- cleans dates and amounts,
- **splits each inflow description into 1NF rows** — one per singular product bought — pulling out `customer_name`, `product_name`, and splitting `amount` evenly across the listed cups,
- infers `payment_type` (`paynow` / `cash`) from the "Person In Charge" column,
- tags all imported rows with `payment_status = 'paid'` since they're historical.

## Structured ordering + recipe model (v0.2.3)

- **Recipe databank** (`/products`) is a gallery of product cards; clicking opens the recipe detail.
- **Components** (`/components`) are reusable building blocks (matcha cloud, buttercream, syrups). Each has its own ingredient list and step list.
- **Product recipe ingredients** can reference either an inventory item or a component — components act as a "bundled" ingredient for flavour work.
- Orders are stored via `products` + `order_items` (3NF operational), and are promoted into the 1NF **`finance_cash_inflows`** sheet automatically when both status = **Completed** and payment = **Paid**.
- On the orders page, status + payment are **morphing buttons** — click to advance to the next state. Completed + paid rows drop off the list (they now live in finance).
- Shop page uses a **product-card picker** (no separate menu below) with a per-line special-request input, and shows a PayNow footnote noting that orders are only processed after payment verification.
- Staff / team page replaces the old "Members" label and hides internal employee IDs.

Each dashboard list page links to **Export CSV** for relevant tables.

## Licence / project

School / club project — see repository history for authors.
