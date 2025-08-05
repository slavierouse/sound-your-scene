#!/usr/bin/env python3
"""Test Redis connection before converting storage system"""

import redis
import json
from datetime import datetime

def test_redis_connection():
    """Test basic Redis operations"""
    print("🧪 Testing Redis connection...")
    
    try:
        # Connect to Redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        
        # Test connection
        r.ping()
        print("✅ Connected to Redis!")
        
        # Test basic string operations
        r.set('test_key', 'hello redis')
        result = r.get('test_key')
        print(f"✅ Basic operations: {result}")
        
        # Test JSON serialization (what we'll use for job data)
        test_data = {
            "job_id": "test123",
            "status": "running",
            "timestamp": datetime.now().isoformat(),
            "data": {"query": "test query", "count": 42}
        }
        
        # Store as JSON string
        r.set('test_json', json.dumps(test_data))
        retrieved = json.loads(r.get('test_json'))
        print(f"✅ JSON serialization: {retrieved['job_id']} - {retrieved['status']}")
        
        # Test with TTL (Time To Live)
        r.setex('temp_key', 10, 'expires in 10 seconds')
        ttl = r.ttl('temp_key')
        print(f"✅ TTL test: {ttl} seconds remaining")
        
        # Test hash operations (alternative to JSON)
        r.hset('test_hash', mapping={
            'status': 'done',
            'count': '123',
            'message': 'test complete'
        })
        hash_data = r.hgetall('test_hash')
        print(f"✅ Hash operations: {hash_data}")
        
        # Cleanup test data
        r.delete('test_key', 'test_json', 'temp_key', 'test_hash')
        print("✅ Cleanup complete")
        
        return True
        
    except redis.ConnectionError:
        print("❌ Cannot connect to Redis. Is it running on localhost:6379?")
        print("💡 Try: docker run -p 6379:6379 -d redis:7-alpine")
        return False
    except Exception as e:
        print(f"❌ Redis test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_redis_connection()
    if success:
        print("\n🎉 Redis is ready! We can now convert the storage system.")
    else:
        print("\n🚫 Fix Redis connection before proceeding.")