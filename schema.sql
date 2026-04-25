-- The Mug Club — PostgreSQL schema (Supabase / local Postgres)
-- Run once on deploy; tables use IF NOT EXISTS for idempotent startup.

-- Staff / team members (unchanged feature surface) ---------------------------
CREATE TABLE IF NOT EXISTS members (
    id    SERIAL PRIMARY KEY,
    name  TEXT NOT NULL,
    role  TEXT,
    email TEXT
);

CREATE TABLE IF NOT EXISTS tasks (
    id                 SERIAL PRIMARY KEY,
    title              TEXT NOT NULL,
    description        TEXT,
    assigned_member_id INTEGER REFERENCES members(id) ON DELETE SET NULL,
    created_by_id      INTEGER REFERENCES members(id) ON DELETE SET NULL,
    status             TEXT NOT NULL DEFAULT 'Not Started'
        CHECK (status IN ('Not Started', 'In Progress', 'Completed')),
    priority           TEXT NOT NULL DEFAULT 'Medium'
        CHECK (priority IN ('Low', 'Medium', 'High')),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Physical stock (from inventory datasheet) -------------------------------
CREATE TABLE IF NOT EXISTS inventory_items (
    id            SERIAL PRIMARY KEY,
    item_name     TEXT NOT NULL,
    qty_grams     DOUBLE PRECISION,
    remark        TEXT,
    updated_flag  BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (item_name)
);

-- Prep components (second block in inventory CSV) ---------------------------
CREATE TABLE IF NOT EXISTS inventory_prep (
    id              SERIAL PRIMARY KEY,
    component_name  TEXT NOT NULL,
    qty_for_week    TEXT,
    ready           BOOLEAN NOT NULL DEFAULT FALSE
);

-- Margin datasheet — ingredient lines ---------------------------------------
CREATE TABLE IF NOT EXISTS margin_ingredients (
    id             SERIAL PRIMARY KEY,
    category       TEXT,
    ingredient     TEXT NOT NULL,
    cost_per_cup   DOUBLE PRECISION,
    amt_used_g     DOUBLE PRECISION,
    source_cost    DOUBLE PRECISION,
    source_qty_g   DOUBLE PRECISION,
    supplier       TEXT
);

-- Margin datasheet — menu / drink rows --------------------------------------
CREATE TABLE IF NOT EXISTS margin_menu_items (
    id             SERIAL PRIMARY KEY,
    category       TEXT,
    item_name      TEXT NOT NULL,
    cost           DOUBLE PRECISION,
    selling_price  DOUBLE PRECISION,
    profit         DOUBLE PRECISION
);

-- Orders (Google Form / manual ops) — before finance inflows (FK) ----------
CREATE TABLE IF NOT EXISTS orders (
    id               SERIAL PRIMARY KEY,
    customer_name    TEXT NOT NULL,
    order_summary    TEXT,
    cup_count        INTEGER NOT NULL DEFAULT 1,
    total_amount     DOUBLE PRECISION,
    order_date       DATE,
    payment_notes    TEXT,
    payment_method   TEXT,
    order_status     TEXT NOT NULL DEFAULT 'Pending'
        CHECK (order_status IN ('Pending', 'Processing', 'Completed', 'Cancelled')),
    payment_status   TEXT NOT NULL DEFAULT 'Unpaid'
        CHECK (payment_status IN ('Unpaid', 'Paid', 'Refunded')),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Financial tracker — cash inflows (revenue / order-like rows) --------------
CREATE TABLE IF NOT EXISTS finance_cash_inflows (
    id                 SERIAL PRIMARY KEY,
    source_txn_number  INTEGER,
    amount             DOUBLE PRECISION,
    description        TEXT,
    quantity_cups      INTEGER,
    txn_date           DATE,
    screenshot         TEXT,
    person_in_charge   TEXT,
    linked_order_id    INTEGER REFERENCES orders(id) ON DELETE SET NULL
);

-- Financial tracker — cash outflows (expenses) ------------------------------
CREATE TABLE IF NOT EXISTS finance_cash_outflows (
    id                 SERIAL PRIMARY KEY,
    source_txn_number  INTEGER,
    amount             DOUBLE PRECISION,
    description        TEXT,
    txn_date           DATE,
    screenshot         TEXT,
    person_in_charge   TEXT
);

-- Recipes / menu items (latte rule enforced in app) -------------------------
CREATE TABLE IF NOT EXISTS recipes (
    id               SERIAL PRIMARY KEY,
    name             TEXT NOT NULL,
    drink_category   TEXT,
    is_latte         BOOLEAN NOT NULL DEFAULT FALSE,
    cloud_type       TEXT CHECK (cloud_type IS NULL OR cloud_type IN ('coffee', 'matcha')),
    flavour_name     TEXT NOT NULL DEFAULT '',
    notes            TEXT,
    base_yield_cups  DOUBLE PRECISION NOT NULL DEFAULT 1,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT recipes_latte_cloud CHECK (
        NOT is_latte OR cloud_type IN ('coffee', 'matcha')
    )
);

CREATE TABLE IF NOT EXISTS recipe_steps (
    id          SERIAL PRIMARY KEY,
    recipe_id   INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    step_order  INTEGER NOT NULL DEFAULT 0,
    body        TEXT NOT NULL,
    completed   BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS recipe_ingredients (
    id                   SERIAL PRIMARY KEY,
    recipe_id            INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    sort_order           INTEGER NOT NULL DEFAULT 0,
    label                TEXT NOT NULL,
    qty_per_yield        DOUBLE PRECISION,
    unit                 TEXT NOT NULL DEFAULT 'g',
    inventory_item_name  TEXT
);

CREATE INDEX IF NOT EXISTS idx_tasks_assigned ON tasks(assigned_member_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status   ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_orders_status  ON orders(order_status);
CREATE INDEX IF NOT EXISTS idx_finance_inflow_date ON finance_cash_inflows(txn_date);
CREATE INDEX IF NOT EXISTS idx_finance_outflow_date ON finance_cash_outflows(txn_date);
CREATE INDEX IF NOT EXISTS idx_recipe_steps_recipe ON recipe_steps(recipe_id);
CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_recipe ON recipe_ingredients(recipe_id);
CREATE INDEX IF NOT EXISTS idx_finance_inflow_order ON finance_cash_inflows(linked_order_id);
