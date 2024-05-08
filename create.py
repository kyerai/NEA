import sqlite3

def create():
    connect = sqlite3.connect('/Users/kyeraikundalia/Documents/GitHub/NEA/users.db')
    cursor = connect.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE, 
            password TEXT
        )
    ''')
    connect.commit()
    connect.close()

create()
