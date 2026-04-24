-- Optional seed after schema (only applied when members table is empty — see app.py)

INSERT INTO members (name, role, email) VALUES
    ('Alice Tan',   'Manager',          'alice@example.com'),
    ('Ben Lim',     'Operations',       'ben@example.com'),
    ('Chloe Ng',    'Customer Service', 'chloe@example.com'),
    ('Darren Koh',  'Logistics',        'darren@example.com');

INSERT INTO tasks (title, description, assigned_member_id, created_by_id, status, priority) VALUES
    ('Restock cups',           'Order 12oz cups + lids if below par level.',  2, 1, 'Not Started', 'High'),
    ('Verify PayLah payment',  'Match Form response to finance inflow.',      3, 1, 'In Progress', 'Medium'),
    ('Update inventory sheet', 'Sync counts after weekend service.',          4, 1, 'Not Started', 'Low');
