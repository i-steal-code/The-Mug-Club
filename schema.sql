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
    source_cost   DOUBLE PRECISION,
    source_qty_g  DOUBLE PRECISION,
    supplier      TEXT,
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
    id                SERIAL PRIMARY KEY,
    customer_name     TEXT NOT NULL,
    cup_count         INTEGER NOT NULL DEFAULT 1,
    total_amount      DOUBLE PRECISION,
    order_date        DATE,
    payment_notes     TEXT,
    payment_method    TEXT,
    order_status      TEXT NOT NULL DEFAULT 'Pending'
        CHECK (order_status IN ('Pending', 'Processing', 'Completed', 'Cancelled')),
    payment_status    TEXT NOT NULL DEFAULT 'Unpaid'
        CHECK (payment_status IN ('Unpaid', 'Paid', 'Refunded')),
    finance_pushed_at TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS products (
    id             SERIAL PRIMARY KEY,
    product_name   TEXT NOT NULL UNIQUE,
    product_type   TEXT NOT NULL DEFAULT 'special'
        CHECK (product_type IN ('latte', 'special')),
    cloud_type     TEXT CHECK (cloud_type IS NULL OR cloud_type IN ('coffee', 'matcha')),
    flavour_name   TEXT,
    selling_price  DOUBLE PRECISION,
    short_desc     TEXT,
    image_url      TEXT,
    is_active      BOOLEAN NOT NULL DEFAULT TRUE,
    display_order  INTEGER NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS order_items (
    id            SERIAL PRIMARY KEY,
    order_id      INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id    INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity      INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    unit_price    DOUBLE PRECISION,
    remarks       TEXT
);

-- Financial tracker — cash inflows (1NF: one row per singular product sold) -
CREATE TABLE IF NOT EXISTS finance_cash_inflows (
    id                 SERIAL PRIMARY KEY,
    source_txn_number  INTEGER,
    amount             DOUBLE PRECISION,
    description        TEXT,
    quantity_cups      INTEGER,
    txn_date           DATE,
    screenshot         TEXT,
    person_in_charge   TEXT,
    customer_name      TEXT,
    product_name       TEXT,
    product_id         INTEGER REFERENCES products(id) ON DELETE SET NULL,
    payment_type       TEXT CHECK (payment_type IS NULL OR payment_type IN ('paynow', 'cash')),
    payment_status     TEXT CHECK (payment_status IS NULL OR payment_status IN ('paid', 'unpaid'))
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
    product_id       INTEGER UNIQUE REFERENCES products(id) ON DELETE CASCADE,
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

-- Standalone reusable components (e.g. "Matcha cloud", "Buttercream") --------
CREATE TABLE IF NOT EXISTS components (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    component_type  TEXT,
    notes           TEXT,
    base_yield      DOUBLE PRECISION NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS component_ingredients (
    id                 SERIAL PRIMARY KEY,
    component_id       INTEGER NOT NULL REFERENCES components(id) ON DELETE CASCADE,
    inventory_item_id  INTEGER REFERENCES inventory_items(id) ON DELETE SET NULL,
    label_override     TEXT,
    qty_g              DOUBLE PRECISION,
    sort_order         INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS component_steps (
    id            SERIAL PRIMARY KEY,
    component_id  INTEGER NOT NULL REFERENCES components(id) ON DELETE CASCADE,
    body          TEXT NOT NULL,
    sort_order    INTEGER NOT NULL DEFAULT 0,
    done          BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS recipe_ingredients (
    id                   SERIAL PRIMARY KEY,
    recipe_id            INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    sort_order           INTEGER NOT NULL DEFAULT 0,
    inventory_item_id    INTEGER REFERENCES inventory_items(id) ON DELETE SET NULL,
    component_id         INTEGER REFERENCES components(id) ON DELETE SET NULL,
    label_override       TEXT,
    qty_per_yield        DOUBLE PRECISION,
    unit                 TEXT NOT NULL DEFAULT 'g',
    prep_note            TEXT,
    prep_done            BOOLEAN NOT NULL DEFAULT FALSE
);

-- Weekly prep plan (v0.2.5 dashboard groundwork). One row per component to prep
-- for the upcoming service week. Cloud (matcha/coffee) and flavour (strawberry,
-- mocha, honey buttercream, etc.) are intentionally separate rows so portion
-- math is commutative across the products that use them.
CREATE TABLE IF NOT EXISTS prep_plan (
    id              SERIAL PRIMARY KEY,
    week_start      DATE,
    component_id    INTEGER REFERENCES components(id) ON DELETE SET NULL,
    component_label TEXT NOT NULL,
    qty_to_prep     DOUBLE PRECISION NOT NULL DEFAULT 0,
    notes           TEXT,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS flavours (
    id             SERIAL PRIMARY KEY,
    name           TEXT NOT NULL UNIQUE,
    cloud_type     TEXT CHECK (cloud_type IS NULL OR cloud_type IN ('coffee', 'matcha')),
    is_active      BOOLEAN NOT NULL DEFAULT TRUE,
    display_order  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS recipe_components (
    id            SERIAL PRIMARY KEY,
    recipe_id     INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    component_name TEXT NOT NULL,
    remarks       TEXT,
    sort_order    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS recipe_component_prep (
    id             SERIAL PRIMARY KEY,
    component_id    INTEGER NOT NULL REFERENCES recipe_components(id) ON DELETE CASCADE,
    prep_name       TEXT NOT NULL,
    remarks         TEXT,
    done            BOOLEAN NOT NULL DEFAULT FALSE,
    sort_order      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS recipe_component_steps (
    id             SERIAL PRIMARY KEY,
    component_id    INTEGER NOT NULL REFERENCES recipe_components(id) ON DELETE CASCADE,
    step_name       TEXT NOT NULL,
    remarks         TEXT,
    done            BOOLEAN NOT NULL DEFAULT FALSE,
    sort_order      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS recipe_assembly_steps (
    id            SERIAL PRIMARY KEY,
    recipe_id     INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    step_name     TEXT NOT NULL,
    remarks       TEXT,
    done          BOOLEAN NOT NULL DEFAULT FALSE,
    sort_order    INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_tasks_assigned ON tasks(assigned_member_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status   ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_orders_status  ON orders(order_status);
CREATE INDEX IF NOT EXISTS idx_finance_inflow_date ON finance_cash_inflows(txn_date);
CREATE INDEX IF NOT EXISTS idx_finance_inflows_product ON finance_cash_inflows(product_id);
CREATE INDEX IF NOT EXISTS idx_finance_outflow_date ON finance_cash_outflows(txn_date);
CREATE INDEX IF NOT EXISTS idx_recipe_steps_recipe ON recipe_steps(recipe_id);
CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_recipe ON recipe_ingredients(recipe_id);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_recipes_product ON recipes(product_id);
CREATE INDEX IF NOT EXISTS idx_recipe_components_recipe ON recipe_components(recipe_id);
CREATE INDEX IF NOT EXISTS idx_recipe_prep_component ON recipe_component_prep(component_id);
CREATE INDEX IF NOT EXISTS idx_recipe_steps_component ON recipe_component_steps(component_id);
CREATE INDEX IF NOT EXISTS idx_recipe_assembly_recipe ON recipe_assembly_steps(recipe_id);
CREATE INDEX IF NOT EXISTS idx_component_ingredients ON component_ingredients(component_id);
CREATE INDEX IF NOT EXISTS idx_component_steps ON component_steps(component_id);
CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_component ON recipe_ingredients(component_id);
CREATE INDEX IF NOT EXISTS idx_prep_plan_component ON prep_plan(component_id);
CREATE INDEX IF NOT EXISTS idx_prep_plan_week ON prep_plan(week_start);
