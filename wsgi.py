from main import StockApp  # Import the StockApp class
import os

# Create an instance of StockApp
stock_app = StockApp()
stock_app.register_routes()  # Ensure routes are registered

app = stock_app.app  # Access the Flask instance

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 4000))  
    app.run(host="0.0.0.0", port=port)
