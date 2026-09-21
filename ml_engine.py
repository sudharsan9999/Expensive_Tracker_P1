import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, LinearRegression
import joblib
import os
import sqlite3

# Directory paths for saved ML artifacts
MODEL_DIR = os.path.join(os.path.dirname(__file__), 'ml_models')
os.makedirs(MODEL_DIR, exist_ok=True)

VECTORIZER_PATH = os.path.join(MODEL_DIR, 'tfidf_vectorizer.joblib')
CLASSIFIER_PATH = os.path.join(MODEL_DIR, 'category_classifier.joblib')

# Synthetic base dataset for robust zero-cold-start training
BASE_TRAINING_DATA = [
    # Food & Dining
    ("pizza with friends at hut", "Food & Dining"),
    ("starbucks coffee and morning donut", "Food & Dining"),
    ("walmart grocery shopping milk bread eggs", "Food & Dining"),
    ("mcdonalds burger fries lunch deal", "Food & Dining"),
    ("subway veggie sandwich", "Food & Dining"),
    ("restaurant dinner buffet with family", "Food & Dining"),
    ("organic fruits and vegetables market", "Food & Dining"),
    ("dominos pepperoni pizza delivery", "Food & Dining"),
    ("chipotle Mexican grill burrito bowl", "Food & Dining"),
    ("sushi bar japanese food", "Food & Dining"),
    ("kfc fried chicken bucket dinner", "Food & Dining"),
    ("taco bell tacos and nachos", "Food & Dining"),
    ("diner breakfast pancakes coffee", "Food & Dining"),
    ("bakery sourdough cakes and pastries", "Food & Dining"),
    ("ice cream parlor sundaes", "Food & Dining"),
    ("food truck lunch taco", "Food & Dining"),
    ("groceries superstore food items", "Food & Dining"),
    ("cafe espresso coffee and tea", "Food & Dining"),

    # Transportation
    ("uber ride to office location", "Transportation"),
    ("lyft taxi ride from airport", "Transportation"),
    ("gas station fuel refill shell", "Transportation"),
    ("petrol refill for car", "Transportation"),
    ("subway metro monthly pass ticket", "Transportation"),
    ("bus fare transit pass", "Transportation"),
    ("car oil change maintenance service", "Transportation"),
    ("parking meter fee downtown city", "Transportation"),
    ("highway expressway toll pay", "Transportation"),
    ("auto insurance vehicle premium", "Transportation"),
    ("cab fare ride home", "Transportation"),
    ("car wash and interior detailing", "Transportation"),
    ("train ticket intercity rail", "Transportation"),
    ("car mechanic repair brake replacement", "Transportation"),

    # Bills & Utilities
    ("electricity utility bill payment power", "Bills & Utilities"),
    ("water sewage municipal bill", "Bills & Utilities"),
    ("high speed fiber internet wifi bill", "Bills & Utilities"),
    ("cell phone postpaid mobile recharge", "Bills & Utilities"),
    ("natural gas heating utility payment", "Bills & Utilities"),
    ("apartment monthly rent housing", "Bills & Utilities"),
    ("garbage trash disposal bill", "Bills & Utilities"),
    ("home maintenance HOA dues", "Bills & Utilities"),
    ("cable tv satellite subscription", "Bills & Utilities"),

    # Shopping
    ("amazon online shopping electronics cable", "Shopping"),
    ("zara jacket clothes fashion store", "Shopping"),
    ("nike athletic sneakers shoes", "Shopping"),
    ("ikea desk table lamp furniture", "Shopping"),
    ("sephora cosmetics skin moisturizer makeup", "Shopping"),
    ("apple store iphone case accessories", "Shopping"),
    ("department store apparel clothes shopping", "Shopping"),
    ("ebay online purchase item", "Shopping"),
    ("target store household items shopping", "Shopping"),
    ("h&m shirt pants sweater fashion", "Shopping"),

    # Entertainment
    ("netflix monthly streaming plan", "Entertainment"),
    ("spotify music premium subscription", "Entertainment"),
    ("cinema movie tickets pop corn", "Entertainment"),
    ("steam video games download", "Entertainment"),
    ("concert music festival live show ticket", "Entertainment"),
    ("playstation online subscription network", "Entertainment"),
    ("hulu streaming video series", "Entertainment"),
    ("disney plus subscription movies", "Entertainment"),
    ("bowling alley game weekend", "Entertainment"),
    ("amusement park theme ticket", "Entertainment"),

    # Health & Fitness
    ("gym fitness center membership dues", "Health & Fitness"),
    ("cvs pharmacy prescription medicine doctor", "Health & Fitness"),
    ("dental checkup teeth cleaning dentist", "Health & Fitness"),
    ("protein supplement whey jar", "Health & Fitness"),
    ("eye doctor vision clinic glasses", "Health & Fitness"),
    ("hospital medical checkup bill doctor fee", "Health & Fitness"),
    ("yoga class studio subscription", "Health & Fitness"),
    ("multivitamins pharmacy medicine store", "Health & Fitness"),

    # Education
    ("udemy online python programming course", "Education"),
    ("coursera data science certificate", "Education"),
    ("college university tuition semester fee", "Education"),
    ("barnes noble textbooks reading books", "Education"),
    ("school stationery notebooks pens", "Education"),
    ("edx machine learning certification", "Education"),

    # Travel & Vacation
    ("airbnb holiday cabin booking rental", "Travel & Vacation"),
    ("delta flight tickets domestic travel", "Travel & Vacation"),
    ("hotel resort stay 3 nights", "Travel & Vacation"),
    ("flight ticket airline booking", "Travel & Vacation"),
    ("vacation tour travel guide fee", "Travel & Vacation"),

    # Investments
    ("mutual fund sip monthly investment", "Investments"),
    ("stock market equity buy trade shares", "Investments"),
    ("crypto bitcoin investment", "Investments"),
    ("fixed deposit savings account bank", "Investments"),
    ("gold bond investment fund", "Investments"),

    # Miscellaneous
    ("dry cleaning suit laundry service", "Miscellaneous"),
    ("hardware store tools screws nails", "Miscellaneous"),
    ("pet food vet care dog", "Miscellaneous"),
    ("post office courier shipping fee", "Miscellaneous"),
    ("charity donation gift", "Miscellaneous")
]


