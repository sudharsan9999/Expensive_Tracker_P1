from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
import sqlite3
import datetime
import io
import csv
import os

from werkzeug.security import generate_password_hash, check_password_hash

from database import get_db, init_db
from ml_engine import category_classifier, budget_predictor, init_ml_engine

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# Ensure database and ML engine are initialized on startup
with app.app_context():
    init_db()
    conn = get_db()
    init_ml_engine(conn)
    conn.close()

# Serves Frontend Single Page App
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

# ----------------------------
# 1. CATEGORY API
# ----------------------------
@app.route('/api/categories', methods=['GET'])
def get_categories():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, icon, color FROM categories ORDER BY name ASC")
    categories = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({"status": "success", "categories": categories})


# ----------------------------
# 2. EXPENSE CRUD API
# ----------------------------
@app.route('/api/expenses', methods=['GET'])
def get_expenses():
    user_id = request.args.get('user_id', 1, type=int)
    category = request.args.get('category', '', type=str)
    search = request.args.get('search', '', type=str)
    start_date = request.args.get('start_date', '', type=str)
    end_date = request.args.get('end_date', '', type=str)

    query = "SELECT e.*, c.icon, c.color FROM expenses e LEFT JOIN categories c ON e.category = c.name WHERE e.user_id = ?"
    params = [user_id]

    if category and category != 'All':
        query += " AND e.category = ?"
        params.append(category)

    if search:
        query += " AND (e.description LIKE ? OR e.category LIKE ?)"
        params.append(f"%{search}%")
        params.append(f"%{search}%")

    if start_date:
        query += " AND e.date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND e.date <= ?"
        params.append(end_date)

    query += " ORDER BY e.date DESC, e.id DESC"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(query, params)
    expenses = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return jsonify({"status": "success", "count": len(expenses), "expenses": expenses})


@app.route('/api/expenses', methods=['POST'])
def add_expense():
    data = request.json or {}
    description = data.get('description', '').strip()
    amount = data.get('amount')
    category = data.get('category', '').strip()
    date_str = data.get('date', datetime.date.today().strftime('%Y-%m-%d'))
    payment_method = data.get('payment_method', 'Card')
    user_id = data.get('user_id', 1)

    if not description or amount is None or not category:
        return jsonify({"status": "error", "message": "Description, amount, and category are required."}), 400

    try:
        amount = float(amount)
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid amount number."}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO expenses (user_id, description, amount, category, date, payment_method)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, description, amount, category, date_str, payment_method))
    
    expense_id = cursor.lastrowid
    conn.commit()

    # Retrain ML model periodically or asynchronously with newly logged data
    try:
        category_classifier.load_or_train(conn)
    except Exception as e:
        print(f"ML retrain on insert notice: {e}")

    conn.close()

    return jsonify({"status": "success", "message": "Expense added successfully", "expense_id": expense_id}), 201


