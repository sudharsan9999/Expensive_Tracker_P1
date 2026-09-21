import os
import sys
import subprocess

def main():
    print("🚀 Starting Smart Expense Tracker Web Application...")
    
    # Check if database exists, initialize if not
    db_file = os.path.join(os.path.dirname(__file__), 'expense_tracker.db')
    if not os.path.exists(db_file):
        print("📦 Initializing database & seeding sample records...")
        from database import init_db
        init_db()

    print("🧠 Initializing ML Models (TF-IDF + Logistic Regression & Linear Regression)...")
    from database import get_db
    from ml_engine import init_ml_engine
    conn = get_db()
    init_ml_engine(conn)
    conn.close()

    print("🌐 Launching Flask Web Application on http://localhost:5000")
    from app import app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

if __name__ == '__main__':
    main()
