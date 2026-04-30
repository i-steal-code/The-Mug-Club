"""
The Mug Club — operations dashboard (Flask + PostgreSQL / Supabase).
Deploy: Render Web Service + Supabase Postgres (DATABASE_URL).
v0.2.3 — components rework, 1NF finance, morphing order buttons, recipe databank, anti-cold-start hooks.
"""

from __future__ import annotations

import csv
import io
import ipaddress
import json
import os
import urllib.error
import urllib.request
import re
import secrets
import socket
import threading
import time
from datetime import date, datetime
from urllib.parse import parse_qs, unquote, urlparse

import psycopg2
from flask import (
    Flask,
    Response,
    abort,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from psycopg2 import OperationalError, extras
from psycopg2.extensions import connection as PgConnection

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.environ.get("DATABASE_URL")


def _agent_debug_log(
    location: str,
    message: str,
    *,
    hypothesis_id: str,
    data: dict | None = None,
    run_id: str = "pre-fix",
) -> None:
    # region agent log
    payload = {
        "sessionId": "5bc04c",
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data or {},
        "timestamp": int(time.time() * 1000),
    }
    line = json.dumps(payload, default=str) + "\n"
    try:
        with open(
            os.path.join(BASE_DIR, "debug-5bc04c.log"), "a", encoding="utf-8"
        ) as _lf:
            _lf.write(line)
    except Exception:
        pass
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:7841/ingest/d7bf6410-c1ca-4d49-8fc4-3948c0f33670",
            data=line.encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Debug-Session-Id": "5bc04c",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            resp.read()
    except (urllib.error.URLError, TimeoutError, OSError):
        pass
    except Exception:
        pass
    # endregion

# v0.2.5 — minimal shared-password auth. Single password for all staff; tracked
# per device by a long-lived cookie. STAFF_PASSWORD env var overrides default.
STAFF_PASSWORD = os.environ.get("STAFF_PASSWORD", "mugclub")
DEVICE_COOKIE_NAME = "mc_device_id"
DEVICE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # 1 year
# Public endpoints that bypass auth (login flow, health probes, customer shop,
# static assets). Anything else requires session["authed"] == True.
PUBLIC_ENDPOINTS = {
    "static",
    "login",
    "login_submit",
    "logout",
    "healthz",
    "warm",
    "shop_order_form",
    "shop_order_submit",
}

TASK_STATUSES = ["Not Started", "In Progress", "Completed"]
TASK_STATUS_CYCLE = ["Not Started", "In Progress", "Completed"]
TASK_PRIORITIES = ["Low", "Medium", "High"]
ORDER_STATUSES = ["Pending", "Processing", "Completed", "Cancelled"]
PAYMENT_STATUSES = ["Unpaid", "Paid", "Refunded"]
# Morphing button cycles for the orders page (v0.2.3).
# Cancelled is still valid for imports / manual rollback but lives outside the cycle.
ORDER_STATUS_CYCLE = ["Pending", "Processing", "Completed"]
PAYMENT_STATUS_CYCLE = ["Unpaid", "Paid"]
CLOUD_TYPES = ("coffee", "matcha")
# Customer-facing payment choice — simplified to two canonical values shared
# with the finance 1NF sheet so orders flow in without translation.
CUSTOMER_PAYMENT_METHODS = (
    ("paynow", "PayNow (scan QR)"),
    ("cash", "Cash / in person at collection"),
)
PRODUCT_TYPES = ("latte", "special")


def _host_is_literal_ip(host: str) -> bool:
    """
    True if host is already an IPv4 or IPv6 address string.
    `ipaddress.ip_address()` raises ValueError for hostnames (e.g. db.xxx.supabase.co),
    not only for "non-IP" text — a hostname is not a valid single IP object.
    """
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


def _first_ipv4_addr(hostname: str, port: int) -> str | None:
    """
    Return an IPv4 address for hostname for use as libpq hostaddr.

    Some resolvers (e.g. on Render) return AAAA first or only, so a plain
    getaddrinfo() scan can find no AF_INET even when an A record exists. Request
    IPv4-only resolution first, then fall back to gethostbyname (A record only).
    """
    for resolver in (_ipv4_getaddrinfo_inet, _ipv4_gethostbyname):
        try:
            ip = resolver(hostname, port)
        except OSError:
            continue
        if ip:
            return ip
    return None


def _ipv4_getaddrinfo_inet(hostname: str, port: int) -> str | None:
    try:
        infos = socket.getaddrinfo(
            hostname, port, family=socket.AF_INET, type=socket.SOCK_STREAM
        )
    except OSError:
        return None
    for _fam, _t, _p, _c, sockaddr in infos:
        if sockaddr and len(sockaddr) >= 1 and sockaddr[0]:
            return str(sockaddr[0])
    return None


def _ipv4_gethostbyname(hostname: str, _port: int) -> str | None:
    """Returns IPv4 string from A record only; raises OSError if none."""
    return socket.gethostbyname(hostname)


def _connect_kwargs_from_database_url(url: str) -> dict:
    """
    Build psycopg2 keyword args from a postgresql:// URI.

    Render (and some hosts) cannot reach Supabase over IPv6 even when DNS returns
    AAAA first → "Network is unreachable". Passing hostaddr=<IPv4> with host=<FQDN>
    forces IPv4 while keeping the correct TLS server name.
    """
    try:
        parsed = urlparse(url)
    except ValueError as e:
        raise RuntimeError(
            "Invalid DATABASE_URL: the URI is malformed. Common causes: (1) square brackets [ ] "
            "around the hostname—only use [ ] for a literal IPv6 address, never wrap "
            "db.xxxxx.supabase.co in brackets. (2) A database password containing @, :, /, ?, #, "
            "[, ], or & must be percent-encoded in the URI. Copy the connection string from "
            f"Supabase (Database settings) and paste it unchanged. Parser error: {e}"
        ) from e
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
    for drop in ("port", "host", "user", "password", "dbname"):
        extra.pop(drop, None)
    if "sslmode" not in q:
        extra["sslmode"] = "require"

    base: dict = {
        "dbname": dbname,
        "user": user,
        "password": password,
        "port": int(port),
        **extra,
    }

    if not host:
        return base

    if host and "pooler.supabase.com" in host.lower() and user == "postgres":
        raise RuntimeError(
            "Supabase pooler requires username postgres.<project-ref>, not only 'postgres'. "
            "In Supabase → Database → Connection string, choose Session pooler (or Transaction) "
            "and copy the full URI; the user looks like postgres.abcxyz (your project ref after the dot)."
        )

    if _host_is_literal_ip(host):
        return {**base, "host": host}

    ipv4 = _first_ipv4_addr(host, int(port))
    if ipv4:
        return {**base, "host": host, "hostaddr": ipv4}
    # Do not fall back to hostname-only: libpq will use IPv6 (AAAA) and often fail
    # on hosts like Render with "Network is unreachable" to Supabase.
    raise RuntimeError(
        f"No IPv4 (A) address found for {host!r} from this environment. "
        "Use Supabase → Database → Connection string → Session pooler "
        "(IPv4-proxied; user like postgres.<project-ref> on port 5432), or Transaction "
        "mode pooler on port 6543, or confirm a public IPv4 A record for the direct host."
    )


def _connect() -> PgConnection:
    """Open a new DB connection (no schema bootstrap — used internally)."""
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not set. Add your Supabase connection string "
            "(see .env.example) for local runs and Render."
        )
    url = DATABASE_URL
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    kwargs = _connect_kwargs_from_database_url(url)
    try:
        return psycopg2.connect(cursor_factory=extras.RealDictCursor, **kwargs)
    except OperationalError as e:
        err = str(e).lower()
        if "tenant or user not found" in err:
            raise RuntimeError(
                "Database rejected the login: 'Tenant or user not found' (Supabase pooler). "
                "Use username postgres.<your-project-ref> from the Session (or Transaction) pooler "
                "connection string— not the direct-DB user 'postgres' alone. Confirm the password "
                "is the database password and the URI was copied from Database → Connection string."
            ) from e
        raise


_schema_lock = threading.Lock()
_schema_ready = False


def get_conn() -> PgConnection:
    _ensure_schema_applied()
    return _connect()


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