@app.route('/api/expenses/upload', methods=['POST'])
def upload_expenses_csv():
    user_id = request.form.get('user_id', request.args.get('user_id', 1), type=int)
    auto_categorize = request.form.get('auto_categorize', 'true').lower() in ['true', '1', 'yes']

    file_content = ""
    if 'file' in request.files:
        uploaded_file = request.files['file']
        if uploaded_file.filename == '':
            return jsonify({"status": "error", "message": "No file selected."}), 400
        try:
            file_content = uploaded_file.read().decode('utf-8-sig', errors='replace')
        except Exception as e:
            return jsonify({"status": "error", "message": f"Could not read uploaded file: {str(e)}"}), 400
    elif request.is_json:
        # Fallback JSON batch import support
        data = request.json
        if isinstance(data, dict) and 'csv_text' in data:
            file_content = data['csv_text']
        elif isinstance(data, dict) and 'expenses' in data:
            # Batch list of dicts
            rows = data['expenses']
            return _process_expense_dict_list(rows, user_id, auto_categorize)
    
    if not file_content.strip():
        return jsonify({"status": "error", "message": "Uploaded CSV file is empty."}), 400

    # Parse CSV content using csv module
    try:
        csv_file = io.StringIO(file_content)
        # Check first line for dialect / header sniffing
        dialect = csv.Sniffer().sniff(csv_file.read(2048)) if len(file_content) > 10 else csv.excel
        csv_file.seek(0)
        reader = csv.reader(csv_file, dialect)
    except Exception:
        csv_file = io.StringIO(file_content)
        reader = csv.reader(csv_file)

    lines = list(reader)
    if not lines:
        return jsonify({"status": "error", "message": "No valid data lines found in CSV."}), 400

    header = [h.strip().lower().replace('_', ' ') for h in lines[0]]
    
    # Map header column indexes
    def find_idx(possible_names):
        for name in possible_names:
            for idx, col in enumerate(header):
                if name in col:
                    return idx
        return -1

    desc_idx = find_idx(['description', 'desc', 'title', 'item', 'details', 'name'])
    amt_idx = find_idx(['amount', 'price', 'cost', 'val', 'total'])
    cat_idx = find_idx(['category', 'type', 'group'])
    date_idx = find_idx(['date', 'time', 'day'])
    pay_idx = find_idx(['payment', 'method', 'mode', 'paid via', 'card'])

    # Default header mapping if no header matches
    data_rows = lines[1:] if desc_idx != -1 or amt_idx != -1 else lines
    if desc_idx == -1: desc_idx = 1 if len(lines[0]) > 1 else 0
    if amt_idx == -1: amt_idx = 2 if len(lines[0]) > 2 else (0 if desc_idx != 0 else 1)

    conn = get_db()
    cursor = conn.cursor()

    imported_count = 0
    auto_categorized_count = 0
    errors = []
    inserted_records = []

    today_str = datetime.date.today().strftime('%Y-%m-%d')

    for row_num, row in enumerate(data_rows, start=2):
        if not row or not any(field.strip() for field in row):
            continue

        description = row[desc_idx].strip() if desc_idx < len(row) else ''
        if not description:
            continue

        raw_amt = row[amt_idx].strip() if amt_idx < len(row) else '0'
        # Clean currency symbols
        cleaned_amt = raw_amt.replace('₹', '').replace('$', '').replace(',', '').strip()
        try:
            amount = float(cleaned_amt)
            if amount <= 0:
                continue
        except ValueError:
            errors.append(f"Row {row_num}: Invalid amount '{raw_amt}' for description '{description}'")
            continue

        category = row[cat_idx].strip() if (cat_idx != -1 and cat_idx < len(row)) else ''
        
        # If category is empty or uncategorized and auto_categorize is enabled, run ML model
        if auto_categorize and (not category or category.lower() in ['uncategorized', 'unknown', 'none', 'other', '']):
            ml_pred = category_classifier.predict(description)
            category = ml_pred.get('category', 'Miscellaneous')
            auto_categorized_count += 1
        elif not category:
            category = 'Miscellaneous'

        date_str = row[date_idx].strip() if (date_idx != -1 and date_idx < len(row)) else today_str
        # Standardize date format if possible
        if not date_str:
            date_str = today_str
        else:
            try:
                # Basic normalization for common formats e.g. DD/MM/YYYY or YYYY-MM-DD
                for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d'):
                    try:
                        parsed = datetime.datetime.strptime(date_str, fmt)
                        date_str = parsed.strftime('%Y-%m-%d')
                        break
                    except ValueError:
                        pass
            except Exception:
                date_str = today_str

        payment_method = row[pay_idx].strip() if (pay_idx != -1 and pay_idx < len(row)) else 'Card'
        if not payment_method:
            payment_method = 'Card'

        cursor.execute('''
        INSERT INTO expenses (user_id, description, amount, category, date, payment_method)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, description, amount, category, date_str, payment_method))
        
        imported_count += 1
        inserted_records.append({
            "description": description,
            "amount": amount,
            "category": category,
            "date": date_str,
            "payment_method": payment_method
        })

    conn.commit()

    # Retrain ML model with newly imported expenses
    try:
        category_classifier.load_or_train(conn)
    except Exception as e:
        print(f"ML retrain post-CSV upload: {e}")

    conn.close()

    return jsonify({
        "status": "success",
        "message": f"Successfully imported {imported_count} expenses ({auto_categorized_count} auto-categorized by ML).",
        "imported_count": imported_count,
        "auto_categorized_count": auto_categorized_count,
        "errors": errors,
        "sample": inserted_records[:5]
    }), 201


@app.route('/api/expenses/<int:expense_id>', methods=['PUT'])
def update_expense(expense_id):
    data = request.json or {}
    description = data.get('description')
    amount = data.get('amount')
    category = data.get('category')
    date_str = data.get('date')
    payment_method = data.get('payment_method')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM expenses WHERE id = ?", (expense_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"status": "error", "message": "Expense not found"}), 404

    cursor.execute('''
    UPDATE expenses 
    SET description = COALESCE(?, description),
        amount = COALESCE(?, amount),
        category = COALESCE(?, category),
        date = COALESCE(?, date),
        payment_method = COALESCE(?, payment_method)
    WHERE id = ?
    ''', (description, amount, category, date_str, payment_method, expense_id))
    
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": "Expense updated successfully"})


@app.route('/api/expenses/<int:expense_id>', methods=['DELETE'])
def delete_expense(expense_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    if deleted == 0:
        return jsonify({"status": "error", "message": "Expense not found"}), 404

    return jsonify({"status": "success", "message": "Expense deleted successfully"})


# ----------------------------
# 3. ML API ENDPOINTS
# ----------------------------
@app.route('/api/ml/predict-category', methods=['POST'])
def predict_category():
    data = request.json or {}
    description = data.get('description', '').strip()

    if not description:
        return jsonify({"status": "error", "message": "Description string is required"}), 400

    result = category_classifier.predict(description)
    return jsonify({"status": "success", "input": description, "prediction": result})


@app.route('/api/ml/predict-next-month', methods=['GET'])
def predict_next_month():
    user_id = request.args.get('user_id', 1, type=int)

    conn = get_db()
    cursor = conn.cursor()

    # Query monthly aggregate totals for past 12 months
    cursor.execute('''
    SELECT strftime('%Y-%m', date) as month_str, SUM(amount) as monthly_total
    FROM expenses
    WHERE user_id = ?
    GROUP BY month_str
    ORDER BY month_str ASC
    ''', (user_id,))
    
    rows = cursor.fetchall()
    conn.close()

    monthly_labels = [r['month_str'] for r in rows]
    monthly_totals = [round(r['monthly_total'], 2) for r in rows]

    # Predict using Linear Regression
    prediction_data = budget_predictor.predict_next_month(monthly_totals)
    prediction_data['monthly_labels'] = monthly_labels

    return jsonify({"status": "success", "prediction": prediction_data})


@app.route('/api/ml/retrain', methods=['POST'])
def retrain_ml():
    conn = get_db()
    category_classifier.load_or_train(conn)
    conn.close()
    return jsonify({"status": "success", "message": "Category classifier model retrained successfully on latest DB dataset."})


# ----------------------------
# 4. DASHBOARD & ANALYTICS API
# ----------------------------
@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    user_id = request.args.get('user_id', 1, type=int)
    today = datetime.date.today()
    current_month_prefix = today.strftime('%Y-%m')

    conn = get_db()
    cursor = conn.cursor()

    # Get User Budget
    cursor.execute("SELECT monthly_budget FROM users WHERE id = ?", (user_id,))
    user_row = cursor.fetchone()
    monthly_budget = user_row['monthly_budget'] if (user_row and user_row['monthly_budget']) else 2500.0

    # Total Expenses (All-time)
    cursor.execute("SELECT SUM(amount) as total FROM expenses WHERE user_id = ?", (user_id,))
    total_spending = cursor.fetchone()['total'] or 0.0

    # Current Month Spending
    cursor.execute("SELECT SUM(amount) as total, COUNT(*) as count FROM expenses WHERE user_id = ? AND strftime('%Y-%m', date) = ?", 
                   (user_id, current_month_prefix))
    cm_row = cursor.fetchone()
    current_month_total = cm_row['total'] or 0.0
    current_month_count = cm_row['count'] or 0

    # Budget percentage used
    budget_used_pct = round((current_month_total / monthly_budget * 100), 1) if monthly_budget > 0 else 0

    # Category Breakdown (Current Month)
    cursor.execute('''
    SELECT category, SUM(amount) as total
    FROM expenses
    WHERE user_id = ? AND strftime('%Y-%m', date) = ?
    GROUP BY category
    ORDER BY total DESC
    ''', (user_id, current_month_prefix))
    cat_rows = cursor.fetchall()
    
    category_labels = [r['category'] for r in cat_rows]
    category_totals = [round(r['total'], 2) for r in cat_rows]
    top_category = category_labels[0] if category_labels else 'N/A'

    # Monthly Trend (Past 6 Months)
    cursor.execute('''
    SELECT strftime('%Y-%m', date) as m_str, SUM(amount) as total
    FROM expenses
    WHERE user_id = ?
    GROUP BY m_str
    ORDER BY m_str DESC
    LIMIT 6
    ''', (user_id,))
    trend_rows = list(reversed(cursor.fetchall()))
    
    trend_months = [r['m_str'] for r in trend_rows]
    trend_totals = [round(r['total'], 2) for r in trend_rows]

    # Recent 5 Transactions
    cursor.execute('''
    SELECT e.*, c.icon, c.color FROM expenses e 
    LEFT JOIN categories c ON e.category = c.name 
    WHERE e.user_id = ? 
    ORDER BY e.date DESC, e.id DESC LIMIT 5
    ''', (user_id,))
    recent_expenses = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return jsonify({
        "status": "success",
        "stats": {
            "total_spending": round(total_spending, 2),
            "current_month_total": round(current_month_total, 2),
            "current_month_count": current_month_count,
            "monthly_budget": monthly_budget,
            "budget_used_percentage": budget_used_pct,
            "top_category": top_category
        },
        "category_breakdown": {
            "labels": category_labels,
            "data": category_totals
        },
        "monthly_trend": {
            "labels": trend_months,
            "data": trend_totals
        },
        "recent_expenses": recent_expenses
    })


# ----------------------------
# 5. REPORTS & EXPORT API
# ----------------------------
@app.route('/api/reports/export', methods=['GET'])
def export_csv():
    user_id = request.args.get('user_id', 1, type=int)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT id, date, description, amount, category, payment_method 
    FROM expenses 
    WHERE user_id = ? 
    ORDER BY date DESC
    ''', (user_id,))
    rows = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Date', 'Description', 'Amount (₹)', 'Category', 'Payment Method'])

    for r in rows:
        writer.writerow([r['id'], r['date'], r['description'], r['amount'], r['category'], r['payment_method']])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=expense_report.csv"}
    )


