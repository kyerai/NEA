from flask import Flask, render_template, redirect, url_for
from flask import request
import sqlite3

app = Flask(__name__)

@app.route('/')
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
            return render_template("home.html", _methods=["POST"])  # Redirect to the home page with POST method
        else:
            return 'Username or password is incorrect'

    return render_template('login.html')

@app.route('/home', methods=['POST', 'GET'])
def home():
    if request.method == 'POST':
        return render_template('home.html')
    elif request.method == 'GET':
        return render_template("login.html", error="Please login first")



if __name__ == '__main__':
    app.run(host=0.0, port=4000, debug=True)
