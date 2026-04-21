# Online Shop Operations Dashboard

An H2 Computing mini-project that satisfies the official **task-tracker** requirement while being themed as an online shop operations dashboard.

**Stack:** Flask · Jinja2 · plain HTML/CSS · Supabase (Postgres) · Vercel.

---

## 1. Project Overview

The app is a web dashboard that a small online shop team can use to manage day-to-day operations. The core of the app is the **Task Management** module — this is the piece that directly satisfies the H2 Computing assignment. Three more modules (Inventory, Orders, Finance) wrap the shop theme around the core.

- **Task Management** — add shop tasks (restock, pack order, verify payment, etc.), assign them to staff, filter by assigned member, update status.
- **Inventory Management** — track products, categories, stock levels, and see low-stock warnings.
- **Order Management** — record customer orders and update order / payment status.
- **Financial Margins** — see per-product margin and estimated profit from completed orders.

---

## 2. Feature Checklist (mapped to assignment)

| Assignment requirement            | Where it lives                                                                 |
|-----------------------------------|-------------------------------------------------------------------------------|
| Add new tasks                     | `POST /tasks/add`  (form in `task_add.html`)                                  |
| Display all tasks clearly         | `GET /tasks`  (table in `tasks.html`)                                         |
| Update task status                | `POST /tasks/<id>/status`  (inline dropdown on tasks page)                    |
| Not Started / In Progress / Completed | CHECK constraint in `schema.sql`; list in `app.py` (`TASK_STATUSES`)     |
| Title                             | `tasks.title` column + form field                                             |
| Description                       | `tasks.description` column + form field                                       |
| Assigned member                   | `tasks.assigned_member_id` FK → `members`                                     |
| Created by                        | `tasks.created_by_id` FK → `members`                                          |
| Show only tasks of a selected member | `?member_id=...` query-string filter on `/tasks`                           |
| SQL database storage              | Supabase Postgres, accessed via `psycopg2` with parameterised queries         |
| Optional: search by keyword       | `?q=...` on `/tasks` (ILIKE in title/description)                             |
| Optional: priority (Low/Med/High) | `tasks.priority` column + form field                                          |

Shop-themed extras:
- Inventory CRUD (`/inventory`, `/inventory/add`) with low-stock indicator and category filter.
- Orders CRUD (`/orders`, `/orders/add`) with order-status and payment-status updates.
- Finance summary (`/finance`) computing margin per unit and estimated profit.

---

## 3. Folder Structure

```
shop-dashboard/
├── app.py                  # Flask app + all routes
├── requirements.txt        # Python dependencies
├── schema.sql              # Supabase table definitions
├── seed.sql                # Sample data
├── vercel.json             # Vercel deployment config
├── .env.example            # Template for local env vars
├── .gitignore
├── templates/              # Jinja2 HTML templates
│   ├── base.html
│   ├── dashboard.html
│   ├── tasks.html
│   ├── task_add.html
│   ├── inventory.html
│   ├── inventory_add.html
│   ├── orders.html
│   ├── order_add.html
│   ├── finance.html
│   ├── members.html
│   └── error.html
└── static/
    └── style.css
```

---

## 4. Database Schema (summary)

Four tables, all in the `public` schema of Supabase:

- `members (id, name, role, email)` — staff roster.
- `tasks (id, title, description, assigned_member_id, created_by_id, status, priority, created_at)` — the core table.
- `products (id, name, category, stock_quantity, cost_price, selling_price)` — inventory.
- `orders (id, customer_name, product_id, quantity, order_status, payment_status, created_at)` — customer orders.

See `schema.sql` for the full SQL, including CHECK constraints that enforce the allowed status / priority values at the database level.

---

## 5. Route Reference

