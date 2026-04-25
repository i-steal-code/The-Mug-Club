-- v0.2.1 manual bootstrap for Supabase SQL editor.
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

COMMIT;
