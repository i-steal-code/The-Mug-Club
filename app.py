"""
The Mug Club — operations dashboard (Flask + PostgreSQL / Supabase).
Deploy: Render Web Service + Supabase Postgres (DATABASE_URL).
"""

from __future__ import annotations

import csv
import io
import ipaddress
import os
import re
import socket
from datetime import date, datetime
from urllib.parse import parse_qs, unquote, urlparse

import psycopg2
from flask import Flask, Response, flash, redirect, render_template, request, url_for
from psycopg2 import extras
from psycopg2.extensions import connection as PgConnection

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.environ.get("DATABASE_URL")

TASK_STATUSES = ["Not Started", "In Progress", "Completed"]
TASK_PRIORITIES = ["Low", "Medium", "High"]
ORDER_STATUSES = ["Pending", "Processing", "Completed", "Cancelled"]
PAYMENT_STATUSES = ["Unpaid", "Paid", "Refunded"]
CLOUD_TYPES = ("coffee", "matcha")


def _first_ipv4_addr(hostname: str, port: int) -> str | None:
    """Return first IPv4 for hostname, or None (e.g. only AAAA on broken IPv6 paths)."""
    try:
        infos = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except OSError:
        return None
    for family, _, _, _, sockaddr in infos:
        if family == socket.AF_INET:
            return sockaddr[0]
    return None


def _connect_kwargs_from_database_url(url: str) -> dict:
    """
    Build psycopg2 keyword args from a postgresql:// URI.

    Render (and some hosts) cannot reach Supabase over IPv6 even when DNS returns
    AAAA first → "Network is unreachable". Passing hostaddr=<IPv4> with host=<FQDN>
    forces IPv4 while keeping the correct TLS server name.
    """
    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port or 5432
    path = parsed.path or "/postgres"
    dbname = path[1:] if path.startswith("/") else path
    if not dbname:
        dbname = "postgres"

    user = unquote(parsed.username) if parsed.username else "postgres"
    password = unquote(parsed.password) if parsed.password is not None else ""

    q = parse_qs(parsed.query, keep_blank_values=True)
    extra: dict[str, str] = {}
    for key, values in q.items():
        if values and values[0] is not None:
            extra[key] = values[0]
    if "sslmode" not in q:
        extra["sslmode"] = "require"

    base = {
        "dbname": dbname,
        "user": user,
        "password": password,
        "port": str(port),
        **extra,
    }

    if not host:
        return base

    try:
        ipaddress.ip_address(host)
        return {**base, "host": host}
    except ValueError:
        pass

    ipv4 = _first_ipv4_addr(host, port)
    if ipv4:
        return {**base, "host": host, "hostaddr": ipv4}
    return {**base, "host": host}


def get_conn() -> PgConnection:
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not set. Add your Supabase connection string "
            "(see .env.example) for local runs and Render."
        )
    url = DATABASE_URL
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    kwargs = _connect_kwargs_from_database_url(url)
    return psycopg2.connect(cursor_factory=extras.RealDictCursor, **kwargs)


def query(sql: str, params=None, fetch=False, one=False):
    params = params or ()
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                if fetch:
                    rows = cur.fetchall()
                    return (rows[0] if rows else None) if one else rows
                return None
    finally:
        conn.close()


def _run_schema(conn: PgConnection) -> None:
    path = os.path.join(BASE_DIR, "schema.sql")
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    cur = conn.cursor()
    for stmt in re.split(r";\s*\n", raw):
        stmt = stmt.strip()
        if stmt:
            cur.execute(stmt)


