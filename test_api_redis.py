#!/usr/bin/env python3
"""Test Redis storage integration with the running API"""

import requests
import time
import json

API_BASE = "http://localhost:8000"

def test_api_redis_integration():
    """Test that Redis storage works with the API"""
    print("🧪 Testing API + Redis integration...")
    
    # Test 1: Create a search job
    print("\n📤 Creating search job...")
    search_request = {
        "query_text": "upbeat dance music for a party",
        "user_session_id": "test_user_123",
        "search_session_id": "test_search_456"
    }
    
    try:
        response = requests.post(f"{API_BASE}/search", json=search_request, timeout=10)
        if response.status_code != 200:
            print(f"❌ Search request failed: {response.status_code} - {response.text}")
            return False
        
        job_data = response.json()
        job_id = job_data["job_id"]
        print(f"✅ Created job: {job_id}")
        print(f"   User session: {job_data.get('user_session_id')}")
        print(f"   Model: {job_data.get('model')}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to create search job: {e}")
        return False
    
    # Test 2: Poll job status multiple times (simulates different workers)
    print(f"\n🔄 Polling job status...")
    
    for i in range(5):
        try:
            response = requests.get(f"{API_BASE}/jobs/{job_id}", timeout=5)
            if response.status_code == 404:
                print(f"❌ Job not found on poll {i+1} - Redis sharing failed!")
                return False
            elif response.status_code != 200:
                print(f"⚠️ Poll {i+1} failed: {response.status_code}")
                continue
            
            job_status = response.json()
            status = job_status["status"]
            query = job_status.get("query_text", "")
            model = job_status.get("model", "")
            
            print(f"   Poll {i+1}: {status} - {query[:30]}... (model: {model})")
            
            if status == "done":
                result_count = job_status.get("result_count", 0)
                print(f"✅ Job completed! {result_count} results found")
                
                # Check if results are available
                if job_status.get("results"):
                    tracks = job_status["results"]["tracks"]
                    if tracks:
                        first_track = tracks[0]
                        print(f"   First result: {first_track['track']} by {first_track['artist']}")
                
                break
            elif status == "error":
                error_msg = job_status.get("error_message", "Unknown error")
                print(f"❌ Job failed: {error_msg}")
                return False
            
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Poll {i+1} failed: {e}")
        
        time.sleep(2)
    
    # Test 3: Check Redis cache statistics via health endpoint
    print(f"\n📊 Checking cache statistics...")
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Health check: {health_data.get('status')}")
            print(f"   Active jobs: {health_data.get('active_jobs', 'unknown')}")
            print(f"   Cached results: {health_data.get('cached_results', 'unknown')}")
        else:
            print(f"⚠️ Health check failed: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Health check failed: {e}")
    
    print("\n🎉 API + Redis integration test completed!")
    return True

def test_redis_connection_direct():
    """Test direct Redis connection to verify storage"""
    print("\n🔗 Testing direct Redis connection...")
    
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        
        # Check for job keys
        job_keys = r.keys("job:*")
        result_keys = r.keys("results:*")
        
        print(f"✅ Direct Redis connection successful")
        print(f"   Jobs in cache: {len(job_keys)}")
        print(f"   Results in cache: {len(result_keys)}")
        
        if job_keys:
            print(f"   Sample job key: {job_keys[0]}")
            # Get sample job data
            sample_job = r.get(job_keys[0])
            if sample_job:
                job_data = json.loads(sample_job)
                print(f"   Sample job status: {job_data.get('status')}")
                print(f"   Sample job query: {job_data.get('query_text', '')[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Direct Redis connection failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Redis storage with running API...")
    
    # Test direct Redis connection first
    redis_ok = test_redis_connection_direct()
    if not redis_ok:
        print("🚫 Fix Redis connection before testing API integration")
        exit(1)
    
    # Test API integration
    api_ok = test_api_redis_integration()
    
    if api_ok and redis_ok:
        print("\n🎉 All tests passed! Redis storage is working with the API.")
        print("💡 Jobs are now shared across workers - no more 404 errors!")
    else:
        print("\n❌ Some tests failed. Check the output above.")
        exit(1)