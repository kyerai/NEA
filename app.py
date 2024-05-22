from flask import Flask, render_template, redirect, url_for, request, session
import sqlite3

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
        
        conn = sqlite3.connect('/Users/kyeraikundalia/Documents/GitHub/NEA/users.db')
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
        
        conn = sqlite3.connect('/Users/kyeraikundalia/Documents/GitHub/NEA/users.db')
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

@app.route('/logout')
def logout():
    session.pop('logged_in', None)  # Remove session variable
    session.pop('username', None)  # Remove username from session
    return redirect(url_for('index'))  # Redirect to index page

if __name__ == '__main__':
    app.run(debug=True)