def ensure_schema_and_seed() -> None:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'members'
                    """
                )
                exists = cur.fetchone() is not None
            if not exists:
                _run_schema(conn)
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS c FROM members")
                n = cur.fetchone()["c"]
            if n == 0:
                seed_path = os.path.join(BASE_DIR, "seed.sql")
                if os.path.isfile(seed_path):
                    with open(seed_path, encoding="utf-8") as f:
                        seed_sql = f.read()
                    with conn.cursor() as cur:
                        for stmt in re.split(r";\s*\n", seed_sql):
                            stmt = stmt.strip()
                            if stmt:
                                cur.execute(stmt)
    finally:
        conn.close()


with app.app_context():
    if DATABASE_URL:
        ensure_schema_and_seed()


@app.before_request
def _require_database_url():
    if DATABASE_URL or request.endpoint == "static":
        return None
    return render_template("setup.html"), 503


# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------
def parse_money(value) -> float | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    s = s.replace("$", "").replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def parse_date(value) -> date | None:
    if value is None:
        return None
    s = str(value).strip().split(",")[0].strip()
    if not s:
        return None
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parse_int(value) -> int | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def parse_bool_cell(value) -> bool:
    s = str(value).strip().upper()
    return s in ("TRUE", "T", "1", "YES", "Y")


def csv_response(filename: str, rows: list[list], header: list[str] | None = None):
    buf = io.StringIO()
    w = csv.writer(buf)
    if header:
        w.writerow(header)
    for r in rows:
        w.writerow(r)
    data = buf.getvalue().encode("utf-8")
    return Response(
        data,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Import parsers
# ---------------------------------------------------------------------------
def import_inventory_csv(stream, replace: bool = False) -> tuple[int, int]:
    """Returns (items_upserted, prep_rows_inserted)."""
    text = io.TextIOWrapper(stream, encoding="utf-8", newline="")
    rows = list(csv.reader(text))
    items = []
    prep = []
    mode = "items"
    for row in rows:
        if not row or all(not (c or "").strip() for c in row):
            continue
        key = (row[0] or "").strip().lower()
        if key == "component":
            mode = "prep"
            continue
        if mode == "items":
            if (row[0] or "").strip().lower() == "item":
                continue
            name = (row[0] or "").strip()
            if not name:
                continue
            qty_raw = (row[1] or "").strip() if len(row) > 1 else ""
            qty = None
            if qty_raw:
                try:
                    qty = float(qty_raw.replace(",", ""))
                except ValueError:
                    qty = None
            remark = (row[2] or "").strip() if len(row) > 2 else ""
            upd = parse_bool_cell(row[3]) if len(row) > 3 else False
            items.append((name, qty, remark or None, upd))
        else:
            cname = (row[0] or "").strip()
            if not cname or cname.lower() == "component":
                continue
            qfw = (row[1] or "").strip() if len(row) > 1 else ""
            ready = parse_bool_cell(row[2]) if len(row) > 2 else False
            prep.append((cname, qfw or None, ready))

    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                if replace:
                    cur.execute("DELETE FROM inventory_prep")
                    cur.execute("DELETE FROM inventory_items")
                for name, qty, remark, upd in items:
                    cur.execute(
                        """
                        INSERT INTO inventory_items (item_name, qty_grams, remark, updated_flag)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (item_name) DO UPDATE SET
                          qty_grams = EXCLUDED.qty_grams,
                          remark = EXCLUDED.remark,
                          updated_flag = EXCLUDED.updated_flag
                        """,
                        (name, qty, remark, upd),
                    )
                n_items = len(items)
                if prep:
                    cur.execute("DELETE FROM inventory_prep")
                    for p in prep:
                        cur.execute(
                            """
                            INSERT INTO inventory_prep (component_name, qty_for_week, ready)
                            VALUES (%s, %s, %s)
                            """,
                            p,
                        )
                n_prep = len(prep)
        return n_items, n_prep
    finally:
        conn.close()


def import_margins_csv(stream, replace: bool = False) -> tuple[int, int]:
    text = io.TextIOWrapper(stream, encoding="utf-8", newline="")
    rows = list(csv.reader(text))
    ingredients: list[tuple] = []
    menu: list[tuple] = []
    section = "find_header"

    for row in rows:
        if not row:
            continue
        r0 = (row[0] or "").strip().lower()
        r1 = (row[1] or "").strip().lower() if len(row) > 1 else ""
        if section == "find_header" and r0 == "category" and "ingredient" in r1:
            section = "ingredients"
            continue
        if section == "ingredients":
            if not r0 and not r1:
                section = "after_ingredients"
                continue
            if r0 == "category":
                continue
            if len(row) < 2 or not (row[1] or "").strip():
                section = "after_ingredients"
                continue
            cat = (row[0] or "").strip() or None
            ing = (row[1] or "").strip()
            ingredients.append(
                (
                    cat,
                    ing,
                    parse_money(row[2]) if len(row) > 2 else None,
                    parse_money(row[3]) if len(row) > 3 else None,
                    parse_money(row[4]) if len(row) > 4 else None,
                    parse_money(row[5]) if len(row) > 5 else None,
                    ((row[6] or "").strip() or None) if len(row) > 6 else None,
                )
            )
            continue
        if section == "after_ingredients":
            if r1 == "thing" or (len(row) > 1 and (row[1] or "").strip().lower() == "thing"):
                section = "menu"
                continue
            continue
        if section == "menu":
            if len(row) > 1 and (row[1] or "").strip().lower() == "thing":
                continue
            name = (row[1] or "").strip() if len(row) > 1 else ""
            if not name:
                continue
            mcat = (row[0] or "").strip() or None
            cost = parse_money(row[2]) if len(row) > 2 else None
            sell = parse_money(row[3]) if len(row) > 3 else None
            profit = parse_money(row[4]) if len(row) > 4 else None
            menu.append((mcat, name, cost, sell, profit))

    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                if replace:
                    cur.execute("DELETE FROM margin_menu_items")
                    cur.execute("DELETE FROM margin_ingredients")
                for t in ingredients:
                    cur.execute(
                        """
                        INSERT INTO margin_ingredients
                          (category, ingredient, cost_per_cup, amt_used_g, source_cost, source_qty_g, supplier)
                        VALUES (%s,%s,%s,%s,%s,%s,%s)
                        """,
                        t,
                    )
                for t in menu:
                    cur.execute(
                        """
                        INSERT INTO margin_menu_items (category, item_name, cost, selling_price, profit)
                        VALUES (%s,%s,%s,%s,%s)
                        """,
                        t,
                    )
        return len(ingredients), len(menu)
    finally:
        conn.close()


def import_financial_csv(stream, replace: bool = False) -> tuple[int, int]:
    text = io.TextIOWrapper(stream, encoding="utf-8", newline="")
    rows = list(csv.reader(text))
    start = None
    for i, row in enumerate(rows):
        joined = ",".join(row)
        if "Transaction Item" in joined and "Cash Inflow" in joined:
            start = i + 2
            break
    if start is None:
        raise ValueError("Could not find financial tracker header row.")

    inflows: list[tuple] = []
    outflows: list[tuple] = []

    for row in rows[start:]:
        if not row or len(row) < 4:
            continue
        def g(idx):
            return row[idx] if idx < len(row) else ""

        txn_in = parse_int(g(2))
        amt_in = parse_money(g(3))
        desc_in = (g(4) or "").strip() or None
        cups = parse_int(g(5))
        d_in = parse_date(g(6))
        shot_in = (g(7) or "").strip() or None
        pic_in = (g(8) or "").strip() or None

        txn_out = parse_int(g(9))
        amt_out = parse_money(g(10))
        desc_out = (g(11) or "").strip() or None
        d_out = parse_date(g(12))
        shot_out = (g(13) or "").strip() or None
        pic_out = (g(14) or "").strip() or None if len(row) > 14 else None

        if amt_in is not None:
            inflows.append((txn_in, amt_in, desc_in, cups, d_in, shot_in, pic_in))
        if amt_out is not None:
            outflows.append((txn_out, amt_out, desc_out, d_out, shot_out, pic_out))

    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                if replace:
                    cur.execute("DELETE FROM finance_cash_outflows")
                    cur.execute("DELETE FROM finance_cash_inflows")
                for t in inflows:
                    cur.execute(
                        """
                        INSERT INTO finance_cash_inflows
                          (source_txn_number, amount, description, quantity_cups, txn_date, screenshot, person_in_charge)
                        VALUES (%s,%s,%s,%s,%s,%s,%s)
                        """,
                        t,
                    )
                for t in outflows:
                    cur.execute(
                        """
                        INSERT INTO finance_cash_outflows
                          (source_txn_number, amount, description, txn_date, screenshot, person_in_charge)
                        VALUES (%s,%s,%s,%s,%s,%s)
                        """,
                        t,
                    )
        return len(inflows), len(outflows)
    finally:
        conn.close()


def import_orders_csv(stream, replace: bool = False) -> int:
    """
    Expected header (case-insensitive):
    customer_name,order_summary,cup_count,total_amount,order_date,payment_notes,order_status,payment_status
    Extra columns ignored. If order_date missing, uses today.
    """
    text = io.TextIOWrapper(stream, encoding="utf-8", newline="")
    reader = csv.DictReader(text)
    if not reader.fieldnames:
        raise ValueError("Orders CSV has no header row.")

    fn = {h.strip().lower(): h for h in reader.fieldnames if h}
    def col(row, *names):
        for n in names:
            key = fn.get(n.lower())
            if key and row.get(key) is not None:
                return row.get(key)
        return None

    rows_out: list[tuple] = []
    for row in reader:
        if not row or not any((v or "").strip() for v in row.values()):
            continue
        cust = (col(row, "customer_name", "name", "customer") or "").strip()
        if not cust:
            continue
        summary = (col(row, "order_summary", "description", "order details", "items") or "").strip() or None
        cups = parse_int(col(row, "cup_count", "cups", "quantity")) or 1
        total = parse_money(col(row, "total_amount", "amount", "total"))
        odate = parse_date(col(row, "order_date", "date")) or date.today()
        notes = (col(row, "payment_notes", "notes", "payment") or "").strip() or None
        ost = (col(row, "order_status") or "Pending").strip()
        pst = (col(row, "payment_status") or "Unpaid").strip()
        if ost not in ORDER_STATUSES:
            ost = "Pending"
        if pst not in PAYMENT_STATUSES:
            pst = "Unpaid"
        rows_out.append((cust, summary, cups, total, odate, notes, ost, pst))

    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                if replace:
                    cur.execute("DELETE FROM orders")
                for t in rows_out:
                    cur.execute(
                        """
                        INSERT INTO orders
                          (customer_name, order_summary, cup_count, total_amount, order_date, payment_notes, order_status, payment_status)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                        """,
                        t,
                    )
        return len(rows_out)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Routes: dashboard
# ---------------------------------------------------------------------------
@app.route("/")
def dashboard():
    stats = {
        "tasks_total": query("SELECT COUNT(*) AS c FROM tasks", fetch=True, one=True)["c"],
        "tasks_open": query(
            "SELECT COUNT(*) AS c FROM tasks WHERE status <> 'Completed'",
            fetch=True,
            one=True,
        )["c"],
        "inventory_lines": query(
            "SELECT COUNT(*) AS c FROM inventory_items", fetch=True, one=True
        )["c"],
        "orders_total": query("SELECT COUNT(*) AS c FROM orders", fetch=True, one=True)["c"],
        "orders_pending": query(
            "SELECT COUNT(*) AS c FROM orders WHERE order_status = 'Pending'",
            fetch=True,
            one=True,
        )["c"],
    }
    recent_tasks = query(
        """
        SELECT t.id, t.title, t.status, t.priority,
               a.name AS assigned_name,
               c.name AS created_name
        FROM tasks t
        LEFT JOIN members a ON a.id = t.assigned_member_id
        LEFT JOIN members c ON c.id = t.created_by_id
        ORDER BY t.created_at DESC
        LIMIT 5
        """,
        fetch=True,
    )
    return render_template("dashboard.html", stats=stats, recent_tasks=recent_tasks)


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------
@app.route("/tasks")
def tasks_list():
    member_id = request.args.get("member_id", type=int)
    keyword = request.args.get("q", "").strip()
    sql = """
        SELECT t.*, a.name AS assigned_name, c.name AS created_name
        FROM tasks t
        LEFT JOIN members a ON a.id = t.assigned_member_id
        LEFT JOIN members c ON c.id = t.created_by_id
        WHERE 1=1
    """
    params: list = []
    if member_id:
        sql += " AND t.assigned_member_id = %s"
        params.append(member_id)
    if keyword:
        sql += " AND (t.title ILIKE %s OR t.description ILIKE %s)"
        like = f"%{keyword}%"
        params.extend([like, like])
    sql += " ORDER BY t.created_at DESC"
    tasks = query(sql, params, fetch=True)
    members = query("SELECT id, name FROM members ORDER BY name", fetch=True)
    return render_template(
        "tasks.html",
        tasks=tasks,
        members=members,
        selected_member=member_id,
        keyword=keyword,
        statuses=TASK_STATUSES,
    )


@app.route("/tasks/add", methods=["GET", "POST"])
def tasks_add():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        assigned = request.form.get("assigned_member_id") or None
        created = request.form.get("created_by_id") or None
        priority = request.form.get("priority", "Medium")
        if not title:
            flash("Task title is required.", "error")
        elif priority not in TASK_PRIORITIES:
            flash("Invalid priority.", "error")
        else:
            query(
                """INSERT INTO tasks
                   (title, description, assigned_member_id, created_by_id, status, priority)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (title, description, assigned, created, "Not Started", priority),
            )
            flash("Task added.", "success")
            return redirect(url_for("tasks_list"))
    members = query("SELECT id, name FROM members ORDER BY name", fetch=True)
    return render_template("task_add.html", members=members, priorities=TASK_PRIORITIES)