class ExpenseCategoryClassifier:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=1500, lowercase=True)
        self.model = LogisticRegression(C=1.0, max_iter=300, random_state=42)
        self.is_trained = False

    def train(self, texts, labels):
        if not texts or len(texts) < 2:
            return False
        
        X = self.vectorizer.fit_transform(texts)
        self.model.fit(X, labels)
        self.is_trained = True

        # Save artifacts
        joblib.dump(self.vectorizer, VECTORIZER_PATH)
        joblib.dump(self.model, CLASSIFIER_PATH)
        return True

    def load_or_train(self, db_conn=None):
        """Loads model if saved, otherwise trains using base data + DB records."""
        texts, labels = [], []
        
        # Add base training data
        for desc, cat in BASE_TRAINING_DATA:
            texts.append(desc)
            labels.append(cat)

        # Supplement with DB records if available
        if db_conn:
            try:
                cursor = db_conn.cursor()
                cursor.execute("SELECT description, category FROM expenses WHERE description IS NOT NULL AND category IS NOT NULL")
                rows = cursor.fetchall()
                for r in rows:
                    if r['description'] and r['category']:
                        texts.append(r['description'])
                        labels.append(r['category'])
            except Exception as e:
                print(f"Note: Error reading DB for ML training: {e}")

        self.train(texts, labels)

    def predict(self, description_text):
        if not self.is_trained or not description_text:
            return {"category": "Miscellaneous", "confidence": 0.50, "all_probabilities": {}}

        X_text = self.vectorizer.transform([description_text])
        probabilities = self.model.predict_proba(X_text)[0]
        classes = self.model.classes_

        top_idx = np.argmax(probabilities)
        top_category = classes[top_idx]
        top_confidence = round(float(probabilities[top_idx]), 2)

        probs_dict = {classes[i]: round(float(probabilities[i]), 3) for i in range(len(classes))}
        # Sort descending
        sorted_probs = dict(sorted(probs_dict.items(), key=lambda item: item[1], reverse=True))

        return {
            "predicted_category": top_category,
            "confidence": top_confidence,
            "confidence_percentage": int(top_confidence * 100),
            "top_suggestions": list(sorted_probs.items())[:3]
        }


class BudgetPredictor:
    """Linear Regression model to predict next month's total expense based on historical trends."""
    
    def predict_next_month(self, monthly_totals):
        """
        monthly_totals: List of floats representing sequential monthly total expenses.
        Example: [1200.5, 1350.0, 1280.2, 1410.0, 1500.0]
        """
        if not monthly_totals or len(monthly_totals) == 0:
            return {
                "predicted_amount": 0.0,
                "confidence_status": "No Historical Data Available",
                "trend_direction": "Neutral",
                "monthly_history": []
            }

        if len(monthly_totals) == 1:
            return {
                "predicted_amount": round(monthly_totals[0], 2),
                "confidence_status": "Based on 1 Month of Data",
                "trend_direction": "Stable",
                "monthly_history": monthly_totals
            }

        # Prepare X (indices 0, 1, 2...) and y (expenses)
        X = np.array(range(len(monthly_totals))).reshape(-1, 1)
        y = np.array(monthly_totals)

        model = LinearRegression()
        model.fit(X, y)

        next_month_idx = np.array([[len(monthly_totals)]])
        pred = model.predict(next_month_idx)[0]
        pred_amount = max(0.0, round(float(pred), 2))

        slope = model.coef_[0]
        if slope > 15:
            trend = "Increasing"
        elif slope < -15:
            trend = "Decreasing"
        else:
            trend = "Stable"

        avg_spending = round(float(np.mean(y)), 2)

        return {
            "predicted_amount": pred_amount,
            "average_monthly_spend": avg_spending,
            "trend_slope": round(float(slope), 2),
            "trend_direction": trend,
            "data_points_count": len(monthly_totals),
            "monthly_history": monthly_totals
        }

# Global instances
category_classifier = ExpenseCategoryClassifier()
budget_predictor = BudgetPredictor()

def init_ml_engine(db_conn=None):
    category_classifier.load_or_train(db_conn)
    print("ML Engine initialized successfully (TF-IDF + Logistic Regression Classifier trained).")

if __name__ == '__main__':
    # Unit test execution
    classifier = ExpenseCategoryClassifier()
    classifier.load_or_train()
    
    test_queries = [
        "Pizza with friends on Friday night",
        "Uber ride from downtown to airport",
        "Electric power utility bill payment",
        "Netflix monthly streaming subscription",
        "Udemy python machine learning course"
    ]
    
    print("\n--- Testing ML Expense Category Classification ---")
    for q in test_queries:
        res = classifier.predict(q)
        print(f"Input: '{q}' -> Predicted: {res['predicted_category']} ({res['confidence_percentage']}% confidence)")

    print("\n--- Testing Next Month Budget Prediction (Linear Regression) ---")
    history = [1250.0, 1320.0, 1290.0, 1400.0, 1480.0]
    predictor = BudgetPredictor()
    pred_res = predictor.predict_next_month(history)
    print(f"Past History: {history}")
    print(f"Predicted Next Month: ₹{pred_res['predicted_amount']} (Trend: {pred_res['trend_direction']})")
