#!/usr/bin/env python3
"""
AI Education Platform Deployment Checker
Validates configuration and tests connectivity
"""

import requests
import os
import sys
from urllib.parse import urljoin

def check_backend_health(backend_url):
    """Check if backend is responding"""
    try:
        health_url = urljoin(backend_url, '/health')
        response = requests.get(health_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Backend is healthy: {data.get('status', 'unknown')}")
            print(f"   Service: {data.get('service', 'unknown')}")
            print(f"   Version: {data.get('version', 'unknown')}")
            return True
        else:
            print(f"❌ Backend health check failed: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to backend: {e}")
        return False

def check_api_docs(backend_url):
    """Check if API documentation is accessible"""
    try:
        docs_url = urljoin(backend_url, '/docs')
        response = requests.get(docs_url, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ API documentation is accessible: {docs_url}")
            return True
        else:
            print(f"❌ API documentation not accessible: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot access API docs: {e}")
        return False

def check_cors(backend_url):
    """Check CORS configuration"""
    try:
        # Make an OPTIONS request to check CORS headers
        response = requests.options(backend_url, timeout=10)
        cors_headers = {
            'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
            'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
            'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
        }
        
        if any(cors_headers.values()):
            print("✅ CORS headers detected:")
            for header, value in cors_headers.items():
                if value:
                    print(f"   {header}: {value}")
            return True
        else:
            print("⚠️  No CORS headers detected")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot check CORS: {e}")
        return False

def test_grading_endpoint(backend_url):
    """Test if grading endpoint is available"""
    try:
        grading_url = urljoin(backend_url, '/api/v1/v2/grading/submit-sync')
        
        # Just check if endpoint exists (will return 401/422 but not 404)
        response = requests.post(grading_url, json={}, timeout=10)
        
        if response.status_code in [401, 422, 403]:
            print("✅ Grading endpoint is available (authentication required)")
            return True
        elif response.status_code == 404:
            print("❌ Grading endpoint not found")
            return False
        else:
            print(f"⚠️  Grading endpoint responded with status: {response.status_code}")
            return True
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot test grading endpoint: {e}")
        return False

def main():
    print("🔍 AI Education Platform Deployment Checker")
    print("=" * 50)
    
    # Get backend URL from user
    backend_url = input("Enter your Railway backend URL (e.g., https://your-backend.railway.app): ").strip()
    
    if not backend_url:
        print("❌ Backend URL is required")
        sys.exit(1)
    
    if not backend_url.startswith(('http://', 'https://')):
        backend_url = 'https://' + backend_url
    
    print(f"\n🎯 Testing backend: {backend_url}")
    print("-" * 50)
    
    # Run checks
    checks = [
        ("Backend Health", lambda: check_backend_health(backend_url)),
        ("API Documentation", lambda: check_api_docs(backend_url)),
        ("CORS Configuration", lambda: check_cors(backend_url)),
        ("Grading Endpoint", lambda: test_grading_endpoint(backend_url)),
    ]
    
    results = []
    for check_name, check_func in checks:
        print(f"\n📋 Checking {check_name}...")
        result = check_func()
        results.append((check_name, result))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 DEPLOYMENT CHECK SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {check_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 All checks passed! Your deployment is ready!")
        print("\n📝 Next steps:")
        print("1. Test frontend connection to backend")
        print("2. Try uploading a sample image for grading")
        print("3. Configure OpenRouter API key if not done")
        print(f"4. Visit API docs: {backend_url}/docs")
    else:
        print("\n⚠️  Some checks failed. Please review the errors above.")
        print("\n🛠️  Common fixes:")
        print("- Wait for deployment to complete (can take 2-5 minutes)")
        print("- Check environment variables in Railway dashboard")
        print("- Verify database services are running")
        print("- Check Railway logs for errors")
    
    return passed == total

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Check cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)