"""
Test script for the Desktop Automation AI API
This script demonstrates how to interact with the FastAPI server programmatically.
"""

import requests
import time
import json
from datetime import datetime

# API base URL
BASE_URL = "http://localhost:8000"

def test_health():
    """Test the health endpoint"""
    print("Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"✅ Health check: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_status():
    """Test the status endpoint"""
    print("\nTesting status endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/status")
        print(f"✅ Status: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Status check failed: {e}")
        return False

def test_reset():
    """Test the reset endpoint"""
    print("\nTesting reset endpoint...")
    try:
        response = requests.post(f"{BASE_URL}/reset")
        print(f"✅ Reset: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Reset failed: {e}")
        return False

def test_prompt(prompt_text: str = "Take a screenshot and tell me what you see on the screen"):
    """Test sending a prompt"""
    print(f"\nTesting prompt endpoint with: '{prompt_text}'")
    
    # You can use webhook.site for testing webhooks
    webhook_url = "https://webhook.site/unique-url-here"  # Replace with your webhook URL
    
    payload = {
        "prompt": prompt_text,
        "webhook_url": webhook_url,
        "only_n_most_recent_images": 5
    }
    
    try:
        response = requests.post(f"{BASE_URL}/prompt", json=payload)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Prompt sent successfully: {result}")
            
            # Monitor status
            print("\nMonitoring processing status...")
            for i in range(30):  # Check for up to 5 minutes
                time.sleep(10)  # Wait 10 seconds between checks
                status_response = requests.get(f"{BASE_URL}/status")
                status = status_response.json()
                
                print(f"Status check {i+1}: Processing={status['is_processing']}, Messages={status['messages_count']}")
                
                if not status['is_processing']:
                    print("✅ Processing completed!")
                    break
            else:
                print("⚠️ Processing is taking longer than expected...")
            
            return True
        else:
            print(f"❌ Prompt failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Prompt test failed: {e}")
        return False

def run_comprehensive_test():
    """Run a comprehensive test of all endpoints"""
    print("=== Desktop Automation AI API Test ===")
    print(f"Testing API at: {BASE_URL}")
    print(f"Test started at: {datetime.now()}")
    print("="*50)
    
    tests = [
        ("Health Check", test_health),
        ("Status Check", test_status),
        ("Reset Session", test_reset),
        ("Send Prompt", lambda: test_prompt("Take a screenshot"))
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    print("\n" + "="*50)
    print("TEST RESULTS SUMMARY:")
    print("="*50)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The API is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")

def interactive_test():
    """Interactive test mode"""
    print("=== Interactive API Test Mode ===")
    print("Available commands:")
    print("1. health - Test health endpoint")
    print("2. status - Check processing status")
    print("3. reset - Reset session")
    print("4. prompt <text> - Send a custom prompt")
    print("5. screenshot - Take a screenshot")
    print("6. quit - Exit")
    print()
    
    while True:
        try:
            command = input("Enter command: ").strip().lower()
            
            if command == "quit":
                break
            elif command == "health":
                test_health()
            elif command == "status":
                test_status()
            elif command == "reset":
                test_reset()
            elif command.startswith("prompt "):
                prompt_text = command[7:]  # Remove "prompt " prefix
                test_prompt(prompt_text)
            elif command == "screenshot":
                test_prompt("Take a screenshot and describe what you see")
            else:
                print("Unknown command. Type 'quit' to exit.")
                
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        interactive_test()
    else:
        run_comprehensive_test()
        
        print("\n" + "="*50)
        print("To run in interactive mode, use: python test_api.py interactive")
        print("Make sure to:")
        print("1. Start the API server first: python api_server.py")
        print("2. Set up a webhook URL (try webhook.site for testing)")
        print("3. Set your ANTHROPIC_API_KEY environment variable")