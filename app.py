from flask import Flask, render_template, redirect, url_for
from flask import request
import sqlite3

app = Flask(__name__)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('/Users/kyeraikundalia/Documents/GitHub/NEA/users.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            conn.close()
            return render_template('signup.html', error='Username already exists')
        else:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        
    return render_template('signup.html')

@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        connect = sqlite3.connect('/Users/kyeraikundalia/Documents/GitHub/NEA/users.db')
        cursor = connect.cursor()

        username = request.form['username']
        password = request.form['password']
        cursor.execute('''
            SELECT * FROM users
            WHERE username = ? AND password = ?
        ''', (username, password))
        user = cursor.fetchone()

        if user:
            return redirect(url_for('home'))  # Redirect to the home page
        else:
            return 'Username or password is incorrect'

    return render_template('login.html')

@app.route('/home')
def home():
    refferer = request.referrer
    if refferer and refferer.endswith('/login'):
        return render_template('home.html')
    else:
        return redirect(url_for('login'))



if __name__ == '__main__':
    app.run(host=0.0, port=4000, debug=True)
