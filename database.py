import sqlite3
import os
import datetime
from datetime import timedelta
import random

from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), 'expense_tracker.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT DEFAULT '',
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        address TEXT DEFAULT '',
        monthly_budget REAL DEFAULT 2500.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Migration check for existing DBs: check if 'name' or 'address' columns exist
    cursor.execute("PRAGMA table_info(users)")
    columns = [row['name'] for row in cursor.fetchall()]
    if 'name' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN name TEXT DEFAULT ''")
    if 'address' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN address TEXT DEFAULT ''")

    # Categories table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        icon TEXT DEFAULT 'fa-tag',
        color TEXT DEFAULT '#4F46E5'
    )
    ''')

    # Expenses table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        date TEXT NOT NULL,
        payment_method TEXT DEFAULT 'Card',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')

    conn.commit()

    # Seed default categories
    seed_categories = [
        ('Food & Dining', 'fa-utensils', '#EF4444'),
        ('Transportation', 'fa-car', '#F59E0B'),
        ('Bills & Utilities', 'fa-file-invoice-dollar', '#10B981'),
        ('Shopping', 'fa-shopping-bag', '#EC4899'),
        ('Entertainment', 'fa-film', '#8B5CF6'),
        ('Health & Fitness', 'fa-heartbeat', '#06B6D4'),
        ('Education', 'fa-graduation-cap', '#3B82F6'),
        ('Travel & Vacation', 'fa-plane', '#6366F1'),
        ('Investments', 'fa-chart-line', '#10B981'),
        ('Miscellaneous', 'fa-ellipsis-h', '#6B7280')
    ]

    cursor.executemany('''
    INSERT OR IGNORE INTO categories (name, icon, color) VALUES (?, ?, ?)
    ''', seed_categories)

    # Seed default demo user if not exists
    cursor.execute("SELECT id FROM users WHERE username = 'demo'")
    user = cursor.fetchone()
    demo_pass_hash = generate_password_hash('demo123')
    if not user:
        cursor.execute('''
        INSERT INTO users (name, username, email, password_hash, address, monthly_budget)
        VALUES ('Demo User', 'demo', 'demo@expensetracker.com', ?, '123 Tech Park, Silicon Valley, CA', 2500.0)
        ''', (demo_pass_hash,))
        user_id = cursor.lastrowid
    else:
        user_id = user['id']
        cursor.execute('''
        UPDATE users SET name = COALESCE(NULLIF(name, ''), 'Demo User'),
                          address = COALESCE(NULLIF(address, ''), '123 Tech Park, Silicon Valley, CA')
        WHERE id = ?
        ''', (user_id,))

    # Check if expenses exist, if not seed rich demo expenses (past 6 months)
    cursor.execute("SELECT COUNT(*) as count FROM expenses WHERE user_id = ?", (user_id,))
    count = cursor.fetchone()['count']
    if count == 0:
        seed_sample_expenses(cursor, user_id)

    conn.commit()
    conn.close()

def seed_sample_expenses(cursor, user_id):
    today = datetime.date.today()
    
    sample_data = [
        # Food & Dining
        ("Pizza Hut dinner with friends", 42.50, "Food & Dining", "Credit Card"),
        ("Starbucks caramel macchiato and pastry", 12.80, "Food & Dining", "UPI"),
        ("Walmart grocery shopping - vegetables & milk", 85.30, "Food & Dining", "Debit Card"),
        ("McDonalds burger combo lunch", 14.20, "Food & Dining", "Cash"),
        ("Subway veggie delight sandwich", 9.50, "Food & Dining", "UPI"),
        ("Organic groceries at Whole Foods", 112.40, "Food & Dining", "Credit Card"),
        ("Dominos pepperonis pizza delivery", 28.90, "Food & Dining", "UPI"),
        ("Chipotle burrito bowl and guac", 16.75, "Food & Dining", "Debit Card"),
        ("Diner breakfast - eggs and pancakes", 22.00, "Food & Dining", "Cash"),
        ("Sushi bar dinner buffet", 65.00, "Food & Dining", "Credit Card"),
        ("Local bakery sourdough bread and donuts", 15.60, "Food & Dining", "UPI"),
        ("KFC fried chicken bucket", 31.20, "Food & Dining", "Debit Card"),
        
        # Transportation
        ("Uber ride to international airport", 38.50, "Transportation", "Credit Card"),
        ("Gasoline refill at Shell station", 45.00, "Transportation", "Debit Card"),
        ("Monthly metro subway pass renewal", 80.00, "Transportation", "UPI"),
        ("Lyft ride home from downtown", 24.10, "Transportation", "Credit Card"),
        ("Car oil change and tire rotation service", 120.00, "Transportation", "Debit Card"),
        ("City parking meter fee for 4 hours", 12.00, "Transportation", "Cash"),
        ("Highway expressway toll gate payment", 8.50, "Transportation", "UPI"),
        ("Auto insurance monthly premium", 115.00, "Transportation", "Credit Card"),

        # Bills & Utilities
        ("Electric power utility bill payment", 94.20, "Bills & Utilities", "UPI"),
        ("High speed fiber internet monthly bill", 65.00, "Bills & Utilities", "Credit Card"),
        ("Cell phone post-paid mobile plan", 55.00, "Bills & Utilities", "Debit Card"),
        ("City water & sewage municipal bill", 42.10, "Bills & Utilities", "UPI"),
        ("Natural gas heating bill", 38.40, "Bills & Utilities", "Credit Card"),
        ("Apartment monthly maintenance fee", 150.00, "Bills & Utilities", "Debit Card"),

        # Shopping
        ("Amazon electronics order - USB Hub & Cable", 34.99, "Shopping", "Credit Card"),
        ("Zara winter jacket and blue jeans", 129.50, "Shopping", "Credit Card"),
        ("Nike running shoes on discount", 89.90, "Shopping", "Debit Card"),
        ("IKEA desk lamp and bookshelf organizer", 74.00, "Shopping", "Credit Card"),
        ("Sephora skincare moisturizers and cosmetics", 62.30, "Shopping", "UPI"),
        ("Apple store iPhone leather case", 49.00, "Shopping", "Credit Card"),

        # Entertainment
        ("Netflix monthly 4K streaming subscription", 19.99, "Entertainment", "Credit Card"),
        ("Spotify Premium music subscription", 10.99, "Entertainment", "Debit Card"),
        ("IMAX Cinema movie tickets & popcorn", 36.50, "Entertainment", "UPI"),
        ("Steam summer game sale purchase", 45.00, "Entertainment", "Credit Card"),
        ("Concert music festival ticket booking", 110.00, "Entertainment", "Credit Card"),
        ("PlayStation Plus online membership", 14.99, "Entertainment", "Debit Card"),

        # Health & Fitness
        ("Gym membership monthly dues", 50.00, "Health & Fitness", "Credit Card"),
        ("CVS Pharmacy prescription medicine & vitamins", 38.40, "Health & Fitness", "Debit Card"),
        ("Dental checkup & cleaning consultation", 90.00, "Health & Fitness", "Credit Card"),
        ("Protein powder supplement jar", 54.99, "Health & Fitness", "UPI"),
        ("Eye doctor vision clinic exam fee", 65.00, "Health & Fitness", "Credit Card"),

        # Education
        ("Udemy Python machine learning online course", 16.99, "Education", "Credit Card"),
        ("Coursera Data Science specialization subscription", 49.00, "Education", "Debit Card"),
        ("Barnes & Noble technical programming books", 58.20, "Education", "Credit Card"),

        # Travel & Vacation
        ("Airbnb cabin booking for weekend getaway", 280.00, "Travel & Vacation", "Credit Card"),
        ("Delta airlines round-trip domestic flight", 340.00, "Travel & Vacation", "Credit Card"),

        # Investments
        ("Monthly index fund SIP investment", 250.00, "Investments", "Bank Transfer"),
        ("Stocks buy order - S&P 500 ETF", 200.00, "Investments", "Bank Transfer"),

        # Miscellaneous
        ("Dry cleaning suit & coat service", 25.00, "Miscellaneous", "Cash"),
        ("Hardware store repair tools & screws", 18.40, "Miscellaneous", "UPI")
    ]

    # Generate records spread over the past 5 months up to today
    for month_offset in range(5, -1, -1):
        # Determine month target date
        target_month_date = today - timedelta(days=30 * month_offset)
        # Choose 12-18 random items per month to create realistic time series trend
        num_items = random.randint(12, 18)
        selected_samples = random.sample(sample_data, min(num_items, len(sample_data)))
        
        for desc, base_amt, cat, method in selected_samples:
            # Vary amount slightly for realism
            amt = round(base_amt * random.uniform(0.85, 1.15), 2)
            # Random day in that month
            day = random.randint(1, 28)
            try:
                date_str = target_month_date.replace(day=day).strftime('%Y-%m-%d')
            except ValueError:
                date_str = target_month_date.strftime('%Y-%m-%d')
                
            cursor.execute('''
            INSERT INTO expenses (user_id, description, amount, category, date, payment_method)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, desc, amt, cat, date_str, method))

if __name__ == '__main__':
    init_db()
    print("Database initialized and seeded successfully.")