_SCHEMA_MIGRATION_DDL = [
    """
    ALTER TABLE recipes ADD COLUMN IF NOT EXISTS base_yield_cups
      DOUBLE PRECISION NOT NULL DEFAULT 1
    """,
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_method TEXT",
    "ALTER TABLE inventory_items ADD COLUMN IF NOT EXISTS source_cost DOUBLE PRECISION",
    "ALTER TABLE inventory_items ADD COLUMN IF NOT EXISTS source_qty_g DOUBLE PRECISION",
    "ALTER TABLE inventory_items ADD COLUMN IF NOT EXISTS supplier TEXT",
    "ALTER TABLE finance_cash_inflows DROP COLUMN IF EXISTS linked_order_id",
    """
    CREATE TABLE IF NOT EXISTS recipe_steps (
        id SERIAL PRIMARY KEY,
        recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
        step_order INTEGER NOT NULL DEFAULT 0,
        body TEXT NOT NULL,
        completed BOOLEAN NOT NULL DEFAULT FALSE
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_recipe_steps_recipe ON recipe_steps(recipe_id)",
    """
    CREATE TABLE IF NOT EXISTS recipe_ingredients (
        id SERIAL PRIMARY KEY,
        recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
        sort_order INTEGER NOT NULL DEFAULT 0,
        inventory_item_id INTEGER REFERENCES inventory_items(id) ON DELETE SET NULL,
        label_override TEXT,
        qty_per_yield DOUBLE PRECISION,
        unit TEXT NOT NULL DEFAULT 'g'
    )
    """,
    "ALTER TABLE recipe_ingredients ADD COLUMN IF NOT EXISTS inventory_item_id INTEGER",
    "ALTER TABLE recipe_ingredients ADD COLUMN IF NOT EXISTS label_override TEXT",
    """
    DO $$ BEGIN
      ALTER TABLE recipe_ingredients
        ADD CONSTRAINT recipe_ingredients_inventory_item_id_fkey
        FOREIGN KEY (inventory_item_id) REFERENCES inventory_items(id) ON DELETE SET NULL;
    EXCEPTION WHEN duplicate_object THEN NULL;
    END $$
    """,
    "CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_recipe ON recipe_ingredients(recipe_id)",
    """
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        product_name TEXT NOT NULL UNIQUE,
        product_type TEXT NOT NULL DEFAULT 'special'
            CHECK (product_type IN ('latte', 'special')),
        cloud_type TEXT CHECK (cloud_type IS NULL OR cloud_type IN ('coffee', 'matcha')),
        flavour_name TEXT,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        display_order INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS order_items (
        id SERIAL PRIMARY KEY,
        order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
        product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
        quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
        unit_price DOUBLE PRECISION,
        remarks TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id)",
    "CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items(product_id)",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS selling_price DOUBLE PRECISION",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS short_desc TEXT",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS image_url TEXT",
    "ALTER TABLE recipes ADD COLUMN IF NOT EXISTS product_id INTEGER UNIQUE",
    """
    DO $$ BEGIN
      ALTER TABLE recipes
        ADD CONSTRAINT recipes_product_id_fkey
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE;
    EXCEPTION WHEN duplicate_object THEN NULL;
    END $$
    """,
    """
    CREATE TABLE IF NOT EXISTS flavours (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        cloud_type TEXT CHECK (cloud_type IS NULL OR cloud_type IN ('coffee', 'matcha')),
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        display_order INTEGER NOT NULL DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS recipe_components (
        id SERIAL PRIMARY KEY,
        recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
        component_name TEXT NOT NULL,
        remarks TEXT,
        sort_order INTEGER NOT NULL DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS recipe_component_prep (
        id SERIAL PRIMARY KEY,
        component_id INTEGER NOT NULL REFERENCES recipe_components(id) ON DELETE CASCADE,
        prep_name TEXT NOT NULL,
        remarks TEXT,
        done BOOLEAN NOT NULL DEFAULT FALSE,
        sort_order INTEGER NOT NULL DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS recipe_component_steps (
        id SERIAL PRIMARY KEY,
        component_id INTEGER NOT NULL REFERENCES recipe_components(id) ON DELETE CASCADE,
        step_name TEXT NOT NULL,
        remarks TEXT,
        done BOOLEAN NOT NULL DEFAULT FALSE,
        sort_order INTEGER NOT NULL DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS recipe_assembly_steps (
        id SERIAL PRIMARY KEY,
        recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
        step_name TEXT NOT NULL,
        remarks TEXT,
        done BOOLEAN NOT NULL DEFAULT FALSE,
        sort_order INTEGER NOT NULL DEFAULT 0
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_recipes_product ON recipes(product_id)",
    "CREATE INDEX IF NOT EXISTS idx_recipe_components_recipe ON recipe_components(recipe_id)",
    "CREATE INDEX IF NOT EXISTS idx_recipe_prep_component ON recipe_component_prep(component_id)",
    "CREATE INDEX IF NOT EXISTS idx_recipe_steps_component ON recipe_component_steps(component_id)",
    "CREATE INDEX IF NOT EXISTS idx_recipe_assembly_recipe ON recipe_assembly_steps(recipe_id)",
    # v0.2.3 — standalone reusable components (shared across product recipes).
    """
    CREATE TABLE IF NOT EXISTS components (
        id             SERIAL PRIMARY KEY,
        name           TEXT NOT NULL UNIQUE,
        component_type TEXT,
        notes          TEXT,
        base_yield     DOUBLE PRECISION NOT NULL DEFAULT 1,
        created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS component_ingredients (
        id                SERIAL PRIMARY KEY,
        component_id      INTEGER NOT NULL REFERENCES components(id) ON DELETE CASCADE,
        inventory_item_id INTEGER REFERENCES inventory_items(id) ON DELETE SET NULL,
        label_override    TEXT,
        qty_g             DOUBLE PRECISION,
        sort_order        INTEGER NOT NULL DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS component_steps (
        id           SERIAL PRIMARY KEY,
        component_id INTEGER NOT NULL REFERENCES components(id) ON DELETE CASCADE,
        body         TEXT NOT NULL,
        sort_order   INTEGER NOT NULL DEFAULT 0,
        done         BOOLEAN NOT NULL DEFAULT FALSE
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_component_ingredients ON component_ingredients(component_id)",
    "CREATE INDEX IF NOT EXISTS idx_component_steps ON component_steps(component_id)",
    # A product recipe ingredient can now reference a reusable component
    # instead of a raw inventory item (flavour components etc.).
    "ALTER TABLE recipe_ingredients ADD COLUMN IF NOT EXISTS component_id INTEGER",
    """
    DO $$ BEGIN
      ALTER TABLE recipe_ingredients
        ADD CONSTRAINT recipe_ingredients_component_id_fkey
        FOREIGN KEY (component_id) REFERENCES components(id) ON DELETE SET NULL;
    EXCEPTION WHEN duplicate_object THEN NULL;
    END $$
    """,
    "CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_component ON recipe_ingredients(component_id)",
    # Finance 1NF rework (v0.2.3): one row per singular product bought.
    "ALTER TABLE finance_cash_inflows ADD COLUMN IF NOT EXISTS customer_name TEXT",
    "ALTER TABLE finance_cash_inflows ADD COLUMN IF NOT EXISTS product_name TEXT",
    "ALTER TABLE finance_cash_inflows ADD COLUMN IF NOT EXISTS payment_type TEXT",
    "ALTER TABLE finance_cash_inflows ADD COLUMN IF NOT EXISTS payment_status TEXT",
    """
    DO $$ BEGIN
      ALTER TABLE finance_cash_inflows
        ADD CONSTRAINT finance_cash_inflows_payment_type_chk
        CHECK (payment_type IS NULL OR payment_type IN ('paynow', 'cash'));
    EXCEPTION WHEN duplicate_object THEN NULL;
    END $$
    """,
    """
    DO $$ BEGIN
      ALTER TABLE finance_cash_inflows
        ADD CONSTRAINT finance_cash_inflows_payment_status_chk
        CHECK (payment_status IS NULL OR payment_status IN ('paid', 'unpaid'));
    EXCEPTION WHEN duplicate_object THEN NULL;
    END $$
    """,
    # v0.2.6 — link each inflow row to `products` for consistent names in finance + analytics.
    "ALTER TABLE finance_cash_inflows ADD COLUMN IF NOT EXISTS product_id INTEGER",
    """
    DO $$ BEGIN
      ALTER TABLE finance_cash_inflows
        ADD CONSTRAINT finance_cash_inflows_product_id_fkey
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL;
    EXCEPTION WHEN duplicate_object THEN NULL;
    END $$
    """,
    "CREATE INDEX IF NOT EXISTS idx_finance_inflows_product ON finance_cash_inflows(product_id)",
    """
    UPDATE finance_cash_inflows f
    SET product_id = p.id
    FROM products p
    WHERE f.product_id IS NULL
      AND lower(regexp_replace(trim(COALESCE(f.product_name, '')), '\\s+', ' ', 'g'))
        = lower(regexp_replace(trim(COALESCE(p.product_name, '')), '\\s+', ' ', 'g'))
    """,
    # Orders get a "finance_pushed_at" stamp so completion → 1NF finance insert
    # only happens once, even if the buttons are re-clicked (idempotent).
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS finance_pushed_at TIMESTAMPTZ",
    # v0.2.5 — per-ingredient prep note + checkbox state on each recipe line.
    "ALTER TABLE recipe_ingredients ADD COLUMN IF NOT EXISTS prep_note TEXT",
    "ALTER TABLE recipe_ingredients ADD COLUMN IF NOT EXISTS prep_done BOOLEAN NOT NULL DEFAULT FALSE",
    # v0.2.5 — weekly prep plan groundwork for the dashboard prep components card.
    """
    CREATE TABLE IF NOT EXISTS prep_plan (
        id              SERIAL PRIMARY KEY,
        week_start      DATE,
        component_id    INTEGER REFERENCES components(id) ON DELETE SET NULL,
        component_label TEXT NOT NULL,
        qty_to_prep     DOUBLE PRECISION NOT NULL DEFAULT 0,
        notes           TEXT,
        sort_order      INTEGER NOT NULL DEFAULT 0,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_prep_plan_component ON prep_plan(component_id)",
    "CREATE INDEX IF NOT EXISTS idx_prep_plan_week ON prep_plan(week_start)",
]


def ensure_schema_only() -> None:
    conn = _connect()
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
            with conn.cursor() as cur:
                for stmt in _SCHEMA_MIGRATION_DDL:
                    stmt = stmt.strip()
                    if stmt:
                        cur.execute(stmt)
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS c FROM products")
                has_products = int(cur.fetchone()["c"] or 0) > 0
            if not has_products:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO products (product_name, product_type, cloud_type, flavour_name, is_active)
                        SELECT DISTINCT
                          name,
                          CASE WHEN is_latte THEN 'latte' ELSE 'special' END,
                          cloud_type,
                          NULLIF(flavour_name, ''),
                          TRUE
                        FROM recipes
                        WHERE COALESCE(NULLIF(name, ''), '') <> ''
                        ON CONFLICT (product_name) DO NOTHING
                        """
                    )
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO flavours (name, cloud_type, is_active, display_order)
                    VALUES
                      ('original', NULL, TRUE, 10),
                      ('strawberry', 'matcha', TRUE, 20),
                      ('honey buttercream', NULL, TRUE, 30),
                      ('mocha', 'coffee', TRUE, 40)
                    ON CONFLICT (name) DO NOTHING
                    """
                )
                cur.execute(
                    """
                    UPDATE recipes r
                    SET product_id = p.id
                    FROM products p
                    WHERE r.product_id IS NULL AND lower(trim(r.name)) = lower(trim(p.product_name))
                    """
                )
                # v0.2.5 — guarantee every product has a recipe row so the
                # recipe databank exposes it for editing. Steps stay empty so
                # operators fill them in by hand from the UI.
                cur.execute(
                    """
                    INSERT INTO recipes
                      (product_id, name, drink_category, is_latte, cloud_type, flavour_name, base_yield_cups, notes)
                    SELECT
                      p.id,
                      p.product_name,
                      CASE
                        WHEN p.product_type = 'latte' AND p.cloud_type = 'matcha' THEN 'matcha latte'
                        WHEN p.product_type = 'latte' AND p.cloud_type = 'coffee' THEN 'coffee latte'
                        WHEN p.product_type = 'latte'                              THEN 'latte'
                        ELSE                                                            'special'
                      END,
                      (p.product_type = 'latte'),
                      p.cloud_type,
                      COALESCE(p.flavour_name, ''),
                      1,
                      'Auto-seeded recipe row. Fill in ingredients + product recipe steps from the recipe databank.'
                    FROM products p
                    WHERE NOT EXISTS (SELECT 1 FROM recipes r WHERE r.product_id = p.id)
                    """
                )
                # Seed cloud + flavour reusable components so prep dashboard
                # has stable rows to map to from day one.
                cur.execute(
                    """
                    INSERT INTO components (name, component_type, base_yield, notes)
                    VALUES
                      ('Matcha cloud',        'cloud',   1, 'Whisked matcha base for matcha lattes.'),
                      ('Coffee cloud',        'cloud',   1, 'Brewed espresso shot for coffee lattes.'),
                      ('Strawberry flavour',  'flavour', 1, 'Strawberry puree base for strawberry lattes / milk.'),
                      ('Honey buttercream',   'flavour', 1, 'Honey + salted butter cream for buttercream drinks.'),
                      ('Mocha flavour',       'flavour', 1, 'Cocoa-forward base for mocha drinks.'),
                      ('Iced chocolate base', 'flavour', 1, 'Hot chocolate / iced chocolate base.'),
                      ('Tiramisu cream',      'flavour', 1, 'Cream cheese + cream + ladyfinger setup for tiramisu cups.')
                    ON CONFLICT (name) DO NOTHING
                    """
                )
    finally:
        conn.close()


def _ensure_schema_applied() -> None:
    global _schema_ready
    if _schema_ready or not DATABASE_URL:
        return
    with _schema_lock:
        if _schema_ready or not DATABASE_URL:
            return
        ensure_schema_only()
        _schema_ready = True


@app.before_request
def _require_database_url():
    if DATABASE_URL or request.endpoint in ("static", "healthz", "warm"):
        return None
    return render_template("setup.html"), 503


@app.before_request
def _require_login():
    """
    Gate every operations-side endpoint behind the shared staff password.
    /shop and health probes stay public so customers can still place orders.
    """
    endpoint = request.endpoint or ""
    if endpoint in PUBLIC_ENDPOINTS:
        return None
    if session.get("authed"):
        return None
    next_url = request.full_path if request.method == "GET" else url_for("dashboard")
    return redirect(url_for("login", next=next_url))


@app.after_request
def _ensure_device_cookie(resp: Response) -> Response:
    """
    Stamp every response with a stable device id cookie when missing. Acts as the
    foundation for per-device tracking (audit logs, public viewing, etc.).
    """
    if request.cookies.get(DEVICE_COOKIE_NAME):
        return resp
    device_id = secrets.token_urlsafe(16)
    resp.set_cookie(
        DEVICE_COOKIE_NAME,
        device_id,
        max_age=DEVICE_COOKIE_MAX_AGE,
        httponly=True,
        samesite="Lax",
    )
    return resp


@app.get("/login")
def login():
    if session.get("authed"):
        return redirect(url_for("dashboard"))
    return render_template("login.html", error=None)


@app.post("/login")
def login_submit():
    pw = (request.form.get("password") or "").strip()
    if pw and secrets.compare_digest(pw, STAFF_PASSWORD):
        session["authed"] = True
        session["device_id"] = request.cookies.get(DEVICE_COOKIE_NAME) or secrets.token_urlsafe(16)
        nxt = (request.args.get("next") or request.form.get("next") or "").strip()
        if nxt and nxt.startswith("/"):
            return redirect(nxt)
        return redirect(url_for("dashboard"))
    return render_template("login.html", error="Wrong password — try again."), 401


@app.post("/logout")
def logout():
    session.clear()
    flash("Signed out.", "success")
    return redirect(url_for("login"))


@app.get("/healthz")
def healthz():
    """
    Lightweight liveness probe for external keep-alive monitors (e.g. UptimeRobot).
    Does not open a database connection — wakes the web process only.
    """
    return Response(
        "ok\n",
        mimetype="text/plain",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/warm")
def warm():
    """
    DB-touching warm probe. Use in tandem with /healthz on a slower cadence
    (e.g. every 15 min) so the first real page load is not paying for a cold
    Postgres pool + schema migration on top of cold Python.
    """
    started = time.perf_counter()
    try:
        row = query("SELECT 1 AS ok", fetch=True, one=True)
        ok = bool(row and row.get("ok") == 1)
    except Exception as exc:  # noqa: BLE001
        elapsed = (time.perf_counter() - started) * 1000
        return Response(
            f"warm_error elapsed_ms={elapsed:.0f} err={exc}\n",
            mimetype="text/plain",
            status=503,
            headers={"Cache-Control": "no-store"},
        )
    elapsed = (time.perf_counter() - started) * 1000
    return Response(
        f"warm_ok={ok} elapsed_ms={elapsed:.0f}\n",
        mimetype="text/plain",
        headers={"Cache-Control": "no-store"},
    )


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
    if s == "-":
        return None
    for fmt in (
        "%d/%m/%Y",
        "%d/%m/%y",
        "%Y-%m-%d",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y",
    ):
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


def list_active_products():
    return query(
        """
        SELECT *
        FROM products
        WHERE is_active = TRUE
        ORDER BY display_order, product_name
        """,
        fetch=True,
    ) or []


def list_active_flavours():
    return query(
        """
        SELECT *
        FROM flavours
        WHERE is_active = TRUE
        ORDER BY display_order, name
        """,
        fetch=True,
    ) or []


def recalc_order_totals(order_id: int) -> None:
    agg = query(
        """
        SELECT
            COALESCE(SUM(quantity), 0)::int AS cups,
            SUM(
                CASE WHEN unit_price IS NOT NULL
                     THEN unit_price * quantity
                     ELSE 0
                END
            ) AS amount
        FROM order_items
        WHERE order_id = %s
        """,
        (order_id,),
        fetch=True,
        one=True,
    )
    cups = int(agg["cups"] or 0)
    amount = float(agg["amount"] or 0) if agg.get("amount") is not None else None
    query(
        "UPDATE orders SET cup_count = %s, total_amount = %s WHERE id = %s",
        (max(cups, 1), amount, order_id),
    )


# ---------------------------------------------------------------------------
# Import parsers
# ---------------------------------------------------------------------------
def import_inventory_csv(stream, replace: bool = False) -> tuple[int, int]:
    """Returns (items_upserted, legacy_prep_rows_ignored). Legacy prep CSV block is ignored (v0.2.6)."""
    text = io.TextIOWrapper(stream, encoding="utf-8", newline="")
    rows = list(csv.reader(text))
    items = []
    mode = "items"
    for row in rows:
        if not row or all(not (c or "").strip() for c in row):
            continue
        key = (row[0] or "").strip().lower()
        if key == "component":
            mode = "ignore_legacy_prep"
            continue
        if mode == "ignore_legacy_prep":
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

    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                if replace:
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
        return n_items, 0
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


_ITEM_RX = re.compile(r"^\s*(\d+)\s+(.+?)\s*$")


def _infer_payment_type(text: str) -> str | None:
    """Read the old 'Person In Charge' column and infer paynow vs. cash."""
    if not text:
        return None
    s = text.lower()
    if "paynow" in s or "paylah" in s or "ocbc" in s:
        return "paynow"
    if "cash" in s:
        return "cash"
    return None


def _split_inflow_line(description: str | None) -> tuple[str | None, list[tuple[int, str]]]:
    """Parse a financial-tracker description into (customer, [(qty, product), ...]).

    Handles patterns like::
      "Xanthe: 1 Matcha Strawberry Latte, 1 Matcha Original Latte"
      " Isabelle: 1 Matcha Strawberry Latte, 1 Matcha Honey Buttercream Latte"

    Seed-capital / non-order rows (no colon) return (None, []).
    """
    if not description:
        return None, []
    if ":" not in description:
        return None, []
    customer, _, tail = description.partition(":")
    customer = customer.strip() or None
    items: list[tuple[int, str]] = []
    # Comma splits items; strip parenthetical annotations on the product name.
    for raw in tail.split(","):
        piece = raw.strip()
        if not piece:
            continue
        m = _ITEM_RX.match(piece)
        if not m:
            continue
        qty = int(m.group(1))
        name = m.group(2).strip()
        # strip trailing parentheticals like "(less ice)" so the product key is clean
        name = re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()
        if qty > 0 and name:
            items.append((qty, name))
    return customer, items


def _name_key(value: str | None) -> str:
    """Case/spacing-insensitive key used for name normalization."""
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip().lower()


def _name_key_variants(value: str | None) -> list[str]:
    """
    Yield reasonable canonicalisation candidates for a free-typed product name.
    The financial CSV from the field uses inconsistent forms — pluralised
    ("strawberry matcha lattes"), reordered ("Honey Matcha Latte" vs.
    "Matcha Honey Buttercream Latte") — so we try a small set of normalised
    keys so the products table can match what was actually typed.
    """
    base = _name_key(value)
    if not base:
        return []
    out: list[str] = [base]
    # Trailing plural "s" — "lattes" → "latte", "milks" → "milk". Conservative:
    # only chop the trailing 's' on common drink nouns to avoid eating real
    # singulars (e.g. "iced chocolates" exists; "tiramisu" doesn't end in 's').
    plural_match = re.match(r"^(.*?)(latte|milk|tiramisu|chocolate|americano)s$", base)
    if plural_match:
        out.append(f"{plural_match.group(1)}{plural_match.group(2)}")
    # Drop redundant adjectives a customer might type. "iced chocolate" already
    # canonical; "cold matcha latte" should match "matcha latte".
    stripped = re.sub(r"\b(cold|hot|warm|less ice|extra ice)\b", "", base)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    if stripped and stripped != base:
        out.append(stripped)
    # Deduplicate while preserving order.
    seen: set[str] = set()
    uniq: list[str] = []
    for k in out:
        if k and k not in seen:
            seen.add(k)
            uniq.append(k)
    return uniq


def _resolve_canonical(name: str | None, mapping: dict[str, str]) -> str | None:
    """Return the canonical product name from `mapping` for a free-typed input."""
    for k in _name_key_variants(name):
        canonical = mapping.get(k)
        if canonical:
            return canonical
    return name


def _sql_finance_inflows_join_products() -> str:
    """
    Join finance inflow rows to `products`: prefer explicit product_id, else
    case/spacing-insensitive product_name match (same rule everywhere in v0.2.6).
    """
    return """
LEFT JOIN products p ON p.id = f.product_id
   OR (
        f.product_id IS NULL
        AND lower(regexp_replace(trim(COALESCE(f.product_name, '')), '\\s+', ' ', 'g'))
         = lower(regexp_replace(trim(COALESCE(p.product_name, '')), '\\s+', ' ', 'g'))
      )
"""


def import_financial_csv(stream, replace: bool = False) -> tuple[int, int]:
    """
    Parse the raw Google-Sheets financial tracker CSV.

    Inflow rows are exploded into **1NF**: one row per singular product bought.
    Amount is split evenly across the listed cups so totals still sum correctly.
    Outflows are kept as-is (one row per expense).
    """
    text = io.TextIOWrapper(stream, encoding="utf-8", newline="")
    rows = list(csv.reader(text))
    start = None
    for i, row in enumerate(rows):
        joined = ",".join((c or "") for c in row).lower()
        if "transaction item" in joined and "cash inflow" in joined:
            start = i + 1
            break
    if start is None:
        raise ValueError("Could not find financial tracker header row.")

    inflows: list[tuple] = []
    outflows: list[tuple] = []

    for row in rows[start:]:
        if not row or len(row) < 4:
            continue

        def g(idx, _row=row):
            return (_row[idx] if idx < len(_row) else "") or ""

        marker = f"{g(2)} {g(3)} {g(4)}".strip().lower()
        if (
            marker.startswith("- amount")
            or "total cups" in marker
            or "w1:" in marker
            or "w2:" in marker
            or "w3:" in marker
        ):
            continue

        txn_in = parse_int(g(2))
        amt_in = parse_money(g(3))
        desc_in = g(4).strip() or None
        cups = parse_int(g(5))
        d_in = parse_date(g(6))
        shot_in = g(7).strip() or None
        person_in = g(8).strip() or None

        txn_out = parse_int(g(9))
        amt_out = parse_money(g(10))
        desc_out = g(11).strip() or None
        d_out = parse_date(g(12))
        shot_out = g(13).strip() or None
        pic_out = g(14).strip() or None if len(row) > 14 else None

        if amt_in is not None:
            customer, items = _split_inflow_line(desc_in)
            pay_type = _infer_payment_type(person_in or "")
            if items:
                total_qty = sum(q for q, _ in items) or 1
                per_unit = float(amt_in) / total_qty if amt_in else 0.0
                for qty, product_name in items:
                    line_amt = round(per_unit * qty, 4)
                    inflows.append(
                        (
                            txn_in,
                            line_amt,
                            desc_in,
                            qty,
                            d_in,
                            shot_in,
                            person_in,
                            customer,
                            product_name,
                            pay_type,
                            "paid",
                        )
                    )
            else:
                # Non-order rows (e.g. seed capital) kept as one row, no customer/product.
                inflows.append(
                    (
                        txn_in,
                        amt_in,
                        desc_in,
                        cups,
                        d_in,
                        shot_in,
                        person_in,
                        customer,
                        None,
                        pay_type,
                        "paid",
                    )
                )

        if amt_out is not None:
            outflows.append((txn_out, amt_out, desc_out, d_out, shot_out, pic_out))

    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, product_name FROM products WHERE product_name IS NOT NULL"
                )
                prod_rows = cur.fetchall() or []
                canonical_products = {_name_key(r["product_name"]): r["product_name"] for r in prod_rows}
                product_id_by_key = {_name_key(r["product_name"]): r["id"] for r in prod_rows}
                if replace:
                    cur.execute("DELETE FROM finance_cash_outflows")
                    cur.execute("DELETE FROM finance_cash_inflows")
                for t in inflows:
                    txn_no, amount, desc, cups, txn_date, shot, pic, customer_name, product_name, pay_type, pay_status = t
                    product_name = _resolve_canonical(product_name, canonical_products)
                    pid = None
                    if product_name:
                        pid = product_id_by_key.get(_name_key(product_name))
                    cur.execute(
                        """
                        INSERT INTO finance_cash_inflows
                          (source_txn_number, amount, description, quantity_cups, txn_date,
                           screenshot, person_in_charge, customer_name, product_name, product_id,
                           payment_type, payment_status)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """,
                        (
                            txn_no,
                            amount,
                            desc,
                            cups,
                            txn_date,
                            shot,
                            pic,
                            customer_name,
                            product_name,
                            pid,
                            pay_type,
                            pay_status,
                        ),
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
        pm = (col(row, "payment_method") or "").strip() or None
        rows_out.append((cust, summary, cups, total, odate, notes, pm, ost, pst))

    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                if replace:
                    cur.execute("DELETE FROM order_items")
                    cur.execute("DELETE FROM orders")
                for t in rows_out:
                    cust, summary, cups, total, odate, notes, pm, ost, pst = t
                    cur.execute(
                        """
                        INSERT INTO orders
                          (customer_name, cup_count, total_amount, order_date, payment_notes, payment_method, order_status, payment_status)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                        RETURNING id
                        """,
                        (cust, cups, total, odate, notes, pm, ost, pst),
                    )
                    order_id = cur.fetchone()["id"]
                    pname = summary or "Imported item"
                    cur.execute(
                        """
                        INSERT INTO products (product_name, product_type, is_active)
                        VALUES (%s, 'special', TRUE)
                        ON CONFLICT (product_name) DO UPDATE SET product_name = EXCLUDED.product_name
                        RETURNING id
                        """,
                        (pname,),
                    )
                    product_id = cur.fetchone()["id"]
                    unit_price = (total / cups) if (total is not None and cups) else None
                    cur.execute(
                        """
                        INSERT INTO order_items (order_id, product_id, quantity, unit_price)
                        VALUES (%s,%s,%s,%s)
                        """,
                        (order_id, product_id, max(cups, 1), unit_price),
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
        "prep_total": 0,
        "prep_ready": 0,
    }
    prep_plan_rows = _compute_prep_plan_readiness()
    stats["prep_total"] = len(prep_plan_rows)
    stats["prep_ready"] = sum(1 for r in prep_plan_rows if r.get("state") == "ok")
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
    return render_template(
        "dashboard.html",
        stats=stats,
        recent_tasks=recent_tasks,
        prep_plan_rows=prep_plan_rows,
    )


def _compute_prep_plan_readiness() -> list[dict]:
    """
    Resolve each prep_plan row to its linked component (if any) and decide
    whether ingredient stock is sufficient to produce the requested qty_to_prep.

    The math: for each component_ingredient, required_amount = qty_per_component
    × qty_to_prep. If every linked inventory line carries enough stock, the row
    is "ok". If at least one line is short, the row is "short". Plans that
    aren't linked to a component yet sit in "unknown" so the operator knows
    they still need to wire up the recipe.
    """
    try:
        rows = query(
            """
            SELECT pp.id, pp.week_start, pp.component_id, pp.component_label,
                   pp.qty_to_prep, pp.notes, pp.sort_order,
                   c.name AS component_name, c.base_yield AS component_base_yield
            FROM prep_plan pp
            LEFT JOIN components c ON c.id = pp.component_id
            ORDER BY pp.sort_order, pp.id
            """,
            fetch=True,
        ) or []
    except psycopg2.Error as exc:
        if getattr(exc, "pgcode", None) == "42P01":
            return []  # table not yet created on this DB
        raise

    enriched: list[dict] = []
    for r in rows:
        out = dict(r)
        out["state"] = "unknown"
        out["shortfalls"] = []
        if r.get("component_id"):
            ings = query(
                """
                SELECT ci.qty_g, ci.label_override, ii.item_name, ii.qty_grams
                FROM component_ingredients ci
                LEFT JOIN inventory_items ii ON ii.id = ci.inventory_item_id
                WHERE ci.component_id = %s
                ORDER BY ci.sort_order, ci.id
                """,
                (r["component_id"],),
                fetch=True,
            ) or []
            base_yield = float(r.get("component_base_yield") or 1) or 1.0
            scale = float(r.get("qty_to_prep") or 0) / base_yield
            shortfalls: list[dict] = []
            any_known = False
            for ing in ings:
                qpy = ing.get("qty_g")
                stock = ing.get("qty_grams")
                if qpy is None or stock is None:
                    continue
                any_known = True
                needed = float(qpy) * scale
                if float(stock) + 1e-9 < needed:
                    shortfalls.append(
                        {
                            "name": ing.get("label_override") or ing.get("item_name") or "—",
                            "needed": needed,
                            "have": float(stock),
                        }
                    )
            if not ings or not any_known:
                out["state"] = "unknown"
            elif shortfalls:
                out["state"] = "short"
                out["shortfalls"] = shortfalls
            else:
                out["state"] = "ok"
        enriched.append(out)
    return enriched


@app.route("/prep-plan", methods=["GET", "POST"])
def prep_plan_page():
    """
    Manage the weekly prep plan keyed in by humans (item 9 / v0.2.5).
    For latte demand, operators add separate rows per cloud and per flavour so
    qty distribution stays commutative across products that share components.
    """
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            label = request.form.get("component_label", "").strip()
            component_id = request.form.get("component_id", type=int)
            try:
                qty = float(request.form.get("qty_to_prep") or 0)
            except ValueError:
                qty = 0.0
            if qty < 0:
                qty = 0.0
            week_start = parse_date(request.form.get("week_start")) or date.today()
            notes = request.form.get("notes", "").strip() or None
            if not label and component_id:
                # Default the label to the component name when blank.
                row = query(
                    "SELECT name FROM components WHERE id = %s",
                    (component_id,),
                    fetch=True,
                    one=True,
                )
                label = (row or {}).get("name") or "(unnamed)"
            if not label:
                flash("Pick a component or type a label.", "error")
                return redirect(url_for("prep_plan_page"))
            so = query(
                "SELECT COALESCE(MAX(sort_order), -1) + 1 AS n FROM prep_plan",
                fetch=True,
                one=True,
            )["n"]
            query(
                """
                INSERT INTO prep_plan
                  (week_start, component_id, component_label, qty_to_prep, notes, sort_order)
                VALUES (%s,%s,%s,%s,%s,%s)
                """,
                (week_start, component_id, label, qty, notes, so),
            )
            flash("Prep plan row added.", "success")
        elif action == "delete":
            pid = request.form.get("prep_plan_id", type=int)
            if pid:
                query("DELETE FROM prep_plan WHERE id = %s", (pid,))
                flash("Prep plan row removed.", "success")
        elif action == "update_qty":
            pid = request.form.get("prep_plan_id", type=int)
            try:
                qty = float(request.form.get("qty_to_prep") or 0)
            except ValueError:
                qty = 0.0
            if qty < 0:
                qty = 0.0
            if pid:
                query("UPDATE prep_plan SET qty_to_prep = %s WHERE id = %s", (qty, pid))
                flash("Qty updated.", "success")
        return redirect(url_for("prep_plan_page"))

    rows = _compute_prep_plan_readiness()
    components = list_components()
    return render_template(
        "prep_plan.html",
        rows=rows,
        components=components,
        today=date.today().isoformat(),
    )


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
        if status == "Completed":
            query("DELETE FROM tasks WHERE id = %s", (task_id,))
            flash("Task completed and removed.", "success")
        else:
            query("UPDATE tasks SET status = %s WHERE id = %s", (status, task_id))
            flash("Task status updated.", "success")
    else:
        flash("Invalid status.", "error")
    return redirect(request.referrer or url_for("tasks_list"))


@app.post("/tasks/<int:task_id>/advance-status")
def tasks_advance_status(task_id):
    row = query(
        "SELECT status FROM tasks WHERE id = %s",
        (task_id,),
        fetch=True,
        one=True,
    )
    if not row:
        abort(404)
    if row["status"] == "Completed":
        query("DELETE FROM tasks WHERE id = %s", (task_id,))
        flash("Completed task removed.", "success")
        return redirect(url_for("tasks_list"))
    nxt = _cycle_next(row["status"], TASK_STATUS_CYCLE)
    if nxt == "Completed":
        query("DELETE FROM tasks WHERE id = %s", (task_id,))
        flash("Task completed and removed.", "success")
    else:
        query("UPDATE tasks SET status = %s WHERE id = %s", (nxt, task_id))
    return redirect(url_for("tasks_list"))


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
    return render_template("inventory.html", items=items)


@app.route("/inventory/add", methods=["GET", "POST"])
def inventory_add():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        try:
            qty = float(request.form.get("qty_grams", "") or 0)
        except ValueError:
            flash("Quantity must be a number.", "error")
            return redirect(url_for("inventory_add"))
        source_cost = parse_money(request.form.get("source_cost"))
        source_qty_g = parse_money(request.form.get("source_qty_g"))
        supplier = request.form.get("supplier", "").strip() or None
        remark = request.form.get("remark", "").strip() or None
        updated = request.form.get("updated_flag") == "on"
        if not name:
            flash("Item name is required.", "error")
            return redirect(url_for("inventory_add"))
        query(
            """
            INSERT INTO inventory_items
              (item_name, qty_grams, source_cost, source_qty_g, supplier, remark, updated_flag)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (item_name) DO UPDATE SET
              qty_grams = EXCLUDED.qty_grams,
              source_cost = EXCLUDED.source_cost,
              source_qty_g = EXCLUDED.source_qty_g,
              supplier = EXCLUDED.supplier,
              remark = EXCLUDED.remark,
              updated_flag = EXCLUDED.updated_flag
            """,
            (name, qty, source_cost, source_qty_g, supplier, remark, updated),
        )
        flash("Inventory item saved.", "success")
        return redirect(url_for("inventory_list"))
    return render_template("inventory_add.html")


@app.route("/inventory/<int:item_id>/edit", methods=["GET", "POST"])
def inventory_edit(item_id):
    row = query(
        "SELECT * FROM inventory_items WHERE id = %s",
        (item_id,),
        fetch=True,
        one=True,
    )
    if not row:
        abort(404)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        try:
            qty = float(request.form.get("qty_grams", "") or 0)
        except ValueError:
            flash("Quantity must be a number.", "error")
            return redirect(url_for("inventory_edit", item_id=item_id))
        source_cost = parse_money(request.form.get("source_cost"))
        source_qty_g = parse_money(request.form.get("source_qty_g"))
        supplier = request.form.get("supplier", "").strip() or None
        remark = request.form.get("remark", "").strip() or None
        updated = request.form.get("updated_flag") == "on"
        if not name:
            flash("Item name is required.", "error")
            return redirect(url_for("inventory_edit", item_id=item_id))
        conflict = query(
            "SELECT id FROM inventory_items WHERE lower(item_name) = lower(%s) AND id <> %s",
            (name, item_id),
            fetch=True,
            one=True,
        )
        if conflict:
            flash("Another row already uses that item name.", "error")
            return redirect(url_for("inventory_edit", item_id=item_id))
        query(
            """
            UPDATE inventory_items SET
              item_name = %s,
              qty_grams = %s,
              source_cost = %s,
              source_qty_g = %s,
              supplier = %s,
              remark = %s,
              updated_flag = %s
            WHERE id = %s
            """,
            (name, qty, source_cost, source_qty_g, supplier, remark, updated, item_id),
        )
        flash("Inventory item updated.", "success")
        return redirect(url_for("inventory_list"))
    return render_template("inventory_edit.html", item=row)


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------
@app.route("/orders")
def orders_list():
    # Hide orders that are both Completed and Paid — they've already flowed to
    # finance (v0.2.3). Still queryable directly via the order's stored row.
    orders = query(
        """
        SELECT
            o.*,
            COALESCE(
                STRING_AGG(p.product_name || ' x' || oi.quantity, ', ' ORDER BY oi.id),
                '—'
            ) AS order_items_summary
        FROM orders o
        LEFT JOIN order_items oi ON oi.order_id = o.id
        LEFT JOIN products p ON p.id = oi.product_id
        WHERE NOT (o.order_status = 'Completed' AND o.payment_status = 'Paid')
        GROUP BY o.id
        ORDER BY COALESCE(o.order_date, o.created_at::date) DESC, o.id DESC
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
    products = list_active_products()
    if request.method == "POST":
        customer = request.form.get("customer_name", "").strip()
        product_id = request.form.get("product_id", type=int)
        try:
            cups = int(request.form.get("quantity", 1) or 1)
        except ValueError:
            cups = 1
        if cups < 1:
            cups = 1
        total = parse_money(request.form.get("unit_price"))
        line_remarks = request.form.get("line_remarks", "").strip() or None
        odate = parse_date(request.form.get("order_date")) or date.today()
        notes = request.form.get("payment_notes", "").strip() or None
        payment_method = (request.form.get("payment_method") or "").strip() or None
        order_status = request.form.get("order_status", "Pending")
        payment_status = request.form.get("payment_status", "Unpaid")
        if not customer:
            flash("Customer name is required.", "error")
        elif not product_id:
            flash("Select a product.", "error")
        elif order_status not in ORDER_STATUSES or payment_status not in PAYMENT_STATUSES:
            flash("Invalid status.", "error")
        else:
            row = query(
                """
                INSERT INTO orders
                  (customer_name, cup_count, total_amount, order_date, payment_notes, payment_method, order_status, payment_status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
                """,
                (customer, cups, total, odate, notes, payment_method, order_status, payment_status),
                fetch=True,
                one=True,
            )
            query(
                """
                INSERT INTO order_items (order_id, product_id, quantity, unit_price, remarks)
                VALUES (%s,%s,%s,%s,%s)
                """,
                (row["id"], product_id, cups, total, line_remarks),
            )
            recalc_order_totals(int(row["id"]))
            flash("Order added.", "success")
            return redirect(url_for("orders_list"))
    return render_template(
        "order_add.html",
        order_statuses=ORDER_STATUSES,
        payment_statuses=PAYMENT_STATUSES,
        products=products,
    )


def _cycle_next(current: str, cycle: list[str]) -> str:
    """Return the next value in the cycle, wrapping around."""
    if current not in cycle:
        return cycle[0]
    i = cycle.index(current)
    return cycle[(i + 1) % len(cycle)]


def _push_order_to_finance_if_done(order_id: int) -> None:
    """
    Once an order is both Completed and Paid, insert one 1NF row per order_item
    into `finance_cash_inflows`. `orders.finance_pushed_at` gates the insert so
    the buttons stay idempotent — toggling states repeatedly won't duplicate.
    """
    order = query(
        "SELECT * FROM orders WHERE id = %s",
        (order_id,),
        fetch=True,
        one=True,
    )
    if not order:
        return
    if order["order_status"] != "Completed" or order["payment_status"] != "Paid":
        return
    if order.get("finance_pushed_at") is not None:
        return
    items = query(
        """
        SELECT oi.quantity, oi.unit_price, oi.product_id, p.product_name
        FROM order_items oi
        JOIN products p ON p.id = oi.product_id
        WHERE oi.order_id = %s
        ORDER BY oi.id
        """,
        (order_id,),
        fetch=True,
    ) or []
    pay_type = (order.get("payment_method") or "").strip().lower()
    if pay_type not in ("paynow", "cash"):
        pay_type = None
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT product_name FROM products WHERE product_name IS NOT NULL")
                canonical_products = {
                    _name_key(r["product_name"]): r["product_name"] for r in (cur.fetchall() or [])
                }
                for it in items:
                    amt = (
                        float(it["unit_price"]) * int(it["quantity"])
                        if it.get("unit_price") is not None
                        else None
                    )
                    product_name = _resolve_canonical(it.get("product_name"), canonical_products)
                    cur.execute(
                        """
                        INSERT INTO finance_cash_inflows
                          (amount, description, quantity_cups, txn_date,
                           customer_name, product_name, product_id, payment_type, payment_status)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """,
                        (
                            amt,
                            f"Order #{order_id}",
                            int(it["quantity"]),
                            order.get("order_date") or date.today(),
                            order["customer_name"],
                            product_name,
                            it.get("product_id"),
                            pay_type,
                            "paid",
                        ),
                    )
                cur.execute(
                    "UPDATE orders SET finance_pushed_at = NOW() WHERE id = %s",
                    (order_id,),
                )
    finally:
        conn.close()


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
    _push_order_to_finance_if_done(order_id)
    flash("Order updated.", "success")
    return redirect(url_for("orders_list"))


@app.post("/orders/<int:order_id>/advance-status")
def orders_advance_status(order_id):
    """Morph the order_status button to the next state in the UX cycle."""
    row = query(
        "SELECT order_status FROM orders WHERE id = %s",
        (order_id,),
        fetch=True,
        one=True,
    )
    if not row:
        abort(404)
    nxt = _cycle_next(row["order_status"], ORDER_STATUS_CYCLE)
    query("UPDATE orders SET order_status = %s WHERE id = %s", (nxt, order_id))
    _push_order_to_finance_if_done(order_id)
    return redirect(url_for("orders_list"))


@app.post("/orders/<int:order_id>/advance-payment")
def orders_advance_payment(order_id):
    """Morph the payment_status button to the next state in the UX cycle."""
    row = query(
        "SELECT payment_status FROM orders WHERE id = %s",
        (order_id,),
        fetch=True,
        one=True,
    )
    if not row:
        abort(404)
    nxt = _cycle_next(row["payment_status"], PAYMENT_STATUS_CYCLE)
    query("UPDATE orders SET payment_status = %s WHERE id = %s", (nxt, order_id))
    _push_order_to_finance_if_done(order_id)
    return redirect(url_for("orders_list"))


@app.route("/products", methods=["GET", "POST"])
def products_page():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "save_flavour":
            fid = request.form.get("flavour_id", type=int)
            fname = request.form.get("flavour_name", "").strip()
            fcloud = request.form.get("cloud_type") or None
            factive = request.form.get("is_active") == "on"
            if not fname:
                flash("Flavour name is required.", "error")
                return redirect(url_for("products_page"))
            if fid:
                query(
                    "UPDATE flavours SET name = %s, cloud_type = %s, is_active = %s WHERE id = %s",
                    (fname, fcloud, factive, fid),
                )
                flash("Flavour updated.", "success")
            else:
                query(
                    "INSERT INTO flavours (name, cloud_type, is_active) VALUES (%s,%s,%s)",
                    (fname, fcloud, True),
                )
                flash("Flavour added.", "success")
            return redirect(url_for("products_page"))

        pid = request.form.get("product_id", type=int)
        rid = request.form.get("recipe_id", type=int)
        name = request.form.get("product_name", "").strip()
        ptype = request.form.get("product_type", "special")
        cloud_type = request.form.get("cloud_type") or None
        flavour_id = request.form.get("flavour_id", type=int)
        flavour_row = (
            query("SELECT * FROM flavours WHERE id = %s", (flavour_id,), fetch=True, one=True)
            if flavour_id
            else None
        )
        flavour = flavour_row["name"] if flavour_row else None
        if ptype == "latte" and cloud_type not in CLOUD_TYPES:
            flash("Latte products need a cloud type.", "error")
            return redirect(url_for("products_page"))
        if ptype != "latte":
            cloud_type = None
        is_active = request.form.get("is_active") == "on"
        selling_price = parse_money(request.form.get("selling_price"))
        short_desc = request.form.get("short_desc", "").strip() or None
        image_url = request.form.get("image_url", "").strip() or None
        notes = request.form.get("notes", "").strip() or None
        try:
            by = float(request.form.get("base_yield_cups") or 1)
        except ValueError:
            by = 1.0
        if by <= 0:
            by = 1.0
        if ptype not in PRODUCT_TYPES:
            flash("Invalid product type.", "error")
            return redirect(url_for("products_page"))
        if not name:
            flash("Product name is required.", "error")
            return redirect(url_for("products_page"))
        if pid:
            query(
                """
                UPDATE products
                SET product_name = %s, product_type = %s, cloud_type = %s,
                    flavour_name = %s, selling_price = %s, short_desc = %s, image_url = %s, is_active = %s
                WHERE id = %s
                """,
                (name, ptype, cloud_type, flavour, selling_price, short_desc, image_url, is_active, pid),
            )
            if rid:
                query(
                    """
                    UPDATE recipes
                    SET name = %s, drink_category = %s, is_latte = %s, cloud_type = %s,
                        flavour_name = %s, notes = %s, base_yield_cups = %s
                    WHERE id = %s
                    """,
                    (
                        name,
                        ptype,
                        ptype == "latte",
                        cloud_type,
                        flavour or "",
                        notes,
                        by,
                        rid,
                    ),
                )
            flash("Product/recipe updated.", "success")
        else:
            prow = query(
                """
                INSERT INTO products
                  (product_name, product_type, cloud_type, flavour_name, selling_price, short_desc, image_url, is_active)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
                """,
                (name, ptype, cloud_type, flavour, selling_price, short_desc, image_url, True),
                fetch=True,
                one=True,
            )
            query(
                """
                INSERT INTO recipes
                  (product_id, name, drink_category, is_latte, cloud_type, flavour_name, notes, base_yield_cups)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    prow["id"],
                    name,
                    ptype,
                    ptype == "latte",
                    cloud_type,
                    flavour or "",
                    notes,
                    by,
                ),
            )
            flash("Product + recipe created.", "success")
        return redirect(url_for("products_page"))

    products = query(
        """
        SELECT
            p.*,
            r.id AS recipe_id,
            r.notes,
            r.base_yield_cups,
            COALESCE(SUM((ri.qty_per_yield / NULLIF(r.base_yield_cups, 0)) * (ii.source_cost / NULLIF(ii.source_qty_g, 0))), 0) AS ingredient_cost_per_cup
        FROM products p
        LEFT JOIN recipes r ON r.product_id = p.id
        LEFT JOIN recipe_ingredients ri ON ri.recipe_id = r.id
        LEFT JOIN inventory_items ii ON ii.id = ri.inventory_item_id
        GROUP BY p.id, r.id
        ORDER BY p.display_order, p.product_name
        """,
        fetch=True,
    )
    flavours = query("SELECT * FROM flavours ORDER BY display_order, name", fetch=True)
    return render_template(
        "products.html",
        products=products or [],
        product_types=PRODUCT_TYPES,
        flavours=flavours or [],
        components=list_components(),
    )


# ---------------------------------------------------------------------------
# Finance
# ---------------------------------------------------------------------------
@app.route("/finance")
def finance_summary():
    margin_menu = query(
        """
        SELECT m.*,
               COALESCE(p.product_name, m.item_name) AS product_label
        FROM margin_menu_items m
        LEFT JOIN products p
          ON lower(regexp_replace(trim(COALESCE(m.item_name, '')), '\\s+', ' ', 'g'))
           = lower(regexp_replace(trim(COALESCE(p.product_name, '')), '\\s+', ' ', 'g'))
        ORDER BY m.category NULLS LAST, COALESCE(p.product_name, m.item_name)
        """,
        fetch=True,
    )
    margin_ing = query(
        "SELECT * FROM margin_ingredients ORDER BY category NULLS LAST, ingredient",
        fetch=True,
    )
    inflows = query(
        f"""
        SELECT
            f.*,
            COALESCE(p.product_name, f.product_name) AS product_name_canonical
        FROM finance_cash_inflows f
        {_sql_finance_inflows_join_products()}
        ORDER BY f.txn_date NULLS LAST, f.id
        """,
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
    product_margins = query(
        """
        SELECT
            p.id,
            p.product_name,
            p.selling_price,
            r.base_yield_cups,
            COALESCE(SUM((ri.qty_per_yield / NULLIF(r.base_yield_cups, 0)) * (ii.source_cost / NULLIF(ii.source_qty_g, 0))), 0) AS ingredient_cost_per_cup
        FROM products p
        LEFT JOIN recipes r ON r.product_id = p.id
        LEFT JOIN recipe_ingredients ri ON ri.recipe_id = r.id
        LEFT JOIN inventory_items ii ON ii.id = ri.inventory_item_id
        GROUP BY p.id, r.id
        ORDER BY p.product_name
        """,
        fetch=True,
    )
    return render_template(
        "finance.html",
        margin_menu=margin_menu or [],
        margin_ing=margin_ing or [],
        inflows=inflows or [],
        outflows=outflows or [],
        total_revenue=float(rev or 0),
        total_expenses=float(exp or 0),
        net=float((rev or 0) - (exp or 0)),
        product_margins=product_margins or [],
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
    return redirect(url_for("products_page"))


def _recipe_scale_factor(recipe: dict, desired: float | None) -> float:
    base = float(recipe.get("base_yield_cups") or 1)
    if base <= 0:
        base = 1.0
    d = float(desired) if desired is not None else base
    if d <= 0:
        d = base
    return d / base


def _fetch_recipe_ingredients(recipe_id: int) -> list[dict]:
    """
    Return enriched recipe ingredient rows. Falls back gracefully when the
    legacy schema does not yet have prep_note / prep_done columns.
    """
    sql_full = """
        SELECT ri.*,
               ii.item_name AS inventory_item_name,
               ii.qty_grams AS stock_qty_g,
               c.name AS component_name,
               c.component_type AS component_type
        FROM recipe_ingredients ri
        LEFT JOIN inventory_items ii ON ii.id = ri.inventory_item_id
        LEFT JOIN components c ON c.id = ri.component_id
        WHERE ri.recipe_id = %s
        ORDER BY ri.sort_order, ri.id
    """
    try:
        return query(sql_full, (recipe_id,), fetch=True) or []
    except psycopg2.Error as exc:
        if getattr(exc, "pgcode", None) != "42703":
            raise
    sql_no_component = """
        SELECT ri.*,
               ii.item_name AS inventory_item_name,
               ii.qty_grams AS stock_qty_g
        FROM recipe_ingredients ri
        LEFT JOIN inventory_items ii ON ii.id = ri.inventory_item_id
        WHERE ri.recipe_id = %s
        ORDER BY ri.sort_order, ri.id
    """
    rows = query(sql_no_component, (recipe_id,), fetch=True) or []
    for r in rows:
        r.setdefault("component_id", None)
        r.setdefault("component_name", None)
        r.setdefault("component_type", None)
        r.setdefault("prep_note", None)
        r.setdefault("prep_done", False)
    return rows


def _insert_recipe_ingredient(
    *,
    recipe_id: int,
    sort_order: int,
    inventory_item_id: int | None,
    component_id: int | None,
    label_override: str | None,
    qty: float | None,
    unit: str,
    prep_note: str | None,
) -> None:
    """
    Insert a recipe ingredient line. Tries the full v0.2.5 schema first
    (component_id + prep_note + prep_done) and progressively falls back to older
    column sets so legacy Supabase deploys still work without crashing with a
    500. The schema migration runs on first request, so this is mostly belt-and-
    braces, but it neutralises the historical recipe-ingredient 500.
    """
    # region agent log
    _agent_debug_log(
        "app.py:_insert_recipe_ingredient:entry",
        "insert args",
        hypothesis_id="H2-args",
        data={
            "recipe_id": recipe_id,
            "sort_order": sort_order,
            "inventory_item_id": inventory_item_id,
            "component_id": component_id,
            "qty": qty,
            "unit": unit,
            "has_prep_note": bool(prep_note),
        },
    )
    # endregion
    # Some deployments treated qty_per_yield as NOT NULL; 0 is a safe placeholder.
    qty_db = float(qty) if qty is not None else 0.0
    base_cols = ["recipe_id", "sort_order", "label_override", "qty_per_yield", "unit"]
    base_vals: list = [recipe_id, sort_order, label_override, qty_db, unit]
    if inventory_item_id is not None:
        base_cols.append("inventory_item_id")
        base_vals.append(inventory_item_id)
    if component_id is not None:
        base_cols.append("component_id")
        base_vals.append(component_id)
    if prep_note:
        base_cols.append("prep_note")
        base_vals.append(prep_note)
    base_cols.append("prep_done")
    base_vals.append(False)

    def _exec(cols: list[str], vals: list) -> bool:
        placeholders = ",".join(["%s"] * len(cols))
        sql = f"INSERT INTO recipe_ingredients ({', '.join(cols)}) VALUES ({placeholders})"
        try:
            query(sql, tuple(vals))
            return True
        except psycopg2.Error as exc:
            # region agent log
            _agent_debug_log(
                "app.py:_insert_recipe_ingredient:_exec",
                "INSERT attempt failed",
                hypothesis_id="H3-pg-error",
                data={
                    "pgcode": getattr(exc, "pgcode", None),
                    "diag": getattr(exc, "diag", None)
                    and getattr(exc.diag, "message_primary", None),
                    "cols": cols,
                },
            )
            # endregion
            if getattr(exc, "pgcode", None) != "42703":
                raise
            return False

    # Full attempt — v0.2.5 schema, then strip prep_done / prep_note for older DBs.
    work_cols, work_vals = list(base_cols), list(base_vals)
    if _exec(work_cols, work_vals):
        return
    if "prep_done" in work_cols:
        i = work_cols.index("prep_done")
        work_cols = work_cols[:i] + work_cols[i + 1 :]
        work_vals = work_vals[:i] + work_vals[i + 1 :]
        if _exec(work_cols, work_vals):
            return
    # Drop prep_note (older schema) and retry.
    if "prep_note" in work_cols:
        idx = work_cols.index("prep_note")
        cols2 = work_cols[:idx] + work_cols[idx + 1 :]
        vals2 = work_vals[:idx] + work_vals[idx + 1 :]
        if _exec(cols2, vals2):
            return
    else:
        cols2, vals2 = work_cols, work_vals
    # Drop component_id (very old schema). For component-only lines this means
    # the line cannot be saved without a fresh migration, so surface that.
    if component_id is not None and inventory_item_id is None:
        # region agent log
        _agent_debug_log(
            "app.py:_insert_recipe_ingredient:schema",
            "raising: component-only but no component_id column path",
            hypothesis_id="H4-runtime-schema",
            data={"component_id": component_id},
        )
        # endregion
        raise RuntimeError(
            "recipe_ingredients.component_id is missing on this database. "
            "Please re-run schema migration to support component ingredient lines."
        )
    if "component_id" in cols2:
        idx = cols2.index("component_id")
        cols3 = cols2[:idx] + cols2[idx + 1 :]
        vals3 = vals2[:idx] + vals2[idx + 1 :]
        ok3 = _exec(cols3, vals3)
        # region agent log
        _agent_debug_log(
            "app.py:_insert_recipe_ingredient:drop_component",
            "final _exec after dropping component_id",
            hypothesis_id="H5-fallback",
            data={"ok": ok3, "cols3": cols3},
        )
        # endregion
        if ok3:
            return
    # region agent log
    _agent_debug_log(
        "app.py:_insert_recipe_ingredient:final",
        "raising schema mismatch",
        hypothesis_id="H4-runtime-schema",
        data={"cols2": cols2},
    )
    # endregion
    raise RuntimeError("Could not insert recipe ingredient line — schema mismatch.")


@app.route("/recipes/<int:recipe_id>", methods=["GET", "POST"])
def recipe_detail(recipe_id):
    recipe = query("SELECT * FROM recipes WHERE id = %s", (recipe_id,), fetch=True, one=True)
    if not recipe:
        abort(404)
    dc_raw = (request.values.get("desired_cups") or "").strip()
    back_q = {"desired_cups": dc_raw} if dc_raw else {}

    if request.method == "POST":
        action = request.form.get("action")
        if action == "add_ingredient":
            # Source of the line: inventory item OR reusable component (v0.2.3).
            source = (request.form.get("source") or "inventory").strip()
            inventory_item_id = request.form.get("inventory_item_id", type=int)
            component_id = request.form.get("component_id", type=int)
            if source == "component":
                inventory_item_id = None
            else:
                component_id = None
            # region agent log
            _agent_debug_log(
                "app.py:recipe_detail:add_ingredient",
                "parsed form",
                hypothesis_id="H1-form",
                data={
                    "recipe_id": recipe_id,
                    "source": source,
                    "inventory_item_id": inventory_item_id,
                    "component_id": component_id,
                },
            )
            # endregion
            label_override = request.form.get("label_override", "").strip() or None
            prep_note = request.form.get("prep_note", "").strip() or None
            if inventory_item_id or component_id:
                qraw = (request.form.get("qty_per_yield") or "").strip()
                try:
                    qty = float(qraw) if qraw else None
                except ValueError:
                    qty = None
                unit = (request.form.get("unit") or "g").strip() or "g"
                so = request.form.get("sort_order", type=int)
                if so is None:
                    r = query(
                        "SELECT COALESCE(MAX(sort_order), -1) + 1 AS n FROM recipe_ingredients WHERE recipe_id = %s",
                        (recipe_id,),
                        fetch=True,
                        one=True,
                    )
                    so = r["n"]
                try:
                    _insert_recipe_ingredient(
                        recipe_id=recipe_id,
                        sort_order=so,
                        inventory_item_id=inventory_item_id,
                        component_id=component_id,
                        label_override=label_override,
                        qty=qty,
                        unit=unit,
                        prep_note=prep_note,
                    )
                    flash("Ingredient line added.", "success")
                except RuntimeError as exc:
                    # region agent log
                    _agent_debug_log(
                        "app.py:recipe_detail:add_ingredient",
                        "RuntimeError from insert",
                        hypothesis_id="H4-runtime-schema",
                        data={"msg": str(exc)},
                        run_id="post-fix",
                    )
                    # endregion
                    flash(str(exc), "error")
                    return redirect(
                        url_for("recipe_detail", recipe_id=recipe_id, **back_q)
                    )
                except psycopg2.Error as exc:
                    code = getattr(exc, "pgcode", None)
                    # region agent log
                    _agent_debug_log(
                        "app.py:recipe_detail:add_ingredient",
                        "psycopg2 from insert",
                        hypothesis_id="H3-pg-error",
                        data={"pgcode": code, "msg": str(exc)},
                        run_id="post-fix",
                    )
                    # endregion
                    if code in ("23502", "23503", "23505", "23514"):
                        flash(
                            "Could not save that ingredient line (the database rejected it). "
                            "Refresh the page, pick the item again from the list, and check the quantity.",
                            "error",
                        )
                        return redirect(
                            url_for("recipe_detail", recipe_id=recipe_id, **back_q)
                        )
                    raise
            else:
                flash("Pick an inventory item or component before adding the line.", "error")
        elif action == "set_yield":
            try:
                by = float(request.form.get("base_yield_cups") or 1)
            except ValueError:
                by = 1.0
            if by <= 0:
                by = 1.0
            query("UPDATE recipes SET base_yield_cups = %s WHERE id = %s", (by, recipe_id))
            flash("Base yield updated.", "success")
        elif action == "add_assembly_step":
            sname = request.form.get("step_name", "").strip()
            sremarks = request.form.get("step_remarks", "").strip() or None
            if sname:
                so = query(
                    "SELECT COALESCE(MAX(sort_order), -1) + 1 AS n FROM recipe_assembly_steps WHERE recipe_id = %s",
                    (recipe_id,),
                    fetch=True,
                    one=True,
                )["n"]
                query(
                    "INSERT INTO recipe_assembly_steps (recipe_id, step_name, remarks, sort_order) VALUES (%s,%s,%s,%s)",
                    (recipe_id, sname, sremarks, so),
                )
                flash("Assembly step added.", "success")
        return redirect(url_for("recipe_detail", recipe_id=recipe_id, **back_q))

    desired = request.values.get("desired_cups", type=float)
    factor = _recipe_scale_factor(recipe, desired)

    ingredients = _fetch_recipe_ingredients(recipe_id)
    inventory_items = query(
        "SELECT id, item_name FROM inventory_items ORDER BY item_name",
        fetch=True,
    )
    components_lookup = list_components()
    legacy_steps = query(
        "SELECT id, body, completed FROM recipe_steps WHERE recipe_id = %s ORDER BY step_order, id",
        (recipe_id,),
        fetch=True,
    ) or []
    assembly_steps = query(
        "SELECT * FROM recipe_assembly_steps WHERE recipe_id = %s ORDER BY sort_order, id",
        (recipe_id,),
        fetch=True,
    ) or []
    enriched = []
    for ing in ingredients or []:
        row = dict(ing)
        qpy = ing.get("qty_per_yield")
        row["scaled_qty"] = (float(qpy) * factor) if qpy is not None else None
        row["display_name"] = (
            ing.get("label_override")
            or ing.get("component_name")
            or ing.get("inventory_item_name")
            or "—"
        )
        row["source_kind"] = (
            "component" if ing.get("component_id") else ("inventory" if ing.get("inventory_item_id") else "free")
        )
        row["stock_ok"] = bool(
            ing.get("stock_qty_g") is not None
            and row["scaled_qty"] is not None
            and float(ing["stock_qty_g"]) >= float(row["scaled_qty"])
        )
        enriched.append(row)

    # v0.2.5 — checklist is driven exclusively by ingredient lines whose
    # prep_note is non-empty. If a line has no prep instruction, there is
    # nothing to do for that ingredient. Empty prep_note → silently skipped.
    ingredient_prep_rows = [
        {
            "id": ing["id"],
            "label": ing["display_name"],
            "prep_note": ing.get("prep_note") or "",
            "done": bool(ing.get("prep_done")),
        }
        for ing in enriched
        if (ing.get("prep_note") or "").strip()
    ]
    merged_steps = (
        [{"id": s["id"], "step_name": s["step_name"], "remarks": s.get("remarks"), "done": s["done"], "kind": "assembly"} for s in assembly_steps]
        + [{"id": s["id"], "step_name": s["body"], "remarks": None, "done": s["completed"], "kind": "legacy"} for s in legacy_steps]
    )

    return render_template(
        "recipe_detail.html",
        recipe=recipe,
        ingredients=enriched,
        factor=factor,
        desired_output=float(desired) if desired is not None else float(recipe.get("base_yield_cups") or 1),
        preserve_desired_cups=dc_raw,
        inventory_items=inventory_items or [],
        components_lookup=components_lookup,
        ingredient_prep_rows=ingredient_prep_rows,
        merged_steps=merged_steps,
    )


@app.post("/recipes/<int:recipe_id>/steps/<int:step_id>/toggle")
def recipe_step_toggle(recipe_id, step_id):
    query(
        "UPDATE recipe_steps SET completed = NOT completed WHERE id = %s AND recipe_id = %s",
        (step_id, recipe_id),
    )
    flash("Step updated.", "success")
    q = {}
    if request.form.get("desired_cups"):
        q["desired_cups"] = request.form.get("desired_cups")
    return redirect(url_for("recipe_detail", recipe_id=recipe_id, **q))


@app.post("/recipes/<int:recipe_id>/prep/<int:prep_id>/toggle")
def recipe_prep_toggle(recipe_id, prep_id):
    query(
        """
        UPDATE recipe_component_prep
        SET done = NOT done
        WHERE id = %s
          AND component_id IN (SELECT id FROM recipe_components WHERE recipe_id = %s)
        """,
        (prep_id, recipe_id),
    )
    return redirect(url_for("recipe_detail", recipe_id=recipe_id))


@app.post("/recipes/<int:recipe_id>/component-step/<int:step_id>/toggle")
def recipe_component_step_toggle(recipe_id, step_id):
    query(
        """
        UPDATE recipe_component_steps
        SET done = NOT done
        WHERE id = %s
          AND component_id IN (SELECT id FROM recipe_components WHERE recipe_id = %s)
        """,
        (step_id, recipe_id),
    )
    return redirect(url_for("recipe_detail", recipe_id=recipe_id))


@app.post("/recipes/<int:recipe_id>/assembly/<int:step_id>/toggle")
def recipe_assembly_step_toggle(recipe_id, step_id):
    query(
        "UPDATE recipe_assembly_steps SET done = NOT done WHERE id = %s AND recipe_id = %s",
        (step_id, recipe_id),
    )
    return redirect(url_for("recipe_detail", recipe_id=recipe_id))


@app.post("/recipes/<int:recipe_id>/ingredient/<int:ingredient_id>/toggle-prep")
def recipe_ingredient_toggle_prep(recipe_id, ingredient_id):
    """
    Tick / untick the per-line ingredient prep checkbox. Lines with no prep_note
    don't appear in the checklist UI, so this is only ever triggered for rows
    that have an instruction.
    """
    try:
        query(
            """
            UPDATE recipe_ingredients
            SET prep_done = NOT COALESCE(prep_done, FALSE)
            WHERE id = %s AND recipe_id = %s
            """,
            (ingredient_id, recipe_id),
        )
    except psycopg2.Error as exc:
        if getattr(exc, "pgcode", None) == "42703":
            flash(
                "Ingredient prep checklist requires the v0.2.5 schema migration. "
                "Re-run the schema bootstrap to add prep_note + prep_done columns.",
                "error",
            )
        else:
            raise
    return redirect(url_for("recipe_detail", recipe_id=recipe_id))


@app.post("/recipes/<int:recipe_id>/ingredient/<int:ingredient_id>/prep-note")
def recipe_ingredient_set_prep_note(recipe_id, ingredient_id):
    """
    Inline edit of an existing ingredient line's prep instruction. Submitting an
    empty string clears the note (so the row leaves the checklist).
    """
    note = (request.form.get("prep_note") or "").strip() or None
    try:
        query(
            "UPDATE recipe_ingredients SET prep_note = %s WHERE id = %s AND recipe_id = %s",
            (note, ingredient_id, recipe_id),
        )
        flash("Prep note saved.", "success")
    except psycopg2.Error as exc:
        if getattr(exc, "pgcode", None) == "42703":
            flash(
                "Prep notes need the v0.2.5 schema migration to be applied first.",
                "error",
            )
        else:
            raise
    return redirect(url_for("recipe_detail", recipe_id=recipe_id))


@app.post("/recipes/<int:recipe_id>/ingredient/<int:ingredient_id>/delete")
def recipe_ingredient_delete(recipe_id, ingredient_id):
    query(
        "DELETE FROM recipe_ingredients WHERE id = %s AND recipe_id = %s",
        (ingredient_id, recipe_id),
    )
    flash("Ingredient line removed.", "success")
    return redirect(url_for("recipe_detail", recipe_id=recipe_id))


# ---------------------------------------------------------------------------
# Standalone reusable components (v0.2.3)
# ---------------------------------------------------------------------------
def list_components():
    return query(
        "SELECT * FROM components ORDER BY component_type NULLS LAST, name",
        fetch=True,
    ) or []


@app.route("/components", methods=["GET", "POST"])
def components_page():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        component_type = (
            request.form.get("component_type_new", "").strip()
            or request.form.get("component_type", "").strip()
            or None
        )
        notes = request.form.get("notes", "").strip() or None
        try:
            base_yield = float(request.form.get("base_yield") or 1)
        except ValueError:
            base_yield = 1.0
        if base_yield <= 0:
            base_yield = 1.0
        if not name:
            flash("Component name is required.", "error")
            return redirect(url_for("components_page"))
        query(
            """
            INSERT INTO components (name, component_type, notes, base_yield)
            VALUES (%s,%s,%s,%s)
            ON CONFLICT (name) DO UPDATE
            SET component_type = EXCLUDED.component_type,
                notes = EXCLUDED.notes,
                base_yield = EXCLUDED.base_yield
            """,
            (name, component_type, notes, base_yield),
        )
        flash("Component saved.", "success")
        return redirect(url_for("components_page"))

    rows = query(
        """
        SELECT c.*,
               (SELECT COUNT(*)::int FROM component_ingredients ci WHERE ci.component_id = c.id) AS ingredient_count,
               (SELECT COUNT(*)::int FROM component_steps cs WHERE cs.component_id = c.id) AS step_count
        FROM components c
        ORDER BY c.component_type NULLS LAST, c.name
        """,
        fetch=True,
    ) or []
    component_types = query(
        "SELECT DISTINCT component_type FROM components WHERE component_type IS NOT NULL ORDER BY 1",
        fetch=True,
    ) or []
    return render_template(
        "components.html",
        components=rows,
        component_types=[r["component_type"] for r in component_types],
    )


@app.route("/components/<int:component_id>", methods=["GET", "POST"])
def component_detail(component_id):
    comp = query("SELECT * FROM components WHERE id = %s", (component_id,), fetch=True, one=True)
    if not comp:
        abort(404)
    if request.method == "POST":
        action = request.form.get("action")
        if action == "save_meta":
            name = request.form.get("name", "").strip()
            ctype = (
                request.form.get("component_type_new", "").strip()
                or request.form.get("component_type", "").strip()
                or None
            )
            notes = request.form.get("notes", "").strip() or None
            try:
                by = float(request.form.get("base_yield") or 1)
            except ValueError:
                by = 1.0
            if not name:
                flash("Component name is required.", "error")
                return redirect(url_for("component_detail", component_id=component_id))
            query(
                """
                UPDATE components SET name = %s, component_type = %s, notes = %s, base_yield = %s
                WHERE id = %s
                """,
                (name, ctype, notes, by, component_id),
            )
            flash("Component details saved.", "success")
        elif action == "add_ingredient":
            inventory_item_id = request.form.get("inventory_item_id", type=int)
            label_override = request.form.get("label_override", "").strip() or None
            qraw = (request.form.get("qty_g") or "").strip()
            try:
                qty = float(qraw) if qraw else None
            except ValueError:
                qty = None
            if inventory_item_id:
                so = query(
                    "SELECT COALESCE(MAX(sort_order), -1) + 1 AS n FROM component_ingredients WHERE component_id = %s",
                    (component_id,),
                    fetch=True,
                    one=True,
                )["n"]
                query(
                    """
                    INSERT INTO component_ingredients
                      (component_id, inventory_item_id, label_override, qty_g, sort_order)
                    VALUES (%s,%s,%s,%s,%s)
                    """,
                    (component_id, inventory_item_id, label_override, qty, so),
                )
                flash("Ingredient added to component.", "success")
        elif action == "delete_ingredient":
            cid = request.form.get("ingredient_id", type=int)
            if cid:
                query(
                    "DELETE FROM component_ingredients WHERE id = %s AND component_id = %s",
                    (cid, component_id),
                )
                flash("Ingredient removed.", "success")
        elif action == "add_step":
            body = request.form.get("body", "").strip()
            if body:
                so = query(
                    "SELECT COALESCE(MAX(sort_order), -1) + 1 AS n FROM component_steps WHERE component_id = %s",
                    (component_id,),
                    fetch=True,
                    one=True,
                )["n"]
                query(
                    "INSERT INTO component_steps (component_id, body, sort_order) VALUES (%s,%s,%s)",
                    (component_id, body, so),
                )
                flash("Step added.", "success")
        elif action == "delete_step":
            sid = request.form.get("step_id", type=int)
            if sid:
                query(
                    "DELETE FROM component_steps WHERE id = %s AND component_id = %s",
                    (sid, component_id),
                )
                flash("Step removed.", "success")
        return redirect(url_for("component_detail", component_id=component_id))

    ingredients = query(
        """
        SELECT ci.*, ii.item_name AS inventory_item_name
        FROM component_ingredients ci
        LEFT JOIN inventory_items ii ON ii.id = ci.inventory_item_id
        WHERE ci.component_id = %s
        ORDER BY ci.sort_order, ci.id
        """,
        (component_id,),
        fetch=True,
    ) or []
    steps = query(
        "SELECT * FROM component_steps WHERE component_id = %s ORDER BY sort_order, id",
        (component_id,),
        fetch=True,
    ) or []
    inventory_items = query(
        "SELECT id, item_name FROM inventory_items ORDER BY item_name",
        fetch=True,
    ) or []
    component_types = query(
        "SELECT DISTINCT component_type FROM components WHERE component_type IS NOT NULL ORDER BY 1",
        fetch=True,
    ) or []
    return render_template(
        "component_detail.html",
        component=comp,
        ingredients=ingredients,
        steps=steps,
        inventory_items=inventory_items,
        component_types=[r["component_type"] for r in component_types],
    )


@app.post("/components/<int:component_id>/step/<int:step_id>/toggle")
def component_step_toggle(component_id, step_id):
    query(
        "UPDATE component_steps SET done = NOT done WHERE id = %s AND component_id = %s",
        (step_id, component_id),
    )
    return redirect(url_for("component_detail", component_id=component_id))


@app.post("/components/<int:component_id>/delete")
def component_delete(component_id):
    query("DELETE FROM components WHERE id = %s", (component_id,))
    flash("Component deleted.", "success")
    return redirect(url_for("components_page"))


@app.get("/shop")
def shop_order_form():
    return render_template(
        "shop.html",
        payment_methods=CUSTOMER_PAYMENT_METHODS,
        products=list_active_products(),
    )


@app.post("/shop")
def shop_order_submit():
    customer = request.form.get("customer_name", "").strip()
    product_ids = request.form.getlist("product_id")
    quantities = request.form.getlist("quantity")
    line_remarks = request.form.getlist("line_remarks")
    pm = request.form.get("payment_method") or ""
    valid = {x[0] for x in CUSTOMER_PAYMENT_METHODS}
    if not customer:
        flash("Please enter your name.", "error")
        return redirect(url_for("shop_order_form"))
    lines: list[tuple[int, int, str | None]] = []
    for i, raw_pid in enumerate(product_ids):
        pid = parse_int(raw_pid)
        qty = parse_int(quantities[i] if i < len(quantities) else "1") or 0
        remark = (line_remarks[i] if i < len(line_remarks) else "") or ""
        remark = remark.strip() or None
        if pid and qty > 0:
            lines.append((pid, qty, remark))
    if not lines:
        flash("Please add at least one product line.", "error")
        return redirect(url_for("shop_order_form"))
    if pm not in valid:
        flash("Choose a payment option.", "error")
        return redirect(url_for("shop_order_form"))
    notes = (
        "PayNow — order processed after payment is verified."
        if pm == "paynow"
        else "Pay on collection (cash / in person)."
    )
    products = {
        r["id"]: r
        for r in query(
            "SELECT id, product_name, selling_price FROM products WHERE id = ANY(%s)",
            ([pid for pid, _, _ in lines],),
            fetch=True,
        )
    }
    total_amount = 0.0
    total_cups = 0
    line_data: list[tuple[int, int, float | None, str | None]] = []
    for pid, qty, remark in lines:
        p = products.get(pid)
        if not p:
            continue
        unit_price = float(p["selling_price"]) if p.get("selling_price") is not None else None
        total_cups += qty
        if unit_price is not None:
            total_amount += unit_price * qty
        line_data.append((pid, qty, unit_price, remark))
    if not line_data:
        flash("No valid products selected.", "error")
        return redirect(url_for("shop_order_form"))
    row = query(
        """
        INSERT INTO orders
          (customer_name, cup_count, total_amount, order_date, payment_notes, payment_method, order_status, payment_status)
        VALUES (%s,%s,%s,%s,%s,%s,'Pending','Unpaid')
        RETURNING id
        """,
        (
            customer,
            total_cups,
            total_amount if total_amount > 0 else None,
            date.today(),
            notes,
            pm,
        ),
        fetch=True,
        one=True,
    )
    for pid, qty, unit_price, remark in line_data:
        query(
            """
            INSERT INTO order_items (order_id, product_id, quantity, unit_price, remarks)
            VALUES (%s,%s,%s,%s,%s)
            """,
            (row["id"], pid, qty, unit_price, remark),
        )
    recalc_order_totals(int(row["id"]))
    flash("Order received — thank you. We will follow up if anything is unclear.", "success")
    return redirect(url_for("shop_order_form"))


@app.get("/analytics")
def analytics_page():
    menu_by_category = query(
        """
        SELECT COALESCE(NULLIF(TRIM(category), ''), 'Uncategorised') AS cat, COUNT(*)::int AS n
        FROM margin_menu_items
        GROUP BY 1 ORDER BY n DESC, cat
        """,
        fetch=True,
    )
    top_customers = query(
        """
        SELECT customer_name,
               COUNT(*)::int AS order_count,
               COALESCE(SUM(quantity_cups), 0)::int AS cups
        FROM finance_cash_inflows
        WHERE customer_name IS NOT NULL
        GROUP BY customer_name
        ORDER BY cups DESC, order_count DESC
        LIMIT 20
        """,
        fetch=True,
    )
    matcha_vs_coffee = query(
        """
        SELECT COALESCE(cloud_type::text, 'unspecified') AS bucket, COUNT(*)::int AS n
        FROM recipes WHERE is_latte
        GROUP BY 1 ORDER BY n DESC
        """,
        fetch=True,
    )
    orders_by_weekday = query(
        """
        SELECT EXTRACT(ISODOW FROM txn_date)::int AS dow,
               COUNT(*)::int AS n,
               COALESCE(SUM(amount), 0)::float AS revenue
        FROM finance_cash_inflows
        WHERE txn_date IS NOT NULL
        GROUP BY dow ORDER BY dow
        """,
        fetch=True,
    )
    prep_plan_rows = _compute_prep_plan_readiness()
    prep_completion = {
        "total": len(prep_plan_rows),
        "ready": sum(1 for r in prep_plan_rows if r.get("state") == "ok"),
    }
    top_products = query(
        f"""
        SELECT
          COALESCE(p.product_name, f.product_name, '—') AS product_name,
          COALESCE(SUM(f.quantity_cups), 0)::int AS cups,
          COALESCE(SUM(f.amount), 0)::float AS revenue
        FROM finance_cash_inflows f
        {_sql_finance_inflows_join_products()}
        WHERE COALESCE(p.product_name, f.product_name) IS NOT NULL
        GROUP BY 1
        ORDER BY cups DESC, revenue DESC, product_name
        LIMIT 20
        """,
        fetch=True,
    )
    product_margin_snapshot = query(
        """
        SELECT
            p.product_name,
            p.selling_price,
            COALESCE(SUM((ri.qty_per_yield / NULLIF(r.base_yield_cups, 0)) * (ii.source_cost / NULLIF(ii.source_qty_g, 0))), 0) AS ingredient_cost_per_cup
        FROM products p
        LEFT JOIN recipes r ON r.product_id = p.id
        LEFT JOIN recipe_ingredients ri ON ri.recipe_id = r.id
        LEFT JOIN inventory_items ii ON ii.id = ri.inventory_item_id
        GROUP BY p.id, r.id
        ORDER BY p.product_name
        """,
        fetch=True,
    )
    return render_template(
        "analytics.html",
        menu_by_category=menu_by_category or [],
        top_customers=top_customers or [],
        matcha_vs_coffee=matcha_vs_coffee or [],
        orders_by_weekday=orders_by_weekday or [],
        prep_completion=prep_completion or {"total": 0, "ready": 0},
        top_products=top_products or [],
        product_margin_snapshot=product_margin_snapshot or [],
    )


@app.post("/finance/import-tracker")
def finance_import_tracker():
    csv_path = os.path.join(BASE_DIR, "database import", "3_The Mug Club_Financials - Financial Tracker.csv")
    if not os.path.isfile(csv_path):
        flash("Financial tracker CSV file not found.", "error")
        return redirect(url_for("finance_summary"))
    try:
        with open(csv_path, "rb") as f:
            inflows, outflows = import_financial_csv(f, replace=True)
        flash(
            f"Financial tracker imported: {inflows} inflows and {outflows} outflows.",
            "success",
        )
    except Exception as exc:  # noqa: BLE001
        flash(f"Financial import failed: {exc}", "error")
    return redirect(url_for("finance_summary"))


@app.route("/export/<name>")
def export_table(name):
    mapping = {
        "inventory_items": (
            "inventory_items.csv",
            [
                "item_name",
                "qty_grams",
                "source_cost",
                "source_qty_g",
                "supplier",
                "remark",
                "updated_flag",
            ],
            """
            SELECT item_name, qty_grams, source_cost, source_qty_g, supplier, remark, updated_flag
            FROM inventory_items ORDER BY item_name
            """,
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
                "customer_name",
                "product_name",
                "product_id",
                "payment_type",
                "payment_status",
            ],
            """
            SELECT source_txn_number, amount, description, quantity_cups, txn_date::text,
                   screenshot, customer_name, product_name, product_id, payment_type, payment_status
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
                "order_items",
                "cup_count",
                "total_amount",
                "order_date",
                "payment_notes",
                "payment_method",
                "order_status",
                "payment_status",
            ],
            """
            SELECT
              o.customer_name,
              COALESCE(STRING_AGG(p.product_name || ' x' || oi.quantity, ', ' ORDER BY oi.id), '') AS order_items,
              o.cup_count, o.total_amount, o.order_date::text,
              o.payment_notes, o.payment_method, o.order_status, o.payment_status
            FROM orders o
            LEFT JOIN order_items oi ON oi.order_id = o.id
            LEFT JOIN products p ON p.id = oi.product_id
            GROUP BY o.id
            ORDER BY o.id
            """,
        ),
        "products": (
            "products.csv",
            ["product_name", "product_type", "cloud_type", "flavour_name", "selling_price", "short_desc", "image_url", "is_active"],
            "SELECT product_name, product_type, cloud_type, flavour_name, selling_price, short_desc, image_url, is_active FROM products ORDER BY id",
        ),
        "flavours": (
            "flavours.csv",
            ["name", "cloud_type", "is_active"],
            "SELECT name, cloud_type, is_active FROM flavours ORDER BY id",
        ),
        "order_items": (
            "order_items.csv",
            ["order_id", "product_id", "product_name", "quantity", "unit_price", "remarks"],
            """
            SELECT oi.order_id, oi.product_id, p.product_name, oi.quantity, oi.unit_price, oi.remarks
            FROM order_items oi
            LEFT JOIN products p ON p.id = oi.product_id
            ORDER BY oi.id
            """,
        ),
        "recipes": (
            "recipes.csv",
            [
                "name",
                "drink_category",
                "is_latte",
                "cloud_type",
                "flavour_name",
                "notes",
                "base_yield_cups",
            ],
            """
            SELECT name, drink_category, is_latte, cloud_type, flavour_name, notes, base_yield_cups
            FROM recipes ORDER BY id
            """,
        ),
        "tasks": (
            "tasks.csv",
            [
                "title",
                "description",
                "assigned_member_id",
                "created_by_id",
                "status",
                "priority",
                "created_at",
            ],
            """
            SELECT title, description, assigned_member_id, created_by_id, status, priority,
                   created_at::text
            FROM tasks ORDER BY id
            """,
        ),
        "members": (
            "members.csv",
            ["name", "role", "email"],
            "SELECT name, role, email FROM members ORDER BY id",
        ),
    }
    if name not in mapping:
        flash("Unknown export.", "error")
        return redirect(url_for("dashboard"))
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
