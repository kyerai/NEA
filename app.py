from flask import Flask, render_template, redirect, url_for, request, session, flash
import sqlite3
from datetime import datetime, timedelta
import yfinance as yf
import plotly.io as pio
import plotly.graph_objects as go
import random
import string

class StockApp:
    def __init__(self):
        self.app = Flask(__name__)
        self.app.secret_key = 'your_secret_key'  # Replace with your actual secret key
        self.db_path = '/Users/kyeraikundalia/Documents/GitHub/NEA/app.db'
        self.assets = {
            "Stocks": ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"],
            "ETFs": ["SPY", "IVV", "VOO", "QQQ"],
        }
        self.cache = {}  # Initialize a cache for stock data
        self.cache_timeout = timedelta(minutes=10)  # Set cache expiration time
        self.conn = None
        self.cursor = None

    def generate_salt(self, length=16):
        """Generate a random salt of specified length."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    def custom_hash(self, password, salt):
        """Custom hashing function using ASCII manipulation."""
        combined = password + salt
        hash_value = 0
        for char in combined:
            hash_value = (hash_value * 31 + ord(char)) % (10**9 + 7)  # Simple hashing logic
        return str(hash_value)

    def run(self):
        self.register_routes()
        self.app.run(debug=True)

    def register_routes(self):
        self.app.route('/')(self.index)
        self.app.route('/login', methods=['GET', 'POST'])(self.login)
        self.app.route('/signup', methods=['GET', 'POST'])(self.signup)
        self.app.route('/home')(self.home)
        self.app.route('/logout')(self.logout)
        self.app.route('/trade', methods=['GET', 'POST'])(self.trade)
        self.app.route('/portfolio', methods=['GET', 'POST'])(self.portfolio)
        self.app.route('/articles')(self.articles)
        self.app.route('/glossary')(self.glossary)

    def index(self):
        return render_template('index.html')

    def login(self):
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']

            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            self.cursor.execute("SELECT id, password, salt FROM users WHERE username = ?", (username,))
            user = self.cursor.fetchone()
            self.conn.close()

            if user:
                user_id, stored_hashed_password, salt = user
                print(f"Debug: Retrieved user - ID: {user_id}, Password: {stored_hashed_password}, Salt: {salt}")

                # Rehash the input password with the stored salt
                hashed_password = self.custom_hash(password, salt)
                print(f"Debug: Computed hash - {hashed_password}")

                if hashed_password == stored_hashed_password:
                    session['logged_in'] = True
                    session['username'] = username
                    session['user_id'] = user_id
                    return redirect(url_for('home'))
                else:
                    flash('Invalid username or password.')
                    print("Debug: Password mismatch.")
            else:
                flash('Invalid username or password.')
                print("Debug: User not found.")

        return render_template('login.html')

    def signup(self):
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']

            # Generate salt and hash the password
            salt = self.generate_salt()
            hashed_password = self.custom_hash(password, salt)
            print(f"Debug: Generated salt - {salt}")
            print(f"Debug: Hashed password - {hashed_password}")

            # Save username, hashed password, and salt to the database
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            self.cursor.execute("INSERT INTO users (username, password, salt, balance) VALUES (?, ?, ?, 100000)",
                                (username, hashed_password, salt))
            self.conn.commit()
            self.conn.close()

            flash('Signup successful. Please login.')
            return redirect(url_for('login'))
        
        return render_template('signup.html')

    def home(self):
        if 'logged_in' in session and session['logged_in']:
            return render_template('home.html')
        return redirect('/login')

    def logout(self):
        session.clear()
        return redirect('/login')

    def validate_stock_symbol(self, symbol):
        return symbol.isalnum() and 1 <= len(symbol) <= 5

    def fetch_stock_data(self, ticker, period):
        """Fetch stock data with caching mechanism."""
        current_time = datetime.now()

        # Check cache
        if ticker in self.cache:
            cached_data, timestamp = self.cache[ticker]
            if current_time - timestamp < self.cache_timeout:
                print(f"Cache hit for {ticker}")
                return cached_data

        # Fetch fresh data if not in cache or expired
        try:
            print(f"Fetching fresh data for {ticker}")
            stock = yf.Ticker(ticker)
            if period == '1d':
                data = stock.history(period="1d", interval="5m")
            elif period == '1w':
                data = stock.history(period="5d", interval="1h")
            elif period == '1m':
                data = stock.history(period="1mo", interval="1d")
            elif period == '1y':
                data = stock.history(period="1y", interval="1d")
            else:
                data = stock.history(period="1mo", interval="1d")  # default to 1 month

            # Update cache
            self.cache[ticker] = (data, current_time)
            return data

        except Exception as e:
            print(f"Error fetching data for {ticker}: {str(e)}")
            return None

    def create_plot(self, stock_data, chart_type):
        fig = go.Figure()
        if chart_type == 'candlestick':
            fig.add_trace(go.Candlestick(
                x=stock_data.index,
                open=stock_data['Open'],
                high=stock_data['High'],
                low=stock_data['Low'],
                close=stock_data['Close'],
                name='Candlestick'
            ))
        elif chart_type == 'line':
            fig.add_trace(go.Scatter(
                x=stock_data.index,
                y=stock_data['Close'],
                mode='lines',
                name='Line'
            ))
        fig.update_layout(title=f"{chart_type.capitalize()} Chart", xaxis_title="Date", yaxis_title="Price")
        return pio.to_html(fig, full_html=False)

    def trade(self):
        if 'logged_in' not in session:
            return redirect('/login')

        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

        graph_html = None
        company_info = {}
        asset_name = request.form.get('asset_name') if 'asset_name' in request.form else None
        timeframe = request.form.get('timeframe', '6mo')

        # Fetch user's balance
        self.cursor.execute("SELECT balance FROM users WHERE username = ?", (session['username'],))
        balance = self.cursor.fetchone()[0]

        # If search form is submitted, display stock info
        if 'search_stock' in request.form:
            try:
                stock_data = self.fetch_stock_data(asset_name, timeframe)
                if stock_data is not None:
                    company_info = {
                        'current_price': round(stock_data['Close'].iloc[-1], 2),
                        'market_cap': 'N/A',  # Add more details if needed
                        'pe_ratio': 'N/A',
                        'high_52_week': 'N/A',
                        'low_52_week': 'N/A',
                        'description': 'N/A'
                    }
                    graph_html = self.create_plot(stock_data, 'candlestick')
                else:
                    flash(f"Failed to fetch data for {asset_name}.")
            except Exception as e:
                flash(f"Error fetching data for {asset_name}: {str(e)}")

        # If trade form is submitted, execute trade
        elif 'action' in request.form:
            action = request.form.get('action')  # 'buy' or 'short'
            quantity = int(request.form.get('quantity', 0))
            stop_loss = float(request.form.get('stop_loss', 0))  # New stop-loss field
            take_profit = float(request.form.get('take_profit', 0))  # New take-profit field

            # Ensure asset name and quantity are valid
            if asset_name and quantity > 0:
                try:
                    stock_data = self.fetch_stock_data(asset_name, '1d')
                    if stock_data is not None:
                        current_price = round(stock_data['Close'].iloc[-1], 2)
                        total_cost = current_price * quantity

                        if action == 'buy' and total_cost <= balance:
                            new_balance = balance - total_cost
                            self.cursor.execute("UPDATE users SET balance = ? WHERE username = ?", (new_balance, session['username']))
                            self.cursor.execute("INSERT INTO portfolio (user_id, asset_name, quantity, purchase_price, position_type, stop_loss, take_profit) VALUES (?, ?, ?, ?, 'long', ?, ?)",
                                           (session['user_id'], asset_name, quantity, current_price, stop_loss, take_profit))
                            self.conn.commit()
                            flash(f"Bought {quantity} shares of {asset_name} at ${current_price:.2f}.")
                        elif action == 'short' and balance >= total_cost * 0.3:
                            margin_reserve = total_cost * 0.3
                            new_balance = balance - margin_reserve
                            self.cursor.execute("UPDATE users SET balance = ? WHERE username = ?", (new_balance, session['username']))
                            self.cursor.execute("INSERT INTO portfolio (user_id, asset_name, quantity, purchase_price, position_type, stop_loss, take_profit) VALUES (?, ?, ?, ?, 'short', ?, ?)",
                                           (session['user_id'], asset_name, quantity, current_price, stop_loss, take_profit))
                            self.conn.commit()
                            flash(f"Short sold {quantity} shares of {asset_name} at ${current_price:.2f}.")
                        else:
                            flash("Insufficient balance for this transaction.")
                    else:
                        flash(f"Failed to fetch current price for {asset_name}.")
                except Exception as e:
                    flash(f"Error executing trade for {asset_name}: {str(e)}")
            else:
                flash("Please enter a valid asset name and quantity.")

        self.conn.close()
        return render_template('trade.html', balance=round(balance, 2), graph_html=graph_html, company_info=company_info, asset_name=asset_name, timeframe=timeframe, assets=self.assets)

    def portfolio(self):
        if 'logged_in' not in session:
            return redirect('/login')

        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

        if request.method == 'POST':
            if 'close_position' in request.form:
                position_id = request.form['close_position']
                quantity_to_close = int(request.form.get('quantity_to_close', 0))
                self.cursor.execute("SELECT asset_name, quantity, purchase_price, position_type FROM portfolio WHERE id = ?", (position_id,))
                position = self.cursor.fetchone()

                if position:
                    asset_name, quantity, purchase_price, position_type = position
                    live_price = round(yf.Ticker(asset_name).history(period='1d')['Close'].iloc[-1], 2)
                    self.cursor.execute("SELECT balance FROM users WHERE username = ?", (session['username'],))
                    current_balance = self.cursor.fetchone()[0]

                    if quantity_to_close > 0 and quantity_to_close <= quantity:
                        if position_type == 'short':
                            margin_reserve = purchase_price * quantity_to_close * 0.3
                            profit_loss = round((purchase_price - live_price) * quantity_to_close, 2)
                            new_balance = round(current_balance + margin_reserve + profit_loss, 2)
                            self.cursor.execute("UPDATE users SET balance = ? WHERE username = ?", (new_balance, session['username']))
                            flash(f'Closed {quantity_to_close} of {asset_name} with a {"profit" if profit_loss > 0 else "loss"} of ${profit_loss:.2f}. Margin released.')

                        elif position_type == 'long':
                            total_value = purchase_price * quantity_to_close
                            profit_loss = round((live_price - purchase_price) * quantity_to_close, 3)
                            new_balance = round(current_balance + total_value + profit_loss, 3)
                            self.cursor.execute("UPDATE users SET balance = ? WHERE username = ?", (new_balance, session['username']))
                            flash(f'Closed {quantity_to_close} of {asset_name} with a {"profit" if profit_loss > 0 else "loss"} of ${profit_loss:.2f}.')

                        if quantity_to_close == quantity:
                            self.cursor.execute("DELETE FROM portfolio WHERE id = ?", (position_id,))
                        else:
                            new_quantity = quantity - quantity_to_close
                            self.cursor.execute("UPDATE portfolio SET quantity = ? WHERE id = ?", (new_quantity, position_id))

                        self.conn.commit()
                    else:
                        flash('Invalid quantity to close.')

            elif 'reset_balance' in request.form:
                self.cursor.execute("UPDATE users SET balance = 100000 WHERE username = ?", (session['username'],))
                self.cursor.execute("DELETE FROM portfolio WHERE user_id = (SELECT id FROM users WHERE username = ?)", (session['username'],))
                self.conn.commit()
                flash('Portfolio balance reset to $100,000.')

        self.cursor.execute("SELECT * FROM portfolio WHERE user_id = (SELECT id FROM users WHERE username = ?)", (session['username'],))
        positions = self.cursor.fetchall()
        self.cursor.execute("SELECT balance FROM users WHERE username = ?", (session['username'],))
        balance = self.cursor.fetchone()[0]

        current_price = {}
        profit_loss = {}
        for position in positions:
            asset_name = position[2]
            quantity = position[3]
            purchase_price = position[4]
            position_type = position[6]
            
            try:
                live_price = round(yf.Ticker(asset_name).history(period='1d')['Close'].iloc[-1], 2)
                current_price[asset_name] = live_price
                
                if position_type == 'long':
                    profit_loss[asset_name] = round((live_price - purchase_price) * quantity, 2)
                elif position_type == 'short':
                    profit_loss[asset_name] = round((purchase_price - live_price) * quantity, 2)
            except Exception as e:
                flash(f'Error fetching price for {asset_name}: {str(e)}')

        self.conn.close()
        return render_template('portfolio.html', positions=positions, balance=round(balance, 2), current_price=current_price, profit_loss=profit_loss)

    def articles(self):
        return render_template('articles.html')

    def glossary(self):
        return render_template('glossary.html')

if __name__ == '__main__':
    stock_app = StockApp()
    stock_app.run()
