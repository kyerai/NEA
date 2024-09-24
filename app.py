from flask import Flask, render_template, redirect, url_for, request, session, flash
import sqlite3
import sqlite3
from datetime import datetime
import yfinance as yf


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
        conn = sqlite3.connect('/Users/kyeraikundalia/Documents/GitHub/NEA/app.db')
        cursor = conn.cursor()

        if request.method == 'POST':
            if 'close_position' in request.form:
                # Close the position by removing it from the portfolio
                position_id = int(request.form['close_position'])
                cursor.execute("SELECT asset_name, quantity, purchase_price FROM portfolio WHERE id = ?", (position_id,))
                position = cursor.fetchone()

                if position:
                    asset_name, quantity, purchase_price = position
                    current_price = round(yf.Ticker(asset_name).history(period='1d')['Close'][0], 2)
                    total_value = current_price * quantity
                    profit_or_loss = (current_price - purchase_price) * quantity

                    # Get the user's current balance and update it
                    cursor.execute("SELECT balance FROM users WHERE username = ?", (session['username'],))
                    current_balance = cursor.fetchone()[0]
                    new_balance = round(current_balance + total_value, 2)

                    cursor.execute("UPDATE users SET balance = ? WHERE username = ?", (new_balance, session['username']))
                    cursor.execute("DELETE FROM portfolio WHERE id = ?", (position_id,))
                    conn.commit()

                    # Show profit/loss in the flash message
                    if profit_or_loss >= 0:
                        flash(f'Position closed for {asset_name}. Profit: ${profit_or_loss:.2f}. Added ${total_value:.2f} to your balance.')
                    else:
                        flash(f'Position closed for {asset_name}. Loss: ${-profit_or_loss:.2f}. Added ${total_value:.2f} to your balance.')

            elif 'reset_balance' in request.form:
                # Reset user's balance to a default value (e.g., $10,000) and delete all positions
                default_balance = 10000
                cursor.execute("UPDATE users SET balance = ? WHERE username = ?", (default_balance, session['username']))
                cursor.execute("DELETE FROM portfolio WHERE user_id = (SELECT id FROM users WHERE username = ?)", (session['username'],))
                conn.commit()
                flash('Portfolio balance reset to $10,000 and all positions closed.')

        # Fetch portfolio positions for the logged-in user
        cursor.execute("SELECT id FROM users WHERE username = ?", (session['username'],))
        user_id = cursor.fetchone()[0]
        cursor.execute("SELECT * FROM portfolio WHERE user_id = ?", (user_id,))
        positions = cursor.fetchall()

        # Get current prices for each asset in portfolio
        current_price = {}
        for position in positions:
            asset_name = position[2]
            current_price[asset_name] = round(yf.Ticker(asset_name).history(period='1d')['Close'][0], 2)

        # Get user's remaining balance
        cursor.execute("SELECT balance FROM users WHERE username = ?", (session['username'],))
        balance = cursor.fetchone()[0]

        conn.close()
        return render_template('portfolio.html', positions=positions, current_price=current_price, balance=balance)

    return redirect('/login')



@app.route('/trade', methods=['GET', 'POST'])
def trade():
    if 'logged_in' in session and session['logged_in']:
        conn = sqlite3.connect('/Users/kyeraikundalia/Documents/GitHub/NEA/app.db')
        cursor = conn.cursor()

        if request.method == 'POST':
            asset_name = request.form['asset_name']
            quantity = int(request.form['quantity'])
            purchase_price = round(yf.Ticker(asset_name).history(period='1d')['Close'][0], 2)
            total_cost = purchase_price * quantity

            # Get user's current balance
            cursor.execute("SELECT balance FROM users WHERE username = ?", (session['username'],))
            current_balance = cursor.fetchone()[0]

            if total_cost <= current_balance:
                # Deduct cost from balance and update user's balance
                new_balance = round(current_balance - total_cost, 2)
                cursor.execute("UPDATE users SET balance = ? WHERE username = ?", (new_balance, session['username']))

                # Get user ID and save new trade in portfolio
                cursor.execute("SELECT id FROM users WHERE username = ?", (session['username'],))
                user_id = cursor.fetchone()[0]
                purchase_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("INSERT INTO portfolio (user_id, asset_name, quantity, purchase_price, purchase_date) VALUES (?, ?, ?, ?, ?)",
                               (user_id, asset_name, quantity, purchase_price, purchase_date))
                conn.commit()
            else:
                # Notify the user if they don't have enough balance
                flash('Not enough balance to make the purchase!')

        # Fetch user's current balance to display on trade page
        cursor.execute("SELECT balance FROM users WHERE username = ?", (session['username'],))
        balance = cursor.fetchone()[0]
        conn.close()

        return render_template('trade.html', balance=balance)

    return redirect('/login')



@app.route('/logout')
def logout():
    session.pop('logged_in', None)  # Remove session variable
    session.pop('username', None)  # Remove username from session
    return redirect(url_for('index'))  # Redirect to index page

if __name__ == '__main__':
    app.run(debug=True, port=4000)
