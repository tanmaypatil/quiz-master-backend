import json
from lambda_function import lambda_handler

# Optional: Function for testing locally
def test_locally():
    """Function for local testing"""
    print("call the quiz generation function with a sample event")
    test_event = {
        "prompt": "Generate a Quiz of 3 questions on new indian parliament building",
        "tags": ["parliament", "india"],
       
    }
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))