from flask import Flask, render_template
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime

app = Flask(__name__)

# Get today's date
end_date = datetime.now().strftime('%Y-%m-%d')

# Start date
start_date = '2020-01-01'

# Function to fetch and analyze stock data
def get_stock_data(ticker='MC.PA'):
    stock_data = yf.download(ticker, start=start_date, end=end_date)
    stock_data['SMA200'] = stock_data['Close'].rolling(window=200).mean()  # 200-day moving average
    stock_data['SMA50'] = stock_data['Close'].rolling(window=50).mean()    # 50-day moving average
    return stock_data

# Function to plot stock data and return it as an image
def plot_stock_data(stock_data):
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(stock_data['Close'], label='Close Price', color='blue')
    ax.plot(stock_data['SMA200'], label='200-Day SMA', color='orange')  # Plot 200-day moving average
    ax.plot(stock_data['SMA50'], label='50-Day SMA', color='green')      # Plot 50-day moving average
    ax.set_title('Stock Price with 200-Day and 50-Day Moving Averages')
    ax.set_xlabel('Date')
    ax.set_ylabel('Price (USD)')
    ax.legend()
    plt.xticks(rotation=45)  # Rotate x-axis labels for better readability

    # Save plot to a string buffer in memory
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches='tight')
    buf.seek(0)
    # Encode the image to base64 string
    image_data = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()

    return image_data

# Flask route for the main page
@app.route('/')
def index():
    stock_data = get_stock_data()  # Get stock data
    image_data = plot_stock_data(stock_data)  # Generate plot image
    return render_template('index.html', image_data=image_data)

if __name__ == '__main__':
    app.run(debug=True)
