# Online Shop Operations Dashboard (SQLite)

An H2 Computing mini-project.

The core of the app is a **task tracker** — that's the part the
assignment asks for. The three extra modules (Inventory, Orders,
Finance) wrap it in an online-shop theme so the demo feels realistic.

## Tech Stack

- Python 3 + **Flask**
- **HTML** templates (Jinja2) + plain **CSS**
- **SQLite** through Python's built-in **`sqlite3`** module
- One local database file: `shop.db`

No cloud services, no environment variables, no deployment config.

## Folder Structure

```
shop-dashboard/
├── app.py                # Flask app + all routes (single file)
├── schema.sql            # SQLite CREATE TABLE statements
├── seed.sql              # Sample rows for the demo
├── requirements.txt      # Just: Flask
├── README.md
├── templates/            # Jinja2 HTML templates
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

`shop.db` is created automatically the first time you run the app.

## Setup (local, classroom-friendly)

```bash
# 1. (optional) create a virtual environment
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS:    source .venv/bin/activate

# 2. install Flask
pip install -r requirements.txt

# 3. run the app
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in a browser.
That's it — the first run creates `shop.db`, builds the tables from
`schema.sql`, and loads sample rows from `seed.sql`.

To start over from scratch, delete `shop.db` and run `python app.py`
again.

## Feature Checklist (rubric mapping)

| Rubric requirement                                  | Where it lives                                                         |
|-----------------------------------------------------|------------------------------------------------------------------------|
| Add new tasks                                       | `POST /tasks/add` (form in `task_add.html`)                            |
| Display all tasks clearly                           | `GET /tasks` table in `tasks.html`                                     |
| Update task status                                  | `POST /tasks/<id>/status` inline dropdown on tasks page                |
| Statuses: Not Started / In Progress / Completed     | `TASK_STATUSES` list in `app.py` + `CHECK` constraint in `schema.sql`  |
| Title / description / assigned / created-by         | Columns on `tasks`, all present on the add-task form                   |
| Show only a selected member's tasks                 | `?member_id=<id>` filter on `/tasks`                                   |
| SQL database storage                                | Local SQLite via `sqlite3`, all queries use `?` parameter placeholders |
| Optional: keyword search                            | `?q=` on `/tasks` (SQLite `LIKE`)                                      |
| Optional: priority Low / Medium / High              | `tasks.priority` column + form field                                   |

Shop-themed extras:

- `/inventory` + `/inventory/add` — products with a low-stock indicator (stock < 5) and a category filter.
- `/orders` + `/orders/add` — customer orders with order-status and payment-status dropdowns.
- `/finance` — per-product margin and estimated profit (completed orders only).
- `/members` — add/list staff who can be assigned tasks.

## Route Reference

| Method     | URL                     | What it does                                          |
|------------|-------------------------|-------------------------------------------------------|
| GET        | `/`                     | Dashboard (counts + recent tasks)                     |
| GET        | `/tasks`                | List tasks, supports `?member_id=` and `?q=`          |
| GET / POST | `/tasks/add`            | Add-task form / insert                                |
| POST       | `/tasks/<id>/status`    | Change a task's status                                |
| POST       | `/tasks/<id>/delete`    | Delete a task                                         |
| GET        | `/inventory`            | List products, supports `?category=`                  |
| GET / POST | `/inventory/add`        | Add-product form / insert                             |
| GET        | `/orders`               | List orders                                           |
| GET / POST | `/orders/add`           | Add-order form / insert                               |
| POST       | `/orders/<id>/status`   | Update order-status and/or payment-status             |
| GET        | `/finance`              | Margin + estimated profit summary                     |
| GET / POST | `/members`              | List members / add a new member                       |

## Demo Script (10 minutes)

1. Show the dashboard — three stat cards and recent tasks.
2. Go to **Tasks**, add a new one ("Pack order #1030", assigned to Darren, High priority).
3. Change its status inline: Not Started → In Progress → Completed. Mention the `CHECK` constraint in `schema.sql` that rejects invalid values at the database level.
4. Use the **assigned member filter** to show only Chloe's tasks — this hits the rubric requirement.
5. Use the keyword search to find "restock".
6. Open **Inventory**, point out the "Low Stock" pill on Notebook A5 (stock < 5).
7. Open **Orders**, change an order's status and its payment status.
8. Open **Finance**, explain `margin = selling − cost` and that profit only counts **Completed** orders. Point at the total at the top.
9. Open a terminal and run `sqlite3 shop.db ".tables"` and `sqlite3 shop.db "SELECT * FROM tasks;"` — proves the data is really in SQL.
10. Finish by pointing at `app.py` → the `query()` helper uses `?` placeholders. Mention this is how we keep the code safe from SQL injection.

## Common Bugs and Fixes

| Symptom                                              | Fix                                                                       |
|------------------------------------------------------|---------------------------------------------------------------------------|
| `sqlite3.OperationalError: no such table: tasks`     | Delete `shop.db` and run `python app.py` again so it re-creates tables.   |
| Flash messages don't appear                          | `app.secret_key` must be set (it already is in `app.py`).                 |
| `TemplateNotFound`                                   | Run `python app.py` from inside the `shop-dashboard/` folder.             |
| `sqlite3.IntegrityError: CHECK constraint failed`    | A status value isn't in the allowed list. Check spelling in the form.    |
| New data doesn't show after refresh                  | We commit in `query()`. Re-check that `fetch=False` is correct for inserts. |
| Can't open the site                                  | Make sure port 5000 isn't in use; or change `app.run(port=5001)`.          |

## How This Version Is Syllabus-Aligned

- **No cloud services** — just Python, Flask, SQLite.
- **Standard library only for DB** — `import sqlite3`, `sqlite3.connect(...)`, `conn.execute(...)`, parameterised with `?`. This is exactly the style in H2 lecture notes.
- **Simple project layout** — one `app.py`, one `templates/` folder, one `static/` folder, one `.db` file.
- **Straightforward SQL** — plain `CREATE TABLE`, `INSERT`, `SELECT`, `UPDATE`, `DELETE`, `JOIN`, `GROUP BY`. No Postgres-only features.
- **Flask idioms taught in class** — `render_template`, `url_for`, `request.args`, `request.form`, `flash`, GET/POST handling.
- **Runs with one command** — `python app.py` — no setup scripts, no environment variables, no external services.
