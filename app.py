from flask import Flask, render_template, request, redirect, url_for, session, flash
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime
from db import init_db, register_user, login_user, add_to_portfolio, get_portfolio, remove_from_portfolio
import os
from dotenv import load_dotenv

load_dotenv()
SECRET_KEY = os.getenv('SECRET_KEY')

app = Flask(__name__)
app.secret_key = SECRET_KEY  # Set a secret key for session management

# Initialize the database
with app.app_context():
    init_db()

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

# Function to determine if it's an uptrend or downtrend
def determine_trend(stock_data):
    if stock_data['SMA50'].iloc[-1] > stock_data['SMA200'].iloc[-1]:
        return "UPTREND"
    else:
        return "DOWNTREND"

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
@app.route('/', methods=['GET', 'POST'])
def index():
    ticker = 'MC.PA'  # Default ticker
    if request.method == 'POST':
        ticker = request.form.get('fname')
        if not ticker:
            ticker = 'MC.PA'
    
    stock_data = get_stock_data(ticker)  # Get stock data for the selected ticker
    image_data = plot_stock_data(stock_data)  # Generate plot image
    trend = determine_trend(stock_data)  # Determine trend (UPTREND or DOWNTREND)
    
    return render_template('index.html', image_data=image_data, ticker=ticker, trend=trend)

# Route for user registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        if register_user(username, email, password):
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Username or email already exists.', 'danger')
    return render_template('register.html')

# Route for user login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = login_user(username, password)
        if user:
            session['user_id'] = user['id']
            flash('Login successful!', 'success')
            return redirect(url_for('portfolio'))
        else:
            flash('Invalid credentials. Please try again.', 'danger')
    return render_template('login.html')

# Route to display the user's portfolio
@app.route('/portfolio')
def portfolio():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    portfolio = get_portfolio(user_id)  # Get user's portfolio
    return render_template('portfolio.html', portfolio=portfolio)

# Route to add a stock to the portfolio
@app.route('/portfolio/add', methods=['POST'])
def add_portfolio():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    ticker = request.form.get('ticker')
    if ticker:
        add_to_portfolio(user_id, ticker)
        flash(f'Stock {ticker} added to your portfolio.', 'success')

    return redirect(url_for('portfolio'))

# Route to remove a stock from the portfolio
@app.route('/portfolio/remove', methods=['POST'])
def remove_portfolio():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    ticker = request.form.get('ticker')
    if ticker:
        remove_from_portfolio(user_id, ticker)
        flash(f'Stock {ticker} removed from your portfolio.', 'success')

    return redirect(url_for('portfolio'))

# Route to log out
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
