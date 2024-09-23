from flask import Flask, render_template, request, redirect, url_for, session, flash
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime, timedelta
from db import init_db, register_user, login_user, add_to_portfolio, get_portfolio, remove_from_portfolio
from flask_mail import Mail, Message
import os
from dotenv import load_dotenv

load_dotenv()
SECRET_KEY = os.getenv('SECRET_KEY')

app = Flask(__name__)
app.secret_key = SECRET_KEY  # Set a secret key for session management

# Flask-Mail configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT'))
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False

# Initialize Flask-Mail
mail = Mail(app)

# Initialize the database
with app.app_context():
    init_db()

# Get today's date
end_date = datetime.now().strftime('%Y-%m-%d')

# Start date
start_date = '2020-01-01'

# Function to send an email
def send_email():
    msg = Message("Stock Analysis Update", sender=app.config['MAIL_USERNAME'], recipients=["wayne.ugo.lol@gmail.com"])
    msg.body = "Here is the latest stock analysis from your platform."
    mail.send(msg)

# Function to send email if there is a crossover and the stock is in the user's portfolio
def send_email_crossover(direction, ticker): #(user_id, direction, ticker):
    # Fetch the user's portfolio
    portfolio = get_portfolio(1) # Hardcoded user_id for now -> user wayne
    
    # Check if the ticker is in the portfolio
    portfolio_tickers = [stock['ticker'] for stock in portfolio]
    
    if ticker in portfolio_tickers:
        subject = f"{ticker}: 50-Day and 200-Day SMA Crossover"
        if direction == "upward":
            body = f"There has been an upward crossover of the 50-day SMA over the 200-day SMA for {ticker}."
        else:
            body = f"There has been a downward crossover of the 50-day SMA under the 200-day SMA for {ticker}."
        
        msg = Message(subject, sender=app.config['MAIL_USERNAME'], recipients=["wayne.ugo.lol@gmail.com"])
        msg.body = body
        mail.send(msg)
        print(f"Email sent for {ticker} crossover ({direction}) in user's portfolio")
    else:
        print(f"{ticker} is not in the user's portfolio. No email sent.")

def get_stock_data(ticker='MC.PA', user_id=None, timeframe='1mo'):
    end_date = datetime.now()

    # Fetch enough data for moving averages
    if timeframe == '1mo':
        # For short timeframes, fetch 1 year of data to ensure sufficient data for SMA calculations
        start_date = end_date - timedelta(weeks=46)
    elif timeframe == '3mo':
        start_date = end_date - timedelta(weeks=56)
    elif timeframe == '6mo':
        start_date = end_date - timedelta(weeks=66)
    elif timeframe == '1y':
        start_date = end_date - timedelta(weeks=94)
    elif timeframe == '5y':
        start_date = end_date - timedelta(weeks=5*52)
    else:
        start_date = '2020-01-01'  # Default for 'max'
    
    # Fetch stock data within the selected timeframe
    stock_data = yf.download(ticker, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
    
    # Recalculate the moving averages
    stock_data['SMA200'] = stock_data['Close'].rolling(window=200).mean()  # 200-day moving average
    stock_data['SMA50'] = stock_data['Close'].rolling(window=50).mean()    # 50-day moving average
    
    # Filter the data to the desired timeframe
    if timeframe in ['1mo', '3mo', '6mo', '1y']:
        stock_data = stock_data.loc[end_date - pd.DateOffset(weeks={'1mo': 4, '3mo': 12, '6mo': 24, '1y': 52}[timeframe]):]

    # Check for crossover
    stock_data['Crossover'] = stock_data['SMA50'] > stock_data['SMA200']
    
    # Send email notifications if there's a crossover
    if len(stock_data) >= 2:  # Ensure there's enough data to check crossover
        if (stock_data['Crossover'].iloc[-2] == False and stock_data['Crossover'].iloc[-1] == True):
            send_email_crossover(user_id, "upward", ticker)
        elif (stock_data['Crossover'].iloc[-2] == True and stock_data['Crossover'].iloc[-1] == False):
            send_email_crossover(user_id, "downward", ticker)

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

@app.route('/', methods=['GET', 'POST'])
def index():
    ticker = 'MC.PA'  # Default ticker
    timeframe = '1mo'  # Default timeframe

    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    
    if request.method == 'POST':
        if request.form.get('fname'):
            ticker = request.form.get('fname')
        if request.form.get('timeframe'):
            timeframe = request.form.get('timeframe')
        if request.form.get('send_email'):
            # Send the stock analysis email
            send_email()  # Adjust as needed to fetch relevant stock data
            flash('Email sent with the latest stock analysis!', 'success')
            return redirect(url_for('index'))  # Redirect to avoid resending on refresh
    
    # Fetch stock data for the selected ticker and timeframe
    stock_data = get_stock_data(ticker, user_id=user_id, timeframe=timeframe)
    image_data = plot_stock_data(stock_data)
    trend = determine_trend(stock_data)
    
    return render_template('index.html', image_data=image_data, ticker=ticker, trend=trend, timeframe=timeframe)



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
