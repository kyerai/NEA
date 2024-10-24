from flask import Flask, render_template, redirect, url_for, request, session, flash
import sqlite3
from datetime import datetime
import yfinance as yf
import plotly.io as pio
import plotly.graph_objects as go

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with your actual secret key


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('/Users/kyeraikundalia/Documents/GitHub/NEA/app.db')  # Update with your DB path
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['logged_in'] = True
            session['username'] = username
            session['user_id'] = user[0]
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password.')
    
    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('/Users/kyeraikundalia/Documents/GitHub/NEA/app.db')  # Update with your DB path
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password, balance) VALUES (?, ?, 100000)", (username, password))
        conn.commit()
        conn.close()
        flash('Signup successful. Please login.')
        return redirect(url_for('login'))
    
    return render_template('signup.html')


@app.route('/home')
def home():
    if 'logged_in' in session and session['logged_in']:
        return render_template('home.html')
    return redirect('/login')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

def validate_stock_symbol(symbol):
    # Basic check: Ensure it's alphanumeric and has a reasonable length
    return symbol.isalnum() and 1 <= len(symbol) <= 5

def validate_quantity(quantity):
    return quantity > 0

@app.route('/trade', methods=['GET', 'POST'])
def trade():
    if 'logged_in' in session and session['logged_in']:
        conn = sqlite3.connect('/Users/kyeraikundalia/Documents/GitHub/NEA/app.db')  # Update with your DB path
        cursor = conn.cursor()

        graph_html = None  # Initialize graph_html to None

        if request.method == 'POST':
            asset_name = request.form['asset_name']  # Get asset name from form
            action = request.form.get('action', 'search')  # Default to 'search' if no action provided

            # Fetch historical data for the asset
            try:
                data = yf.Ticker(asset_name).history(period='6mo')
                
                # Create a candlestick chart using Plotly
                fig = go.Figure(data=[go.Candlestick(x=data.index,
                                                     open=data['Open'],
                                                     high=data['High'],
                                                     low=data['Low'],
                                                     close=data['Close'])])

                # Customize the chart layout
                fig.update_layout(title=f'{asset_name} Candlestick Chart',
                                  xaxis_title='Date',
                                  yaxis_title='Price')

                # Convert Plotly figure to interactive HTML
                graph_html = pio.to_html(fig, full_html=False)
                flash(f'Stock graph for {asset_name} displayed below.')
            except Exception as e:
                flash(f'Error fetching data for {asset_name}: {str(e)}')
                return redirect(url_for('trade'))

            # If no quantity is provided, only show the graph
            if 'quantity' not in request.form or not request.form['quantity']:
                cursor.execute("SELECT balance FROM users WHERE username = ?", (session['username'],))
                balance = cursor.fetchone()[0]
                conn.close()
                return render_template('trade.html', balance=balance, graph_html=graph_html)

            # Otherwise, process the buy/short sell logic
            quantity = int(request.form['quantity'])

            if not validate_stock_symbol(asset_name):
                flash('Invalid asset name.')
                return redirect(url_for('trade'))
            if not validate_quantity(quantity):
                flash('Quantity must be greater than zero.')
                return redirect(url_for('trade'))
            
            # Fetch stock price with error handling
            try:
                purchase_price = round(yf.Ticker(asset_name).history(period='1d')['Close'][0], 2)
            except Exception as e:
                flash(f'Error fetching price for {asset_name}: {str(e)}')
                return redirect(url_for('trade'))

            # Check user balance
            cursor.execute("SELECT balance FROM users WHERE username = ?", (session['username'],))
            current_balance = cursor.fetchone()[0]

            # Buy (long) logic
            if action == 'buy':
                total_value = purchase_price * quantity
                if total_value <= current_balance:
                    new_balance = round(current_balance - total_value, 2)
                    cursor.execute("UPDATE users SET balance = ? WHERE username = ?", (new_balance, session['username']))
                    cursor.execute("INSERT INTO portfolio (user_id, asset_name, quantity, purchase_price, purchase_date, position_type) VALUES (?, ?, ?, ?, ?, 'long')",
                                   (session['user_id'], asset_name, quantity, purchase_price, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    conn.commit()
                    flash(f'Bought {quantity} shares of {asset_name} at ${purchase_price:.2f}')
                else:
                    flash('Not enough balance to make the purchase!')

            # Short sell logic
            elif action == 'short':
                margin_reserve = purchase_price * quantity * 0.3  # Reserving 30% margin
                if current_balance >= margin_reserve:
                    new_balance = round(current_balance - margin_reserve, 2)
                    cursor.execute("UPDATE users SET balance = ? WHERE username = ?", (new_balance, session['username']))
                    cursor.execute("INSERT INTO portfolio (user_id, asset_name, quantity, purchase_price, purchase_date, position_type) VALUES (?, ?, ?, ?, ?, 'short')",
                                   (session['user_id'], asset_name, quantity, purchase_price, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    conn.commit()
                    flash(f'Short sold {quantity} shares of {asset_name}. Reserved ${margin_reserve:.2f} as margin.')
                else:
                    flash(f'Not enough balance to short sell {asset_name}. Required margin: ${margin_reserve:.2f}')

        # Fetch user's current balance to display on trade page
        cursor.execute("SELECT balance FROM users WHERE username = ?", (session['username'],))
        balance = cursor.fetchone()[0]
        conn.close()

        return render_template('trade.html', balance=balance, graph_html=graph_html)

    return redirect('/login')





@app.route('/portfolio', methods=['GET', 'POST'])
def portfolio():
    if 'logged_in' in session and session['logged_in']:
        conn = sqlite3.connect('/Users/kyeraikundalia/Documents/GitHub/NEA/app.db')  # Update with your DB path
        cursor = conn.cursor()

        if request.method == 'POST':
            # Check if the close position request is submitted
            if 'close_position' in request.form:
                position_id = request.form['close_position']
                
                # Fetch the position details from the portfolio
                cursor.execute("SELECT asset_name, quantity, purchase_price, position_type FROM portfolio WHERE id = ?", (position_id,))
                position = cursor.fetchone()

                if position:
                    asset_name, quantity, purchase_price, position_type = position
                    live_price = round(yf.Ticker(asset_name).history(period='1d')['Close'][0], 2)

                    # Fetch user's current balance
                    cursor.execute("SELECT balance FROM users WHERE username = ?", (session['username'],))
                    current_balance = cursor.fetchone()[0]

                    # If the position is short, release margin and calculate profit/loss
                    if position_type == 'short':
                        # Margin reserved when shorting was 30%
                        margin_reserve = purchase_price * quantity * 0.3
                        profit_loss = round((purchase_price - live_price) * quantity, 2)

                        # Release margin back to the balance and apply profit/loss
                        new_balance = round(current_balance + margin_reserve + profit_loss, 2)
                        cursor.execute("UPDATE users SET balance = ? WHERE username = ?", (new_balance, session['username']))
                        flash(f'Short position closed with a {"profit" if profit_loss > 0 else "loss"} of ${profit_loss:.2f}. Margin released.')

                    # If the position is long, calculate profit/loss without margin
                    elif position_type == 'long':
                        total_value = purchase_price * quantity
                        profit_loss = round((live_price - purchase_price) * quantity, 3)
                        new_balance = round(current_balance + total_value + profit_loss, 3)
                        cursor.execute("UPDATE users SET balance = ? WHERE username = ?", (new_balance, session['username']))
                        flash(f'Long position closed with a {"profit" if profit_loss > 0 else "loss"} of ${profit_loss:.2f}.')

                    # Remove the closed position from the portfolio
                    cursor.execute("DELETE FROM portfolio WHERE id = ?", (position_id,))
                    conn.commit()

            # Reset portfolio balance logic
            elif 'reset_balance' in request.form:
                # Reset the user's balance to $100,000 (or the desired starting amount)
                cursor.execute("UPDATE users SET balance = 100000 WHERE username = ?", (session['username'],))
                
                # Remove all positions from the portfolio for this user
                cursor.execute("DELETE FROM portfolio WHERE user_id = (SELECT id FROM users WHERE username = ?)", (session['username'],))
                conn.commit()
                flash('Portfolio balance reset to $100,000.')

        # Fetch user's current portfolio
        cursor.execute("SELECT * FROM portfolio WHERE user_id = (SELECT id FROM users WHERE username = ?)", (session['username'],))
        positions = cursor.fetchall()

        # Fetch user's current balance
        cursor.execute("SELECT balance FROM users WHERE username = ?", (session['username'],))
        balance = cursor.fetchone()[0]

        # Fetch current prices and calculate profit/loss
        current_price = {}
        profit_loss = {}
        for position in positions:
            asset_name = position[2]
            quantity = position[3]
            purchase_price = position[4]
            position_type = position[6]
            
            try:
                live_price = round(yf.Ticker(asset_name).history(period='1d')['Close'][0], 2)
                current_price[asset_name] = live_price
                
                # Calculate profit/loss based on position type
                if position_type == 'long':
                    profit_loss[asset_name] = round((live_price - purchase_price) * quantity, 2)
                elif position_type == 'short':
                    profit_loss[asset_name] = round((purchase_price - live_price) * quantity, 2)
            except Exception as e:
                flash(f'Error fetching price for {asset_name}: {str(e)}')

        conn.close()

        return render_template('portfolio.html', positions=positions, balance=balance, current_price=current_price, profit_loss=profit_loss)

    return redirect('/login')

@app.route('/articles')
def articles():
    return render_template('articles.html')

@app.route('/glossary')
def glossary():
    return render_template('glossary.html')


if __name__ == '__main__':
    app.run(debug=True)