| Method | URL                          | What it does                                                      |
|--------|------------------------------|-------------------------------------------------------------------|
| GET    | `/`                          | Dashboard with counts + recent tasks                              |
| GET    | `/tasks`                     | List tasks, supports `?member_id=` and `?q=` filters              |
| GET/POST | `/tasks/add`               | Add-task form / insert                                            |
| POST   | `/tasks/<id>/status`         | Update a task's status                                            |
| POST   | `/tasks/<id>/delete`         | Delete a task                                                     |
| GET    | `/inventory`                 | List products, supports `?category=` filter                       |
| GET/POST | `/inventory/add`           | Add-product form / insert                                         |
| GET    | `/orders`                    | List orders                                                       |
| GET/POST | `/orders/add`              | Add-order form / insert                                           |
| POST   | `/orders/<id>/status`        | Update order / payment status                                     |
| GET    | `/finance`                   | Margin + estimated profit summary                                 |
| GET/POST | `/members`                 | List members / add a new member                                   |

---

## 6. How Each Feature Satisfies The Rubric

1. **Add task** → `tasks_add()` inserts a row. The form collects title, description, assigned member, created-by and priority.
2. **Display tasks** → `tasks_list()` selects all tasks and joins `members` twice so we can display both the assigned-to name and created-by name.
3. **Update status** → the tasks table has an inline `<select>` that POSTs to `/tasks/<id>/status`. The backend validates that the new value is one of the three allowed statuses.
4. **Filter by assigned member** → `?member_id=<id>` query string; the template keeps the current selection.
5. **Status enum enforcement** → enforced both in Python (`TASK_STATUSES` list) and in the database (`CHECK` constraint in `schema.sql`).
6. **SQL-backed storage** → every read/write goes through `query()` in `app.py`, which uses parameterised SQL (`%s` placeholders) to prevent SQL injection.
7. **Priority & search** → implemented as optional extras so your team can show progression beyond the minimum rubric.

---

## 7. Setup Instructions (Local)

Prerequisites: Python 3.10+, a free Supabase account.

### 7.1 Create the Supabase database

