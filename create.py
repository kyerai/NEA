import sqlite3

# Connect to SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('app.db')
c = conn.cursor()

# Create a table called users
# Create users table with role selection and classroom association
c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        password TEXT NOT NULL,
        balance REAL DEFAULT 10000,
        salt TEXT,
        role TEXT CHECK(role IN ('student', 'teacher')) NOT NULL,
        classroom_id INTEGER,
        FOREIGN KEY(classroom_id) REFERENCES classrooms(id)
    )
''')

# Create classrooms table
c.execute('''
    CREATE TABLE IF NOT EXISTS classrooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        teacher_id INTEGER,
        FOREIGN KEY(teacher_id) REFERENCES users(id)
    )
''')

# Create classroom_members table with join_date
c.execute('''
    CREATE TABLE IF NOT EXISTS classroom_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        classroom_id INTEGER,
        student_id INTEGER,
        join_date TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(classroom_id) REFERENCES classrooms(id),
        FOREIGN KEY(student_id) REFERENCES users(id)
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