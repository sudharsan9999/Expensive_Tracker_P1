import urllib.request
import json

BASE_URL = "http://127.0.0.1:5000"

def test_api():
    print("=== TESTING ALL REST API ENDPOINTS ===")
    
    # 1. Test Dashboard Stats
    req = urllib.request.urlopen(f"{BASE_URL}/api/dashboard/stats?user_id=1")
    res = json.loads(req.read().decode('utf-8'))
    print(f"\n1. Dashboard Stats API: Status = {res['status']}")
    print(f"   Total Spending: ₹{res['stats']['total_spending']}")
    print(f"   Current Month: ₹{res['stats']['current_month_total']}")
    print(f"   Budget Used: {res['stats']['budget_used_percentage']}%")

    # 2. Test ML Category Prediction Endpoint
    data = json.dumps({"description": "Starbucks mocha iced coffee and muffin"}).encode('utf-8')
    req = urllib.request.Request(f"{BASE_URL}/api/ml/predict-category", data=data, headers={'Content-Type': 'application/json'})
    res = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
    print(f"\n2. ML Category Predictor API: Status = {res['status']}")
    print(f"   Input: '{res['input']}'")
    print(f"   Predicted Category: {res['prediction']['predicted_category']} ({res['prediction']['confidence_percentage']}% confidence)")

    # 3. Test ML Linear Regression Next Month Prediction
    req = urllib.request.urlopen(f"{BASE_URL}/api/ml/predict-next-month?user_id=1")
    res = json.loads(req.read().decode('utf-8'))
    print(f"\n3. ML Budget Linear Regression Predictor API: Status = {res['status']}")
    print(f"   Predicted Next Month Spend: ₹{res['prediction']['predicted_amount']}")
    print(f"   Trend Direction: {res['prediction']['trend_direction']}")

    # 4. Test User Authentication - Login
    login_data = json.dumps({"login": "demo", "password": "demo123"}).encode('utf-8')
    req = urllib.request.Request(f"{BASE_URL}/api/auth/login", data=login_data, headers={'Content-Type': 'application/json'})
    res = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
    print(f"\n4. User Auth Login API: Status = {res['status']}")
    print(f"   Logged User Name: '{res['user']['name']}' | Email: '{res['user']['email']}'")
    assert res['status'] == 'success', "Login failed!"

    # 5. Test User Authentication - Registration
    import time
    unique_user = f"user_{int(time.time())}"
    reg_payload = json.dumps({
        "name": "Sudhir Kumar",
        "username": unique_user,
        "email": f"{unique_user}@example.com",
        "password": "mysecretpassword",
        "address": "456 Tech Park, Electronic City, Bengaluru",
        "monthly_budget": 3000.0
    }).encode('utf-8')
    req = urllib.request.Request(f"{BASE_URL}/api/auth/register", data=reg_payload, headers={'Content-Type': 'application/json'})
    res = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
    print(f"\n5. User Registration API: Status = {res['status']}")
    print(f"   Registered User ID: {res['user']['id']} | Address: '{res['user']['address']}'")
    assert res['status'] == 'success', "Registration failed!"

    # 6. Test User Profile Update
    update_payload = json.dumps({
        "user_id": res['user']['id'],
        "name": "Sudhir Kumar (Updated)",
        "email": f"{unique_user}@example.com",
        "address": "789 Innovation Hub, MG Road, Bengaluru",
        "monthly_budget": 3500.0
    }).encode('utf-8')
    req = urllib.request.Request(f"{BASE_URL}/api/user/profile", data=update_payload, headers={'Content-Type': 'application/json'}, method='PUT')
    res = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
    print(f"\n6. User Profile Update API: Status = {res['status']}")
    print(f"   Updated Address: '{res['user']['address']}' | New Budget: ₹{res['user']['monthly_budget']}")
    assert res['user']['name'] == "Sudhir Kumar (Updated)", "Profile update failed!"

    # 7. Test Expenses API
    req = urllib.request.urlopen(f"{BASE_URL}/api/expenses?user_id=1")
    res = json.loads(req.read().decode('utf-8'))
    print(f"\n7. Expenses List API: Total Expenses count = {res['count']}")

    print("\nALL API ENDPOINT INTEGRATION TESTS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    test_api()