@app.route("/tasks/<int:task_id>/status", methods=["POST"])
def tasks_update_status(task_id):
    status = request.form.get("status")
    if status in TASK_STATUSES:
        query("UPDATE tasks SET status = %s WHERE id = %s", (status, task_id))
        flash("Task status updated.", "success")
    else:
        flash("Invalid status.", "error")
    return redirect(request.referrer or url_for("tasks_list"))


@app.route("/tasks/<int:task_id>/delete", methods=["POST"])
def tasks_delete(task_id):
    query("DELETE FROM tasks WHERE id = %s", (task_id,))
    flash("Task deleted.", "success")
    return redirect(url_for("tasks_list"))


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------
@app.route("/inventory")
def inventory_list():
    items = query(
        "SELECT * FROM inventory_items ORDER BY item_name",
        fetch=True,
    )
    prep = query(
        "SELECT * FROM inventory_prep ORDER BY component_name",
        fetch=True,
    )
    return render_template("inventory.html", items=items, prep=prep)


@app.route("/inventory/add", methods=["GET", "POST"])
def inventory_add():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        try:
            qty = float(request.form.get("qty_grams", "") or 0)
        except ValueError:
            flash("Quantity must be a number.", "error")
            return redirect(url_for("inventory_add"))
        remark = request.form.get("remark", "").strip() or None
        updated = request.form.get("updated_flag") == "on"
        if not name:
            flash("Item name is required.", "error")
            return redirect(url_for("inventory_add"))
        query(
            """
            INSERT INTO inventory_items (item_name, qty_grams, remark, updated_flag)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (item_name) DO UPDATE SET
              qty_grams = EXCLUDED.qty_grams,
              remark = EXCLUDED.remark,
              updated_flag = EXCLUDED.updated_flag
            """,
            (name, qty, remark, updated),
        )
        flash("Inventory item saved.", "success")
        return redirect(url_for("inventory_list"))
    return render_template("inventory_add.html")


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------
@app.route("/orders")
def orders_list():
    orders = query(
        """
        SELECT * FROM orders
        ORDER BY COALESCE(order_date, created_at::date) DESC, id DESC
        """,
        fetch=True,
    )
    return render_template(
        "orders.html",
        orders=orders,
        order_statuses=ORDER_STATUSES,
        payment_statuses=PAYMENT_STATUSES,
    )


