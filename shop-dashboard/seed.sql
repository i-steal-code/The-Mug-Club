-- =========================================================================
-- Sample data for the demo.
-- Run this AFTER schema.sql, in the Supabase SQL editor.
-- Safe to re-run: it just appends more rows.
-- =========================================================================

INSERT INTO members (name, role, email) VALUES
  ('Alice Tan',   'Manager',          'alice@shop.com'),
  ('Ben Lim',     'Operations',       'ben@shop.com'),
  ('Chloe Ng',    'Customer Service', 'chloe@shop.com'),
  ('Darren Koh',  'Logistics',        'darren@shop.com');

INSERT INTO products (name, category, stock_quantity, cost_price, selling_price) VALUES
  ('Black Cotton T-Shirt',  'Apparel',     25, 6.00,  15.00),
  ('Canvas Tote Bag',       'Accessories', 12, 3.50,   9.90),
  ('Ceramic Mug',           'Home',        40, 2.50,   8.50),
  ('Notebook A5',           'Stationery',   3, 1.80,   5.50),
  ('Wireless Earbuds',      'Electronics',  8, 22.00, 49.90);

INSERT INTO tasks (title, description, assigned_member_id, created_by_id, status, priority) VALUES
  ('Restock A5 Notebooks',            'Stock below 5 units. Reorder from supplier.', 2, 1, 'Not Started', 'High'),
  ('Pack order #1024',                'Customer: Jane Doe, 2x Canvas Tote Bag.',     4, 1, 'In Progress', 'Medium'),
  ('Verify payment for order #1020',  'Check PayNow transfer confirmation.',         3, 1, 'Completed',   'Medium'),
  ('Update product listing photos',   'Upload fresh photos for earbuds.',            1, 1, 'Not Started', 'Low'),
  ('Reply customer enquiry',          'Reply to customer question about mug colour.',3, 1, 'In Progress', 'Low');

INSERT INTO orders (customer_name, product_id, quantity, order_status, payment_status) VALUES
  ('Jane Doe',    2, 2, 'Processing', 'Paid'),
  ('John Lee',    5, 1, 'Pending',    'Unpaid'),
  ('Mary Wong',   3, 4, 'Completed',  'Paid'),
  ('Aiden Chua',  1, 3, 'Completed',  'Paid');
