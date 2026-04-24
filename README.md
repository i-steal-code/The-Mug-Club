# The Mug Club

Operations dashboard for inventory, orders, finance, tasks, and recipes.

**Status: v0.1 (development).**

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
2. New **Web Service** on Render: connect this repo, build `pip install -r requirements.txt`, start `gunicorn app:app --bind 0.0.0.0:$PORT` (already in `Procfile`).
3. Set environment variables: `DATABASE_URL`, `SECRET_KEY`.

On first boot the app applies `schema.sql` and optional `seed.sql` if the database is empty.

## Data import

CSV files in the `database import/` folder are reference exports from Google Sheets. Use **Import / Export** in the app to load them (financial tracker, inventory, margins) or to export back to CSV for stakeholders and Sheets.

## Licence / project

School / club project — see repository history for authors.
