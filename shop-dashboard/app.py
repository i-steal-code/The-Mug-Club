"""
Online Shop Operations Dashboard
================================
H2 Computing mini-project (task-tracker + shop modules).

Stack:
    Flask (backend)
    Jinja2 HTML templates + plain CSS (frontend)
    Supabase Postgres (SQL database, connected via psycopg2)

This single file keeps things simple so the code is easy to explain in class.
Each section is commented.
"""

import os
from flask import (
    Flask, render_template, request, redirect, url_for, flash
)
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
load_dotenv()  # read .env locally; on Vercel we use real env vars

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "school-project-secret")

DATABASE_URL = os.getenv("DATABASE_URL")

# Keep allowed values in one place so routes AND templates share them.
TASK_STATUSES = ["Not Started", "In Progress", "Completed"]
TASK_PRIORITIES = ["Low", "Medium", "High"]
ORDER_STATUSES = ["Pending", "Processing", "Completed", "Cancelled"]
PAYMENT_STATUSES = ["Unpaid", "Paid", "Refunded"]


# ---------------------------------------------------------------------------
# Database helper
# ---------------------------------------------------------------------------
def get_conn():
    """Open a new connection to the Supabase Postgres database."""
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not set. Copy .env.example to .env and fill it in."
        )
    # Supabase requires SSL.
    return psycopg2.connect(DATABASE_URL, sslmode="require")


