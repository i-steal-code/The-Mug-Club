-- =========================================================================
-- Online Shop Operations Dashboard  -  SQLite schema
--
-- This file is executed automatically by app.py the first time the app
-- is run (it creates shop.db if it doesn't exist yet). You can also run
-- it manually with:
--       sqlite3 shop.db < schema.sql
-- =========================================================================

-- Staff / team members --------------------------------------------------
CREATE TABLE IF NOT EXISTS members (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT NOT NULL,
    role  TEXT,
    email TEXT
);

-- Tasks (the core task-tracker) -----------------------------------------
CREATE TABLE IF NOT EXISTS tasks (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    title              TEXT NOT NULL,
    description        TEXT,
    assigned_member_id INTEGER REFERENCES members(id) ON DELETE SET NULL,
    created_by_id      INTEGER REFERENCES members(id) ON DELETE SET NULL,
    status             TEXT NOT NULL DEFAULT 'Not Started'
        CHECK (status IN ('Not Started', 'In Progress', 'Completed')),
    priority           TEXT NOT NULL DEFAULT 'Medium'
        CHECK (priority IN ('Low', 'Medium', 'High')),
    created_at         TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP)
);

-- Products / inventory --------------------------------------------------
CREATE TABLE IF NOT EXISTS products (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT    NOT NULL,
    category       TEXT,
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    cost_price     REAL    NOT NULL DEFAULT 0,
    selling_price  REAL    NOT NULL DEFAULT 0
);

-- Customer orders -------------------------------------------------------
CREATE TABLE IF NOT EXISTS orders (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name  TEXT NOT NULL,
    product_id     INTEGER REFERENCES products(id) ON DELETE SET NULL,
    quantity       INTEGER NOT NULL DEFAULT 1,
    order_status   TEXT NOT NULL DEFAULT 'Pending'
        CHECK (order_status IN ('Pending', 'Processing', 'Completed', 'Cancelled')),
    payment_status TEXT NOT NULL DEFAULT 'Unpaid'
        CHECK (payment_status IN ('Unpaid', 'Paid', 'Refunded')),
    created_at     TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP)
);

-- Small indexes to speed up the filter queries --------------------------
CREATE INDEX IF NOT EXISTS idx_tasks_assigned ON tasks(assigned_member_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status   ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_orders_status  ON orders(order_status);
