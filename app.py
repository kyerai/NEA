from flask import Flask, render_template, redirect, url_for, request, session, g
import sqlite3
import sqlite3
from datetime import datetime, timedelta


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Set a secret key for sessions

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('/Users/kyeraikundalia/Documents/GitHub/NEA/app.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            conn.close()
            return render_template('signup.html', error="Details Already Exist")
        else:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('/Users/kyeraikundalia/Documents/GitHub/NEA/app.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()

        if user:
            session['logged_in'] = True  # Set session variable
            session['username'] = username  # Store username in session
            return redirect(url_for('home'))
        else:
            return 'Username or password is incorrect'

    return render_template('login.html')

@app.route('/home')
def home():
    if 'logged_in' in session and session['logged_in']:
        return render_template('home.html')
    else:
        return redirect(url_for('login'))
    
@app.route('/portfolio', methods=['GET', 'POST'])
def portfolio():
    if 'logged_in' in session and session['logged_in']:
        if request.method == 'POST':
            asset_name = request.form['asset_name']
            quantity = request.form['quantity']
            purchase_price = request.form['purchase_price']
            purchase_date = request.form['purchase_date']
            
            conn = sqlite3.connect('/Users/kyeraikundalia/Documents/GitHub/NEA/app.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username = ?", (session['username'],))
            user_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO portfolio (user_id, asset_name, quantity, purchase_price, purchase_date) VALUES (?, ?, ?, ?, ?)", (user_id, asset_name, quantity, purchase_price, purchase_date))
            conn.commit()
            conn.close()
                  
        try:
            conn = sqlite3.connect('/Users/kyeraikundalia/Documents/GitHub/NEA/app.db')
            print("Database connected successfully")  # Debugging statement 1
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username = ?", (session['username'],))
            user_id = cursor.fetchone()[0] 
            print(f"User ID: {user_id}")  # Debugging statement 2
            cursor.execute("SELECT * FROM portfolio WHERE user_id = ?", (user_id,))
            positions = cursor.fetchall()
            print(f"Positions: {positions}")  # Debugging statement 3
        except:
            positions = []

        return render_template('portfolio.html', positions=positions)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)  # Remove session variable
    session.pop('username', None)  # Remove username from session
    return redirect(url_for('index'))  # Redirect to index page

if __name__ == '__main__':
    app.run(debug=True, port=4000)
