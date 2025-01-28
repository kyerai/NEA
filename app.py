from flask import Flask, render_template, redirect, url_for, request, session, flash
import sqlite3
from datetime import datetime, timedelta
import yfinance as yf
import plotly.io as pio
import plotly.graph_objects as go
import threading
import random
import string
import time

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

        # Start background monitoring thread
        self.start_price_monitoring()

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
        self.app.route('/glossary', methods=['GET', 'POST'])(self.glossary)

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

    def monitor_positions(self):
        """Monitor active positions for stop-loss and take-profit execution."""
        while True:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()

            # Fetch all active positions
            self.cursor.execute("SELECT id, asset_name, quantity, purchase_price, stop_loss, take_profit, position_type, user_id FROM portfolio")
            positions = self.cursor.fetchall()

            for position in positions:
                position_id, asset_name, quantity, purchase_price, stop_loss, take_profit, position_type, user_id = position
                try:
                    # Fetch current price
                    stock_data = self.fetch_stock_data(asset_name, '1d')
                    if stock_data is not None:
                        current_price = round(stock_data['Close'].iloc[-1], 2)

                        if stop_loss is not None and current_price <= stop_loss:
                            self.execute_trade(position_id, current_price, quantity, user_id, "Stop-loss triggered")
                            continue

                        if take_profit is not None and current_price >= take_profit:
                            self.execute_trade(position_id, current_price, quantity, user_id, "Take-profit triggered")
                            continue

                except Exception as e:
                    print(f"Error monitoring position {position_id} for {asset_name}: {str(e)}")

            self.conn.close()
            time.sleep(60)  # Wait for 1 minute before checking again

    def execute_trade(self, position_id, current_price, quantity, user_id, reason):
        """Execute trade by closing position and updating balance."""
        self.cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
        current_balance = self.cursor.fetchone()[0]

        # Fetch position details
        self.cursor.execute("SELECT purchase_price, position_type FROM portfolio WHERE id = ?", (position_id,))
        purchase_price, position_type = self.cursor.fetchone()

        # Calculate profit or loss
        if position_type == 'long':
            profit_loss = round((current_price - purchase_price) * quantity, 2)
        elif position_type == 'short':
            profit_loss = round((purchase_price - current_price) * quantity, 2)

        # Update balance
        new_balance = current_balance + profit_loss
        self.cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, user_id))

        # Delete the position
        self.cursor.execute("DELETE FROM portfolio WHERE id = ?", (position_id,))
        self.conn.commit()

        print(f"{reason}: Closed position {position_id} with P/L: ${profit_loss:.2f}")

    def start_price_monitoring(self):
        """Start a background thread for monitoring prices."""
        monitoring_thread = threading.Thread(target=self.monitor_positions, daemon=True)
        monitoring_thread.start()

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
            print("User not logged in; redirecting to login page.")
            return redirect('/login')

        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

        graph_html = None
        company_info = {}

        # Explicitly prioritize form data for asset_name
        asset_name = request.form.get('asset_name') or request.args.get('asset_name', '').strip()
        timeframe = request.args.get('timeframe') or request.form.get('timeframe', '6mo')

        # Prevent redirect loops if asset_name is missing and no trade or search actions
        if not asset_name and 'search_stock' not in request.form and 'tradesubmitted' not in request.form:
            flash("Asset name is missing. Please select or enter a valid asset name.")
            return render_template(
                'trade.html',
                balance=0,  # Default balance if it cannot be fetched
                graph_html=None,
                company_info={},
                asset_name=None,
                timeframe=timeframe,
                assets=self.assets
            )

        # Fetch user's balance
        try:
            self.cursor.execute("SELECT balance FROM users WHERE username = ?", (session['username'],))
            balance = self.cursor.fetchone()[0]
        except Exception as e:
            flash("Error fetching user balance.")
            print(f"Error: {e}")
            return redirect('/login')

        # Handle graph and company overview for asset_name from sidebar
        if asset_name and 'search_stock' not in request.form and 'tradesubmitted' not in request.form:
            try:
                stock_data = self.fetch_stock_data(asset_name, timeframe)
                if stock_data is not None:
                    stock_info = yf.Ticker(asset_name)
                    company_info = {
                        'current_price': round(stock_data['Close'].iloc[-1], 2),
                        'market_cap': stock_info.info.get('marketCap', 'N/A'),
                        'pe_ratio': stock_info.info.get('trailingPE', 'N/A'),
                        'high_52_week': stock_info.info.get('fiftyTwoWeekHigh', 'N/A'),
                        'low_52_week': stock_info.info.get('fiftyTwoWeekLow', 'N/A'),
                        'div_yield': stock_info.info.get('dividendYield', 'N/A')
                    }
                    graph_html = self.create_plot(stock_data, 'candlestick')
                else:
                    flash(f"Failed to fetch data for {asset_name}.")
            except Exception as e:
                flash(f"Error fetching data for {asset_name}: {str(e)}")

        # If search form is submitted, display stock info
        if 'search_stock' in request.form:
            try:
                stock_data = self.fetch_stock_data(asset_name, timeframe)
                if stock_data is not None:
                    stock_info = yf.Ticker(asset_name)
                    stock_data = stock_info.history(period=timeframe)

                    company_info = {
                        'current_price': round(stock_data['Close'].iloc[-1], 2),
                        'market_cap': stock_info.info.get('marketCap', 'N/A'),
                        'pe_ratio': stock_info.info.get('trailingPE', 'N/A'),
                        'high_52_week': stock_info.info.get('fiftyTwoWeekHigh', 'N/A'),
                        'low_52_week': stock_info.info.get('fiftyTwoWeekLow', 'N/A'),
                        'div_yield': stock_info.info.get('dividendYield', 'N/A')
                    }
                    graph_html = self.create_plot(stock_data, 'candlestick')
                else:
                    flash(f"Failed to fetch data for {asset_name}.")
            except Exception as e:
                flash(f"Error fetching data for {asset_name}: {str(e)}")

        # If trade form is submitted, execute trade
        elif 'tradesubmitted' in request.form:
            action = request.form.get('tradesubmitted')  # 'buy' or 'short'
            quantity = int(request.form.get('quantity', 0))
            stop_loss = request.form.get('stop_loss', '').strip()
            take_profit = request.form.get('take_profit', '').strip()

            # Validate and convert stop_loss and take_profit
            stop_loss = float(stop_loss) if stop_loss else None
            take_profit = float(take_profit) if take_profit else None

            if quantity <= 0:
                flash("Quantity must be greater than zero.")
                return redirect('/trade')

            try:
                # Fetch the exact current price right before placing the trade
                stock_data = self.fetch_stock_data(asset_name, '1d')
                if stock_data is not None:
                    current_price = round(stock_data['Close'].iloc[-1], 2)
                    total_cost = current_price * quantity

                    if action == 'buy' and total_cost <= balance:
                        new_balance = balance - total_cost
                        self.cursor.execute("UPDATE users SET balance = ? WHERE username = ?", (new_balance, session['username']))
                        self.cursor.execute(
                            "INSERT INTO portfolio (user_id, asset_name, quantity, purchase_price, position_type, stop_loss, take_profit) VALUES (?, ?, ?, ?, 'long', ?, ?)",
                            (session['user_id'], asset_name, quantity, current_price, stop_loss, take_profit)
                        )
                        self.conn.commit()
                        flash(f"Bought {quantity} shares of {asset_name} at ${current_price:.2f}.")
                    elif action == 'short' and balance >= total_cost * 0.3:
                        margin_reserve = total_cost * 0.3
                        new_balance = balance - margin_reserve
                        self.cursor.execute("UPDATE users SET balance = ? WHERE username = ?", (new_balance, session['username']))
                        self.cursor.execute(
                            "INSERT INTO portfolio (user_id, asset_name, quantity, purchase_price, position_type, stop_loss, take_profit) VALUES (?, ?, ?, ?, 'short', ?, ?)",
                            (session['user_id'], asset_name, quantity, current_price, stop_loss, take_profit)
                        )
                        self.conn.commit()
                        flash(f"Short sold {quantity} shares of {asset_name} at ${current_price:.2f}.")
                    else:
                        flash("Insufficient balance for this transaction.")
                else:
                    flash(f"Failed to fetch current price for {asset_name}.")
            except Exception as e:
                flash(f"Error executing trade for {asset_name}: {str(e)}")

        self.conn.close()
        return render_template(
            'trade.html',
            balance=round(balance, 2),
            graph_html=graph_html,
            company_info=company_info,
            asset_name=asset_name,
            timeframe=timeframe,
            assets=self.assets
        )



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
        price_change = {}
        market_value = {}
        profit_loss = {}

        for position in positions:
            asset_name = position[2]
            quantity = position[3]
            purchase_price = position[4]
            position_type = position[6]
            
            try:
                live_price = round(yf.Ticker(asset_name).history(period='1d')['Close'].iloc[-1], 2)
                current_price[asset_name] = live_price

                price_change[asset_name] = round(live_price - purchase_price, 2)
                market_value[asset_name] = round(live_price * quantity, 2)

                if position_type == 'long':
                    profit_loss[asset_name] = round((live_price - purchase_price) * quantity, 2)
                elif position_type == 'short':
                    profit_loss[asset_name] = round((purchase_price - live_price) * quantity, 2)
            except Exception as e:
                flash(f'Error fetching price for {asset_name}: {str(e)}')

        self.conn.close()
        return render_template('portfolio.html', 
                            positions=positions, 
                            balance=round(balance, 2), 
                            current_price=current_price, 
                            price_change=price_change, 
                            market_value=market_value, 
                            profit_loss=profit_loss)


    def articles(self):
        articles = [
            {
                'title': 'Introduction to Stocks',
                'content': 'Stocks represent ownership in a company. They are a way for companies to raise capital...',
                'author': 'Author Name',
                'date': '2025-01-27'
            },
            {
                'title': 'Understanding Dividends',
                'content': 'Dividends are payments made by companies to their shareholders as a share of profits...',
                'author': 'Author Name',
                'date': '2025-01-26'
            },
            {
                'title': 'An Overview of ETFs',
                'content': 'Exchange-traded funds (ETFs) are a type of investment fund and exchange-traded product...',
                'author': 'Author Name',
                'date': '2025-01-25'
            },
            {
                'title': 'Introduction to Bonds',
                'content': 'Bonds are fixed-income investments that represent a loan made by an investor to a borrower...',
                'author': 'Author Name',
                'date': '2025-01-24'
            },
            {
                'title': 'Stock Market Volatility',
                'content': 'Volatility is a statistical measure of the dispersion of returns for a given security or market index...',
                'author': 'Author Name',
                'date': '2025-01-23'
            },
            {
                'title': 'Understanding Market Capitalization',
                'content': 'Market capitalization is the total value of a company’s outstanding shares of stock...',
                'author': 'Author Name',
                'date': '2025-01-22'
            },
            {
                'title': 'Introduction to Technical Analysis',
                'content': 'Technical analysis is a method of evaluating securities by analyzing statistics generated by market activity...',
                'author': 'Author Name',
                'date': '2025-01-21'
            },
            {
                'title': 'Fundamental Analysis Explained',
                'content': 'Fundamental analysis is a method of evaluating a security by attempting to measure its intrinsic value...',
                'author': 'Author Name',
                'date': '2025-01-20'
            },
            {
                'title': 'An Overview of Options Trading',
                'content': 'Options trading involves buying and selling options contracts on the stock market...',
                'author': 'Author Name',
                'date': '2025-01-19'
            },
            {
                'title': 'Introduction to Forex Trading',
                'content': 'Forex trading, also known as foreign exchange trading or currency trading, involves buying and selling...',
                'author': 'Author Name',
                'date': '2025-01-18'
            }
        ]

        return render_template('articles.html', articles=articles)

    def glossary(self):
        terms = {
            'stock': 'A stock is a type of investment that represents ownership in a company.',
            'bond': 'A bond is a fixed-income investment that represents a loan made by an investor to a borrower.',
            'dividend': 'A dividend is the distribution of some of a company’s earnings to a class of its shareholders.',
            'ETF': 'An exchange-traded fund (ETF) is a type of investment fund and exchange-traded product, with shares that trade like a stock on an exchange.',
            'portfolio': 'A portfolio is a collection of financial investments like stocks, bonds, commodities, cash, and cash equivalents.',
            'volatility': 'Volatility is a statistical measure of the dispersion of returns for a given security or market index.',
            'liquidity': 'Liquidity refers to how easily an asset or security can be bought or sold in the market without affecting the asset’s price.',
            'market_cap': 'Market capitalization is the total value of a company’s outstanding shares of stock, calculated by multiplying the current share price by the total number of shares outstanding.',
            'PE_ratio': 'The price-to-earnings (P/E) ratio is a valuation ratio that shows how much investors are willing to pay per dollar of a company’s earnings.',
            'dividend_yield': 'Dividend yield is a financial ratio that shows how much a company pays out in dividends each year relative to its stock price.',
            'short_selling': 'Short selling is a trading strategy that involves borrowing shares of a security and selling them in the market with the hope of buying them back at a lower price.',
            'margin_call': 'A margin call is a broker’s demand for an investor to deposit additional money or securities to cover possible losses.',
            'stop_loss': 'A stop-loss order is an order placed with a broker to buy or sell a security when it reaches a certain price.',
            'take_profit': 'A take-profit order is a type of limit order that specifies the exact price at which to close out an open position for a profit.',
            'long_position': 'A long position is the buying of a security such as a stock, commodity, or currency with the expectation that the asset will rise in value.',
            'short_position': 'A short position is the sale of a borrowed security, commodity, or currency with the expectation that the asset will fall in value.',
            'market_order': 'A market order is an order to buy or sell a security immediately at the best available current price.',
            'limit_order': 'A limit order is an order to buy or sell a security at a specific price or better.',
            'day_trading': 'Day trading is a trading strategy that involves buying and selling financial instruments within the same trading day.',
            'swing_trading': 'Swing trading is a trading strategy that involves holding positions for longer than a day, but shorter than weeks or months.',
            'scalping': 'Scalping is a trading strategy that involves making small profits from small price changes in a security.',
            'technical_analysis': 'Technical analysis is a method of evaluating securities by analyzing statistics generated by market activity, such as past prices and volume.',
            'fundamental_analysis': 'Fundamental analysis is a method of evaluating a security by attempting to measure its intrinsic value by examining related economic, financial, and other qualitative and quantitative factors.',
            'moving_average': 'A moving average is a widely used indicator in technical analysis that helps smooth out past price data to create a trend-following indicator.',
            'RSI': 'The Relative Strength Index (RSI) is a momentum oscillator that measures the speed and change of price movements.',
            'MACD': 'The Moving Average Convergence Divergence (MACD) is a trend-following momentum indicator that shows the relationship between two moving averages of a security’s price.',
            'support_resistance': 'Support and resistance are price levels where a stock often reverses direction, marked by previous highs and lows.',
            'volatility_index': 'A volatility index is a measure of market expectations of near-term volatility conveyed by stock index option prices.',
            'beta': 'Beta is a measure of a stock’s volatility in relation to the overall market.',
            'alpha': 'Alpha is a measure of an investment’s performance compared to a benchmark index, typically the S&P 500.',
            'gamma': 'Gamma is a measure of how fast an option’s delta changes with respect to the underlying asset’s price.',
            'delta': 'Delta is a measure of how much the price of an option changes when the price of the underlying asset changes.',
            'theta': 'Theta is a measure of the rate of decline in the value of an option over time.',
            'vega': 'Vega is a measure of the sensitivity of an option’s price to changes in implied volatility.',
            'implied_volatility': 'Implied volatility is a measure of the market’s expectation of future volatility of the underlying asset, as implied by the prices of options.',
            'liquidity_ratio': 'The liquidity ratio is a financial metric that measures a company’s ability to pay off its short-term debts with its liquid assets.',
            'current_ratio': 'The current ratio is a financial metric that measures a company’s ability to pay off its short-term liabilities with its short-term assets.',
        }

        search_query = request.form.get('search', '').strip().lower()
        results = []

        if search_query:
            # Perform a partial match against term names only
            results = {
                term: definition
                for term, definition in terms.items()
                if search_query in term.lower()
            }

        return render_template('glossary.html', results=results, search_query=search_query)

if __name__ == '__main__':
    stock_app = StockApp()
    stock_app.run()
