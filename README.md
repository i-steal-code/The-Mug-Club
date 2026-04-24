# The Mug Club

Operations dashboard for inventory, orders, finance, tasks, and recipes.

**Status: v0.1.9 (development).**

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

On first boot the app applies `schema.sql` and optional `seed.sql` if the database is empty.

**Supabase + Render:** Supabase’s **Session pooler** (under **Database → Connection string**) is **IPv4-proxied** and uses a host like `aws-REGION.pooler.supabase.com`, port **5432**, and user **`postgres.<project-ref>`** — use that URI for **`DATABASE_URL`** on Render when the direct `db.<ref>.supabase.co` host fails with IPv6 “Network is unreachable”. **Transaction** mode pooler (port **6543**) is another option. This app also resolves **IPv4 + `hostaddr`** for direct connections when an A record exists.

If Postgres returns **`FATAL: Tenant or user not found`**, the pooler username is wrong: it must be **`postgres.<project-ref>`**, not plain `postgres`. Copy the pooler URI from Supabase without swapping in the direct-connection user.

## Data import

CSV files in the `database import/` folder are reference exports from Google Sheets. Use **Import / Export** in the app to load them (financial tracker, inventory, margins) or to export back to CSV for stakeholders and Sheets.

## Licence / project

School / club project — see repository history for authors.