@app.route("/orders/add", methods=["GET", "POST"])
def orders_add():
    if request.method == "POST":
        customer = request.form.get("customer_name", "").strip()
        summary = request.form.get("order_summary", "").strip() or None
        try:
            cups = int(request.form.get("cup_count", 1) or 1)
        except ValueError:
            cups = 1
        total = parse_money(request.form.get("total_amount"))
        odate = parse_date(request.form.get("order_date")) or date.today()
        notes = request.form.get("payment_notes", "").strip() or None
        order_status = request.form.get("order_status", "Pending")
        payment_status = request.form.get("payment_status", "Unpaid")
        if not customer:
            flash("Customer name is required.", "error")
        elif order_status not in ORDER_STATUSES or payment_status not in PAYMENT_STATUSES:
            flash("Invalid status.", "error")
        else:
            query(
                """
                INSERT INTO orders
                  (customer_name, order_summary, cup_count, total_amount, order_date, payment_notes, order_status, payment_status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (customer, summary, cups, total, odate, notes, order_status, payment_status),
            )
            flash("Order added.", "success")
            return redirect(url_for("orders_list"))
    return render_template(
        "order_add.html",
        order_statuses=ORDER_STATUSES,
        payment_statuses=PAYMENT_STATUSES,
    )


@app.route("/orders/<int:order_id>/status", methods=["POST"])
def orders_update_status(order_id):
    order_status = request.form.get("order_status")
    payment_status = request.form.get("payment_status")
    if order_status and order_status in ORDER_STATUSES:
        query("UPDATE orders SET order_status = %s WHERE id = %s", (order_status, order_id))
    if payment_status and payment_status in PAYMENT_STATUSES:
        query(
            "UPDATE orders SET payment_status = %s WHERE id = %s",
            (payment_status, order_id),
        )
    flash("Order updated.", "success")
    return redirect(url_for("orders_list"))


# ---------------------------------------------------------------------------
# Finance
# ---------------------------------------------------------------------------
@app.route("/finance")
def finance_summary():
    margin_menu = query(
        "SELECT * FROM margin_menu_items ORDER BY category NULLS LAST, item_name",
        fetch=True,
    )
    margin_ing = query(
        "SELECT * FROM margin_ingredients ORDER BY category NULLS LAST, ingredient",
        fetch=True,
    )
    inflows = query(
        "SELECT * FROM finance_cash_inflows ORDER BY txn_date NULLS LAST, id",
        fetch=True,
    )
    outflows = query(
        "SELECT * FROM finance_cash_outflows ORDER BY txn_date NULLS LAST, id",
        fetch=True,
    )
    rev = query(
        "SELECT COALESCE(SUM(amount),0) AS s FROM finance_cash_inflows",
        fetch=True,
        one=True,
    )["s"]
    exp = query(
        "SELECT COALESCE(SUM(amount),0) AS s FROM finance_cash_outflows",
        fetch=True,
        one=True,
    )["s"]
    return render_template(
        "finance.html",
        margin_menu=margin_menu or [],
        margin_ing=margin_ing or [],
        inflows=inflows or [],
        outflows=outflows or [],
        total_revenue=float(rev or 0),
        total_expenses=float(exp or 0),
        net=float((rev or 0) - (exp or 0)),
    )


# ---------------------------------------------------------------------------
# Members (unchanged behaviour)
# ---------------------------------------------------------------------------
@app.route("/members", methods=["GET", "POST"])
def members_page():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        role = request.form.get("role", "").strip() or None
        email = request.form.get("email", "").strip() or None
        if name:
            query(
                "INSERT INTO members (name, role, email) VALUES (%s, %s, %s)",
                (name, role, email),
            )
            flash("Member added.", "success")
        else:
            flash("Member name is required.", "error")
        return redirect(url_for("members_page"))
    members = query("SELECT * FROM members ORDER BY name", fetch=True)
    return render_template("members.html", members=members)


# ---------------------------------------------------------------------------
# Recipes
# ---------------------------------------------------------------------------
@app.route("/recipes", methods=["GET", "POST"])
def recipes_page():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        drink_category = request.form.get("drink_category", "").strip() or None
        is_latte = request.form.get("is_latte") == "on"
        cloud_type = request.form.get("cloud_type") or None
        flavour_name = (request.form.get("flavour_name") or "").strip()
        notes = request.form.get("notes", "").strip() or None

        if not name:
            flash("Recipe name is required.", "error")
            return redirect(url_for("recipes_page"))
        if is_latte:
            if cloud_type not in CLOUD_TYPES:
                flash("Lattes need a cloud: coffee or matcha.", "error")
                return redirect(url_for("recipes_page"))
        else:
            cloud_type = None
        try:
            query(
                """
                INSERT INTO recipes (name, drink_category, is_latte, cloud_type, flavour_name, notes)
                VALUES (%s,%s,%s,%s,%s,%s)
                """,
                (name, drink_category, is_latte, cloud_type, flavour_name, notes),
            )
            flash("Recipe added.", "success")
        except Exception as exc:  # noqa: BLE001
            flash(f"Could not save recipe: {exc}", "error")
        return redirect(url_for("recipes_page"))

    recipes = query("SELECT * FROM recipes ORDER BY created_at DESC", fetch=True)
    return render_template(
        "recipes.html",
        recipes=recipes or [],
        cloud_types=CLOUD_TYPES,
    )


# ---------------------------------------------------------------------------
# Import / export
# ---------------------------------------------------------------------------
@app.route("/data", methods=["GET", "POST"])
def data_import_export():
    if request.method == "POST":
        kind = request.form.get("import_kind", "")
        replace = request.form.get("replace_existing") == "on"
        f = request.files.get("file")
        if not f or not f.filename:
            flash("Choose a CSV file to upload.", "error")
            return redirect(url_for("data_import_export"))
        try:
            if kind == "inventory":
                n1, n2 = import_inventory_csv(f.stream, replace=replace)
                flash(f"Inventory: {n1} items, {n2} prep rows imported.", "success")
            elif kind == "margins":
                a, b = import_margins_csv(f.stream, replace=replace)
                flash(f"Margins: {a} ingredients, {b} menu lines imported.", "success")
            elif kind == "finance":
                a, b = import_financial_csv(f.stream, replace=replace)
                flash(f"Finance: {a} inflows, {b} outflows imported.", "success")
            elif kind == "orders":
                n = import_orders_csv(f.stream, replace=replace)
                flash(f"Orders: {n} rows imported.", "success")
            else:
                flash("Unknown import type.", "error")
        except Exception as exc:  # noqa: BLE001
            flash(f"Import failed: {exc}", "error")
        return redirect(url_for("data_import_export"))
    return render_template("import_export.html")


@app.route("/export/<name>")
def export_table(name):
    mapping = {
        "inventory_items": (
            "inventory_items.csv",
            ["item_name", "qty_grams", "remark", "updated_flag"],
            "SELECT item_name, qty_grams, remark, updated_flag FROM inventory_items ORDER BY item_name",
        ),
        "inventory_prep": (
            "inventory_prep.csv",
            ["component_name", "qty_for_week", "ready"],
            "SELECT component_name, qty_for_week, ready FROM inventory_prep ORDER BY component_name",
        ),
        "margin_ingredients": (
            "margin_ingredients.csv",
            [
                "category",
                "ingredient",
                "cost_per_cup",
                "amt_used_g",
                "source_cost",
                "source_qty_g",
                "supplier",
            ],
            "SELECT category, ingredient, cost_per_cup, amt_used_g, source_cost, source_qty_g, supplier FROM margin_ingredients ORDER BY id",
        ),
        "margin_menu_items": (
            "margin_menu_items.csv",
            ["category", "item_name", "cost", "selling_price", "profit"],
            "SELECT category, item_name, cost, selling_price, profit FROM margin_menu_items ORDER BY id",
        ),
        "finance_inflows": (
            "finance_cash_inflows.csv",
            [
                "source_txn_number",
                "amount",
                "description",
                "quantity_cups",
                "txn_date",
                "screenshot",
                "person_in_charge",
            ],
            """
            SELECT source_txn_number, amount, description, quantity_cups, txn_date::text,
                   screenshot, person_in_charge
            FROM finance_cash_inflows ORDER BY id
            """,
        ),
        "finance_outflows": (
            "finance_cash_outflows.csv",
            [
                "source_txn_number",
                "amount",
                "description",
                "txn_date",
                "screenshot",
                "person_in_charge",
            ],
            """
            SELECT source_txn_number, amount, description, txn_date::text,
                   screenshot, person_in_charge
            FROM finance_cash_outflows ORDER BY id
            """,
        ),
        "orders": (
            "orders.csv",
            [
                "customer_name",
                "order_summary",
                "cup_count",
                "total_amount",
                "order_date",
                "payment_notes",
                "order_status",
                "payment_status",
            ],
            """
            SELECT customer_name, order_summary, cup_count, total_amount, order_date::text,
                   payment_notes, order_status, payment_status
            FROM orders ORDER BY id
            """,
        ),
        "recipes": (
            "recipes.csv",
            ["name", "drink_category", "is_latte", "cloud_type", "flavour_name", "notes"],
            """
            SELECT name, drink_category, is_latte, cloud_type, flavour_name, notes
            FROM recipes ORDER BY id
            """,
        ),
    }
    if name not in mapping:
        flash("Unknown export.", "error")
        return redirect(url_for("data_import_export"))
    fname, header, sql = mapping[name]
    rows = query(sql, fetch=True)
    out = []
    for r in rows or []:
        out.append([r.get(h) for h in header])
    return csv_response(fname, out, header=header)


# ---------------------------------------------------------------------------
# Errors + run
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(_e):
    return render_template("error.html", code=404, message="Page not found."), 404


@app.errorhandler(500)
def server_error(_e):
    return render_template("error.html", code=500, message="Something went wrong on the server."), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
