-- =========================================================================
-- Online Shop Operations Dashboard  -  Supabase schema
-- Run this ONCE in the Supabase SQL editor (or via psql).
-- =========================================================================

-- Staff / team members --------------------------------------------------
CREATE TABLE IF NOT EXISTS members (
    id    SERIAL PRIMARY KEY,
    name  TEXT NOT NULL,
    role  TEXT,
    email TEXT
);

-- Tasks (the core task-tracker) -----------------------------------------
CREATE TABLE IF NOT EXISTS tasks (
    id                 SERIAL PRIMARY KEY,
    title              TEXT        NOT NULL,
    description        TEXT,
    assigned_member_id INT         REFERENCES members(id) ON DELETE SET NULL,
    created_by_id      INT         REFERENCES members(id) ON DELETE SET NULL,
    status             TEXT        NOT NULL DEFAULT 'Not Started'
        CHECK (status IN ('Not Started','In Progress','Completed')),
    priority           TEXT        NOT NULL DEFAULT 'Medium'
        CHECK (priority IN ('Low','Medium','High')),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Products / inventory --------------------------------------------------
CREATE TABLE IF NOT EXISTS products (
    id             SERIAL PRIMARY KEY,
    name           TEXT          NOT NULL,
    category       TEXT,
    stock_quantity INT           NOT NULL DEFAULT 0,
    cost_price     NUMERIC(10,2) NOT NULL DEFAULT 0,
    selling_price  NUMERIC(10,2) NOT NULL DEFAULT 0
);

-- Customer orders -------------------------------------------------------
CREATE TABLE IF NOT EXISTS orders (
    id             SERIAL PRIMARY KEY,
    customer_name  TEXT        NOT NULL,
    product_id     INT         REFERENCES products(id) ON DELETE SET NULL,
    quantity       INT         NOT NULL DEFAULT 1,
    order_status   TEXT        NOT NULL DEFAULT 'Pending'
        CHECK (order_status IN ('Pending','Processing','Completed','Cancelled')),
    payment_status TEXT        NOT NULL DEFAULT 'Unpaid'
        CHECK (payment_status IN ('Unpaid','Paid','Refunded')),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Useful indexes (optional, small speed-up) -----------------------------
CREATE INDEX IF NOT EXISTS idx_tasks_assigned ON tasks(assigned_member_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status   ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_orders_status  ON orders(order_status);
