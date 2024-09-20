import sqlite3
from flask import g
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE = 'app.db'

# Function to get a database connection
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row  # Allows accessing columns by name
    return db

# Function to initialize the database
def init_db():
    db = get_db()
    with db:
        # Create stocks table if it doesn't exist
        db.execute('''
            CREATE TABLE IF NOT EXISTS stocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                date TEXT NOT NULL,
                close_price REAL NOT NULL,
                sma50 REAL,
                sma200 REAL
            )
        ''')

        # Create users table if it doesn't exist
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create portfolio table to track user-specific stocks
        db.execute('''
            CREATE TABLE IF NOT EXISTS portfolio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

# Function to close the database connection
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Function to register a new user
def register_user(username, email, password):
    db = get_db()
    hashed_password = generate_password_hash(password)
    try:
        db.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username, email, hashed_password)
        )
        db.commit()
        return True
    except sqlite3.IntegrityError:
        # This will handle duplicate entries for username or email
        return False

# Function to verify login credentials
def login_user(username, password):
    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    
    if user and check_password_hash(user['password'], password):
        return user
    return None

# Function to add a stock to a user's portfolio
def add_to_portfolio(user_id, ticker):
    db = get_db()
    db.execute(
        "INSERT INTO portfolio (user_id, ticker) VALUES (?, ?)", 
        (user_id, ticker)
    )
    db.commit()

# Function to get a user's portfolio
def get_portfolio(user_id):
    db = get_db()
    portfolio = db.execute(
        "SELECT ticker, added_at FROM portfolio WHERE user_id = ?",
        (user_id,)
    ).fetchall()
    return portfolio

# Function to remove a stock from a user's portfolio
def remove_from_portfolio(user_id, ticker):
    db = get_db()
    db.execute(
        "DELETE FROM portfolio WHERE user_id = ? AND ticker = ?", 
        (user_id, ticker)
    )
    db.commit()

# Example teardown function to close the database when the app context ends
def teardown_db(exception):
    close_connection(exception)
