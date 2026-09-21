from ml_engine import ExpenseCategoryClassifier, BudgetPredictor

def run_tests():
    print("=== STARTING ML ENGINE TESTS ===")

    # Test 1: Category Classifier
    classifier = ExpenseCategoryClassifier()
    classifier.load_or_train()

    test_cases = [
        ("Pizza Hut dinner with friends", "Food & Dining"),
        ("Uber ride to international airport", "Transportation"),
        ("Electric power utility bill payment", "Bills & Utilities"),
        ("Amazon online shopping electronics cable", "Shopping"),
        ("Netflix monthly streaming plan", "Entertainment"),
        ("Gym fitness center membership dues", "Health & Fitness"),
        ("Udemy online python programming course", "Education")
    ]

    correct_predictions = 0
    print("\n--- Test 1: Category Prediction Accuracy ---")
    for text, expected in test_cases:
        res = classifier.predict(text)
        predicted = res['predicted_category']
        conf = res['confidence_percentage']
        is_correct = predicted == expected
        if is_correct:
            correct_predictions += 1
        status = "PASSED" if is_correct else f"FAILED (Got {predicted})"
        print(f"Text: '{text}' => Predicted: [{predicted}] ({conf}% confidence) | Status: {status}")

    accuracy = (correct_predictions / len(test_cases)) * 100
    print(f"Overall Classification Test Accuracy: {accuracy:.1f}%")
    assert accuracy >= 80, "Classifier accuracy test failed!"

    # Test 2: Next Month Budget Linear Regression Predictor
    print("\n--- Test 2: Next Month Budget Linear Regression Predictor ---")
    history = [1200.0, 1280.0, 1350.0, 1420.0, 1500.0]
    predictor = BudgetPredictor()
    pred_res = predictor.predict_next_month(history)

    print(f"Historical Monthly Spending: {history}")
    print(f"Predicted Next Month Expense: ₹{pred_res['predicted_amount']}")
    print(f"Trend Slope: {pred_res['trend_slope']} per month | Trend Direction: {pred_res['trend_direction']}")
    
    assert pred_res['predicted_amount'] > 1500.0, "Linear regression trend should predict an increase!"
    assert pred_res['trend_direction'] == 'Increasing', "Trend direction should be Increasing!"
    print("Linear Regression Budget Predictor Test: PASSED")

    print("\nALL ML ENGINE TESTS COMPLETED SUCCESSFULLY!")

if __name__ == '__main__':
    run_tests()