1. Go to [supabase.com](https://supabase.com) → **New project**.
2. Save the database password when prompted.
3. In the Supabase dashboard, open **SQL Editor** → **New query**, paste the contents of `schema.sql`, click **Run**.
4. Run a second query with the contents of `seed.sql` to load the demo data.
5. Open **Project Settings → Database → Connection string** and copy the **URI** value. It looks like:
   `postgresql://postgres:YOUR_PASSWORD@db.xxxxxxxx.supabase.co:5432/postgres`

### 7.2 Run the Flask app locally

```bash
cd shop-dashboard
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env          # then edit .env and paste your DATABASE_URL
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in a browser.

---

## 8. Deployment (Vercel)

Vercel can run Flask apps as a serverless function using the `@vercel/python` builder. The included `vercel.json` already handles routing.

```bash
npm install -g vercel   # one-time
cd shop-dashboard
vercel                  # follow the prompts, accept defaults
```

Then set the environment variables in the Vercel dashboard → **Project → Settings → Environment Variables**:

- `DATABASE_URL` — your Supabase connection string (use the **Transaction Pooler** URL on port `6543` for better serverless behaviour).
- `FLASK_SECRET` — any random string.

Redeploy after adding env vars: `vercel --prod`.

> **Important note on Vercel + Flask:**
> Vercel's Python runtime is serverless — each request can spin up a new process. This means:
> - Every request opens a fresh DB connection. This works fine for a demo but isn't efficient for high traffic. For better performance, use Supabase's "Transaction Pooler" connection string (port 6543) so the pooler handles connection reuse.
> - Long-running background jobs aren't supported (we don't use any).
> - If your `psycopg2-binary` wheel ever fails to build on Vercel, swap it for `psycopg[binary]` (Psycopg 3) — the code still works with small changes.
>
> If deployment still fails, the simplest fallback is to deploy on **Render** or **Railway** instead of Vercel — both support long-lived Flask processes and keep the stack unchanged. Supabase and the rest of the app code stay the same.

---

## 9. Local Testing Checklist

Use this list during development and before submitting.

- [ ] Dashboard loads and shows numbers that match the seed data.
- [ ] `/tasks` shows all 5 seed tasks with correct assigned-to / created-by names.
- [ ] Adding a new task redirects to the list and the new task appears.
- [ ] Selecting a member from the filter dropdown only shows that member's tasks.
- [ ] Keyword search finds seed task "Restock A5 Notebooks".
- [ ] Changing the status dropdown on a task row updates it (re-load confirms).
- [ ] Deleting a task asks for confirmation and then removes it.
- [ ] `/inventory` shows "Low Stock" on the Notebook A5 row.
- [ ] Adding a product works and appears in the list.
- [ ] Adding an order works and the total column computes correctly.
- [ ] Changing an order's status dropdown persists the change.
- [ ] `/finance` shows non-zero profit for products with completed orders.

---

## 10. Demo Script (10-minute presentation)

| Time  | What to say / do                                                                                                          |
|-------|--------------------------------------------------------------------------------------------------------------------------|
| 0:00  | "Our project is an online shop operations dashboard. The core is a task tracker — that's the rubric requirement — and we've wrapped three shop modules around it." |
| 0:45  | Show the dashboard. Point out the three stat cards (tasks / products / orders) and the recent-tasks table.               |
| 1:30  | Open `/tasks`. Explain the columns: title, description, assigned member, created by, priority, status.                    |
| 2:15  | Click **Add Task**. Add "Pack order #1030" assigned to Darren Koh, priority High. Submit. Show it appearing at the top.   |
| 3:15  | Demonstrate the **status update** dropdown — change the new task to "In Progress", then "Completed". Explain the CHECK constraint that makes the database reject invalid values. |
| 4:00  | Demonstrate the **assigned-member filter** — pick "Chloe Ng" and show only her tasks. This satisfies the rubric's "display only a selected member's tasks" requirement. |
| 4:45  | Demonstrate the keyword search with "restock".                                                                            |
| 5:15  | Jump to `/inventory`. Show the "Low Stock" indicator on Notebook A5 (stock = 3). Explain the simple rule: `stock < 5`.    |
| 6:00  | `/orders` — show how order status and payment status can be changed independently. Explain the two status columns.        |
| 7:00  | `/finance` — explain `margin per unit = selling − cost`, and that profit only counts **Completed** orders. Show total estimated profit at the top. |
| 8:00  | Open the Supabase SQL editor and run `SELECT * FROM tasks WHERE assigned_member_id = 3;` to show the same data straight from SQL — proves it's really SQL-backed. |
| 8:45  | Briefly open `app.py` → highlight the `query()` helper using `%s` placeholders. Mention this is how we protect against SQL injection. |
| 9:30  | Wrap up: "Task tracker satisfies every rubric point; Inventory/Orders/Finance add realistic shop context. Questions?"    |

---

## 11. Common Bugs and Fixes

| Symptom                                                          | Fix                                                                                          |
|------------------------------------------------------------------|----------------------------------------------------------------------------------------------|
| `RuntimeError: DATABASE_URL is not set`                          | You forgot to copy `.env.example` → `.env` and fill it in.                                   |
| `psycopg2.OperationalError: could not connect ... SSL`           | Supabase requires SSL. The code passes `sslmode="require"` — don't remove it.                |
| `FATAL: Tenant or user not found`                                | Wrong password or project ref in `DATABASE_URL`. Recopy from Supabase settings.              |
| `relation "tasks" does not exist`                                | You didn't run `schema.sql` in Supabase. Open SQL editor → paste → Run.                      |
| Flash messages don't appear                                      | `FLASK_SECRET` is unset. Set it in `.env` (any string).                                      |
| Status dropdown POST returns 404 on Vercel                       | Check `vercel.json` still has the catch-all route to `app.py`.                               |
| psycopg2 fails to install on Vercel                              | Replace `psycopg2-binary` with `psycopg[binary]==3.2.1` in `requirements.txt` and change `import psycopg2` to `import psycopg as psycopg2` (Psycopg 3's API is a superset for our usage). |
| Low-stock indicator never turns yellow                           | Confirm the product's `stock_quantity` is below 5 — edit it directly in the Supabase Table Editor. |
| Finance page shows $0 profit                                     | Only **Completed** orders are counted. Change an order's status to Completed to see it show up. |
| Template error: `jinja2.exceptions.TemplateNotFound`             | Make sure you ran `app.py` from inside the `shop-dashboard/` folder so Flask can find `templates/`. |

---

Built for H2 Computing. Keep it simple, explain it clearly, and good luck with the demo!
