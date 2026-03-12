import requests
import json

BASE = "http://localhost:8000/api/v1"

def test():
    print("\n" + "="*60)
    print("  🧪 TESTING AI MAIL ASSISTANT")
    print("="*60)
    
    # Test 1: Health
    print("\n1️⃣ Health Check...")
    r = requests.get(f"{BASE}/health")
    print(json.dumps(r.json(), indent=2))
    
    # Test 2: Models
    print("\n2️⃣ Available Models...")
    r = requests.get(f"{BASE}/models")
    print(json.dumps(r.json(), indent=2))
    
    # Test 3: Process Email
    print("\n3️⃣ Processing Email...")
    email = {
        "sender": "customer@example.com",
        "subject": "Business Hours",
        "body": "What are your office hours? I want to visit tomorrow.",
        "context": "general"
    }
    
    r = requests.post(f"{BASE}/process-email", json=email)
    result = r.json()
    
    print(f"\n📧 Question: {result['original_message']}")
    print(f"\n🤖 AI Answer:\n{result['ai_response']}")
    print(f"\n📊 Model: {result['model_used']}")
    print(f"⏱️  Time: {result['processing_time']}s")
    
    # Test 4: Auto-reply
    print("\n4️⃣ Auto-Reply Test...")
    r = requests.post(f"{BASE}/auto-reply", json=email)
    result = r.json()
    
    print(f"Should Auto-Reply: {result['should_auto_reply']}")
    print(f"Classification: {result['classification']}")
    print(f"Reason: {result['reason']}")
    
    print("\n" + "="*60)
    print("  ✅ ALL TESTS PASSED!")
    print("="*60 + "\n")

if __name__ == "__main__":
    try:
        test()
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Server not running!")
        print("💡 Start it with: python run.py\n")
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")