def query(sql, params=None, fetch=False, one=False):
    """
    Run a SQL query safely.
    - fetch=False  → INSERT / UPDATE / DELETE (no results returned).
    - fetch=True   → SELECT returning many rows (list of dicts).
    - fetch=True, one=True → SELECT returning a single row (dict or None).

    psycopg2 uses %s for parameter substitution which protects against
    SQL injection; we never concatenate user input into SQL strings.
    """
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params or ())
            if fetch:
                rows = cur.fetchall()
                result = (rows[0] if rows else None) if one else rows
            else:
                result = None
        conn.commit()
        return result
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Dashboard (home page)
# ---------------------------------------------------------------------------
@app.route("/")
def dashboard():
    """Landing page with a few high-level numbers."""
    stats = {
        "tasks_total":    query("SELECT COUNT(*) AS c FROM tasks", fetch=True, one=True)["c"],
        "tasks_open":     query("SELECT COUNT(*) AS c FROM tasks WHERE status <> 'Completed'", fetch=True, one=True)["c"],
        "products_total": query("SELECT COUNT(*) AS c FROM products", fetch=True, one=True)["c"],
        "products_low":   query("SELECT COUNT(*) AS c FROM products WHERE stock_quantity < 5", fetch=True, one=True)["c"],
        "orders_total":   query("SELECT COUNT(*) AS c FROM orders", fetch=True, one=True)["c"],
        "orders_pending": query("SELECT COUNT(*) AS c FROM orders WHERE order_status = 'Pending'", fetch=True, one=True)["c"],
    }
    recent_tasks = query(
        """
        SELECT t.id, t.title, t.status, t.priority,
               a.name AS assigned_name, c.name AS created_name
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
# Task Management  (this module is the core assignment deliverable)
# ---------------------------------------------------------------------------
@app.route("/tasks")
def tasks_list():
    """
    Show every task. Supports:
      - filter by assigned member (?member_id=...)
      - keyword search in title / description (?q=...)
    """
    member_id = request.args.get("member_id", type=int)
    keyword = request.args.get("q", "").strip()

    sql = """
        SELECT t.*,
               a.name AS assigned_name,
               c.name AS created_name
        FROM tasks t
        LEFT JOIN members a ON a.id = t.assigned_member_id
        LEFT JOIN members c ON c.id = t.created_by_id
        WHERE 1=1
    """
    params = []
    if member_id:
        sql += " AND t.assigned_member_id = %s"
        params.append(member_id)
    if keyword:
        sql += " AND (t.title ILIKE %s OR t.description ILIKE %s)"
        params.extend([f"%{keyword}%", f"%{keyword}%"])
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
    """GET: show the add-task form. POST: insert a new task."""
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
    """Change a task's status using the inline dropdown on the tasks page."""
    status = request.form.get("status")
    if status in TASK_STATUSES:
        query("UPDATE tasks SET status = %s WHERE id = %s", (status, task_id))
        flash("Task status updated.", "success")
    else:
        flash("Invalid status.", "error")
    return redirect(request.referrer or url_for("tasks_list"))


@app.route("/tasks/<int:task_id>/delete", methods=["POST"])
def tasks_delete(task_id):
    """Delete a task (confirmation handled in the browser)."""
    query("DELETE FROM tasks WHERE id = %s", (task_id,))
    flash("Task deleted.", "success")
    return redirect(url_for("tasks_list"))


# ---------------------------------------------------------------------------
# Inventory Management
# ---------------------------------------------------------------------------
@app.route("/inventory")
def inventory_list():
    """Show all products with a low-stock indicator."""
    category = request.args.get("category", "").strip()
    sql = "SELECT * FROM products"
    params = []
    if category:
        sql += " WHERE category = %s"
        params.append(category)
    sql += " ORDER BY name"
    products = query(sql, params, fetch=True)
    cat_rows = query(
        "SELECT DISTINCT category FROM products WHERE category IS NOT NULL ORDER BY category",
        fetch=True,
    )
    return render_template(
        "inventory.html",
        products=products,
        categories=[r["category"] for r in cat_rows],
        selected_category=category,
    )


@app.route("/inventory/add", methods=["GET", "POST"])
def inventory_add():
    """GET: product form. POST: insert a new product."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip() or None
        try:
            stock = int(request.form.get("stock_quantity", 0))
            cost = float(request.form.get("cost_price", 0))
            price = float(request.form.get("selling_price", 0))
        except ValueError:
            flash("Stock / price fields must be numbers.", "error")
            return redirect(url_for("inventory_add"))
        if not name:
            flash("Product name is required.", "error")
            return redirect(url_for("inventory_add"))

        query(
            """INSERT INTO products (name, category, stock_quantity, cost_price, selling_price)
               VALUES (%s, %s, %s, %s, %s)""",
            (name, category, stock, cost, price),
        )
        flash("Product added.", "success")
        return redirect(url_for("inventory_list"))

    return render_template("inventory_add.html")


# ---------------------------------------------------------------------------
# Order Management
# ---------------------------------------------------------------------------
@app.route("/orders")
def orders_list():
    """Show every order with product name + computed order total."""
    orders = query(
        """SELECT o.*, p.name AS product_name, p.selling_price
           FROM orders o
           LEFT JOIN products p ON p.id = o.product_id
           ORDER BY o.created_at DESC""",
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
    """GET: order form. POST: create a new order."""
    if request.method == "POST":
        customer = request.form.get("customer_name", "").strip()
        product_id = request.form.get("product_id") or None
        try:
            qty = int(request.form.get("quantity", 1))
        except ValueError:
            qty = 1
        order_status = request.form.get("order_status", "Pending")
        payment_status = request.form.get("payment_status", "Unpaid")

        if not customer or not product_id:
            flash("Customer name and product are both required.", "error")
        elif order_status not in ORDER_STATUSES or payment_status not in PAYMENT_STATUSES:
            flash("Invalid status selected.", "error")
        else:
            query(
                """INSERT INTO orders
                   (customer_name, product_id, quantity, order_status, payment_status)
                   VALUES (%s, %s, %s, %s, %s)""",
                (customer, product_id, qty, order_status, payment_status),
            )
            flash("Order added.", "success")
            return redirect(url_for("orders_list"))

    products = query("SELECT id, name, selling_price FROM products ORDER BY name", fetch=True)
    return render_template(
        "order_add.html",
        products=products,
        order_statuses=ORDER_STATUSES,
        payment_statuses=PAYMENT_STATUSES,
    )


@app.route("/orders/<int:order_id>/status", methods=["POST"])
def orders_update_status(order_id):
    """Update order status and/or payment status from the orders page."""
    order_status = request.form.get("order_status")
    payment_status = request.form.get("payment_status")
    if order_status and order_status in ORDER_STATUSES:
        query("UPDATE orders SET order_status = %s WHERE id = %s", (order_status, order_id))
    if payment_status and payment_status in PAYMENT_STATUSES:
        query("UPDATE orders SET payment_status = %s WHERE id = %s", (payment_status, order_id))
    flash("Order updated.", "success")
    return redirect(url_for("orders_list"))


# ---------------------------------------------------------------------------
# Financial Margins / Profit
# ---------------------------------------------------------------------------
@app.route("/finance")
def finance_summary():
    """
    For each product, compute margin per unit and estimated profit.
    Profit only counts 'Completed' orders so it reflects real sales,
    not pending ones.
    """
    rows = query(
        """
        SELECT
            p.id,
            p.name,
            p.category,
            p.cost_price,
            p.selling_price,
            (p.selling_price - p.cost_price) AS margin_per_unit,
            COALESCE(SUM(CASE WHEN o.order_status = 'Completed'
                              THEN o.quantity ELSE 0 END), 0) AS units_sold,
            COALESCE(SUM(CASE WHEN o.order_status = 'Completed'
                              THEN o.quantity * (p.selling_price - p.cost_price)
                              ELSE 0 END), 0) AS estimated_profit
        FROM products p
        LEFT JOIN orders o ON o.product_id = p.id
        GROUP BY p.id
        ORDER BY estimated_profit DESC
        """,
        fetch=True,
    )
    total_profit = sum((r["estimated_profit"] or 0) for r in rows)
    return render_template("finance.html", rows=rows, total_profit=total_profit)


# ---------------------------------------------------------------------------
# Members (staff roster)
# ---------------------------------------------------------------------------
@app.route("/members", methods=["GET", "POST"])
def members_page():
    """List staff members and add new ones."""
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
# Error handling
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(_e):
    return render_template("error.html",
                           code=404,
                           message="Page not found."), 404


@app.errorhandler(500)
def server_error(_e):
    return render_template("error.html",
                           code=500,
                           message="Something went wrong on the server."), 500


# ---------------------------------------------------------------------------
# Local dev entrypoint (Vercel uses the `app` object directly)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, port=5000)
