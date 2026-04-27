-- v0.2.1 → v0.2.5 manual bootstrap for Supabase SQL editor.
-- 1) Clean and normalize CSV names manually before pasting values.
-- 2) Run this file in Supabase SQL editor.
-- 3) Extend with additional INSERT rows as needed.

BEGIN;

-- Optional reset for fresh migration
TRUNCATE TABLE
  order_items,
  products,
  finance_cash_outflows,
  finance_cash_inflows,
  margin_menu_items,
  margin_ingredients,
  inventory_prep,
  inventory_items
RESTART IDENTITY CASCADE;

-- Inventory (supplier/source fields included)
INSERT INTO inventory_items
  (item_name, qty_grams, source_cost, source_qty_g, supplier, remark, updated_flag)
VALUES
  ('cup', 77, 11.49, 100, 'shopee', NULL, FALSE),
  ('lid', 70, 11.49, 100, 'shopee', NULL, FALSE),
  ('straw', 100, 5.49, 100, 'shopee', 'I CANT COUNT', FALSE),
  ('ice', 20000, 10.00, 18000, 'JM ICE', '2 bags in freezer (partially full)', TRUE),
  ('milk', 4000, 6.97, 2000, 'fairprice meiji', NULL, TRUE),
  ('heavy cream', 400, 8.00, 1000, 'redman millac gold', NULL, TRUE),
  ('naoki matcha', 180, 28.99, 80, 'shopee', NULL, FALSE),
  ('coffee capsule', 24, 8.40, 57, 'fairprice starbucks', 'in pieces', TRUE),
  ('brown sugar', 350, 3.40, 800, 'fairprice', NULL, FALSE),
  ('strawberry puree', 1067, 3.90, 180, 'don don donki', NULL, FALSE),
  ('raw honey', 390, 6.65, 360, 'fairprice', NULL, TRUE),
  ('butter (salted)', 0, 6.35, 225, 'fairprice SCS', NULL, TRUE),
  ('honey buttercream', 560, NULL, NULL, NULL, NULL, FALSE),
  ('extra dark cocoa powder', 200, 6.90, 250, 'redman', NULL, TRUE),
  ('vanilla extract', 28, 6.80, 33, 'redman', NULL, FALSE),
  ('mocha veloute', 200, NULL, NULL, NULL, NULL, TRUE),
  ('cream cheese', 0, 5.00, 250, 'redman royal victoria', NULL, TRUE),
  ('egg', 0, 2.85, 550, 'fairprice pasar fresh', 'using eggs from home', TRUE),
  ('ladyfinger cookies', 22, 5.65, 400, 'redman balocco sponge finger', 'by pcs', TRUE);

INSERT INTO inventory_prep (component_name, qty_for_week, ready) VALUES
  ('base', '50', FALSE),
  ('matcha', '30', TRUE),
  ('coffee', '30', TRUE),
  ('strawberry', '20', TRUE),
  ('honey buttercream', '20', TRUE),
  ('mocha', '6', TRUE),
  ('ice chocolate', '10', TRUE);

-- Product catalog (editable later in Products page)
INSERT INTO products (product_name, product_type, cloud_type, flavour_name, is_active, display_order) VALUES
  ('Matcha Original Latte', 'latte', 'matcha', 'original', TRUE, 10),
  ('Matcha Strawberry Latte', 'latte', 'matcha', 'strawberry', TRUE, 20),
  ('Matcha Honey Buttercream Latte', 'latte', 'matcha', 'honey buttercream', TRUE, 30),
  ('Coffee Latte', 'latte', 'coffee', NULL, TRUE, 40),
  ('Coffee Honey Buttercream Latte', 'latte', 'coffee', 'honey buttercream', TRUE, 50),
  ('Coffee Mocha Latte', 'latte', 'coffee', 'mocha', TRUE, 60),
  ('Iced Chocolate', 'special', NULL, NULL, TRUE, 70),
  ('Dirty', 'special', NULL, NULL, TRUE, 80),
  ('Matcha tiramisu', 'special', NULL, NULL, TRUE, 90),
  ('Strawberry Milk', 'special', NULL, NULL, TRUE, 100),
  ('Buttercream Milk', 'special', NULL, NULL, TRUE, 110);

-- v0.2.5 — make sure every registered product has an empty, modifiable recipe
-- in the recipe databank. Steps + ingredient lines are keyed in by hand later
-- via the recipe detail page; this just creates the joining row so the recipe
-- shows up in /products and can be opened.
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
  'Auto-seeded recipe row. Fill in ingredients + product recipe steps in the recipe databank.'
FROM products p
WHERE NOT EXISTS (
  SELECT 1 FROM recipes r WHERE r.product_id = p.id
);

-- v0.2.5 — seed reusable components for the cloud + flavour split used by the
-- prep components dashboard. Cloud (matcha / coffee) and the active flavour
-- batches (strawberry, honey buttercream, mocha) are first-class so prep math
-- stays commutative. base_yield is "portions of cloud / flavour produced".
INSERT INTO components (name, component_type, base_yield, notes) VALUES
  ('Matcha cloud',           'cloud',    1, 'Whisked matcha base for matcha lattes.'),
  ('Coffee cloud',           'cloud',    1, 'Brewed espresso shot for coffee lattes.'),
  ('Strawberry flavour',     'flavour',  1, 'Strawberry puree base for strawberry lattes / milk.'),
  ('Honey buttercream',      'flavour',  1, 'Honey + salted butter cream for buttercream drinks.'),
  ('Mocha flavour',          'flavour',  1, 'Cocoa-forward base for mocha drinks.'),
  ('Iced chocolate base',    'flavour',  1, 'Hot chocolate / iced chocolate base.'),
  ('Tiramisu cream',         'flavour',  1, 'Cream cheese + cream + ladyfinger setup for tiramisu cups.')
ON CONFLICT (name) DO NOTHING;

COMMIT;
