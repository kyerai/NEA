import sqlite3

# Connect to SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('app.db')
c = conn.cursor()

# Create a table called users
c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        password TEXT NOT NULL,
        balance real DEFAULT 10000,
        salt TEXT
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS portfolio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        asset_name TEXT,
        quantity INTEGER,
        purchase_price REAL,
        position_type TEXT,  
        stop_loss REAL,
        take_profit REAL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
''')

# Close the connection
conn.close()