@app.route('/api/user/budget', methods=['GET', 'POST'])
def manage_budget():
    data = request.json or {}
    user_id = request.args.get('user_id', data.get('user_id', 1), type=int)
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        new_budget = data.get('monthly_budget')
        if new_budget is not None:
            cursor.execute("UPDATE users SET monthly_budget = ? WHERE id = ?", (float(new_budget), user_id))
            conn.commit()

    cursor.execute("SELECT monthly_budget FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    return jsonify({"status": "success", "monthly_budget": user['monthly_budget'] if (user and user['monthly_budget']) else 2500.0})


# ----------------------------
# 6. USER AUTHENTICATION & PROFILE API
# ----------------------------
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json or {}
    name = data.get('name', '').strip()
    username = data.get('username', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    address = data.get('address', '').strip()
    monthly_budget = data.get('monthly_budget', 2500.0)

    if not name or not email or not username or not password:
        return jsonify({"status": "error", "message": "Full Name, Username, Email, and Password are required."}), 400

    conn = get_db()
    cursor = conn.cursor()

    # Check if username or email already exists
    cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
    if cursor.fetchone():
        conn.close()
        return jsonify({"status": "error", "message": "Username or Email already registered."}), 400

    password_hash = generate_password_hash(password)

    try:
        cursor.execute('''
        INSERT INTO users (name, username, email, password_hash, address, monthly_budget)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, username, email, password_hash, address, float(monthly_budget)))
        user_id = cursor.lastrowid
        conn.commit()
    except Exception as e:
        conn.close()
        return jsonify({"status": "error", "message": f"Failed to register user: {str(e)}"}), 500

    cursor.execute("SELECT id, name, username, email, address, monthly_budget, created_at FROM users WHERE id = ?", (user_id,))
    user_row = dict(cursor.fetchone())
    conn.close()

    return jsonify({
        "status": "success",
        "message": "Registration successful!",
        "user": user_row
    }), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json or {}
    login_id = data.get('login', '').strip()  # Can be username or email
    password = data.get('password', '')

    if not login_id or not password:
        return jsonify({"status": "error", "message": "Username/Email and Password are required."}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? OR email = ?", (login_id, login_id.lower()))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return jsonify({"status": "error", "message": "Invalid credentials."}), 401

    # Verify password hash (fallback to plain text match for legacy demo accounts if unhashed)
    isValid = check_password_hash(user['password_hash'], password) or (user['password_hash'] == password)
    if not isValid:
        return jsonify({"status": "error", "message": "Invalid credentials."}), 401

    user_dict = {
        "id": user['id'],
        "name": user['name'] or user['username'],
        "username": user['username'],
        "email": user['email'],
        "address": user['address'] or '',
        "monthly_budget": user['monthly_budget']
    }

    return jsonify({
        "status": "success",
        "message": "Login successful!",
        "user": user_dict
    })


@app.route('/api/user/profile', methods=['GET', 'PUT'])
def user_profile():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'GET':
        user_id = request.args.get('user_id', 1, type=int)
        cursor.execute("SELECT id, name, username, email, address, monthly_budget, created_at FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()

        if not user:
            return jsonify({"status": "error", "message": "User not found."}), 404

        return jsonify({"status": "success", "user": dict(user)})

    elif request.method == 'PUT':
        data = request.json or {}
        user_id = data.get('user_id', 1)
        name = data.get('name', '').strip()
        email = data.get('email', '').strip().lower()
        address = data.get('address', '').strip()
        monthly_budget = data.get('monthly_budget')

        cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({"status": "error", "message": "User not found."}), 404

        cursor.execute('''
        UPDATE users
        SET name = COALESCE(?, name),
            email = COALESCE(?, email),
            address = COALESCE(?, address),
            monthly_budget = COALESCE(?, monthly_budget)
        WHERE id = ?
        ''', (name if name else None, email if email else None, address if address else None, monthly_budget, user_id))

        conn.commit()

        cursor.execute("SELECT id, name, username, email, address, monthly_budget, created_at FROM users WHERE id = ?", (user_id,))
        updated_user = dict(cursor.fetchone())
        conn.close()

        return jsonify({"status": "success", "message": "Profile updated successfully!", "user": updated_user})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

