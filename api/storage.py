from typing import Dict, List, Optional
from datetime import datetime, timedelta
import redis
import json
import os
from api.models import JobData, SearchResults

# Redis connection - will fallback to in-memory if Redis unavailable
_redis_client = None

def get_redis_client():
    """Get Redis client with connection pooling"""
    global _redis_client
    if _redis_client is None:
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            
            # Configure for AWS ElastiCache TLS
            if redis_url.startswith('rediss://') or os.getenv('REDIS_TLS', 'false').lower() == 'true':
                _redis_client = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30,
                    ssl_cert_reqs=None,  # AWS ElastiCache doesn't require client certs
                    ssl_check_hostname=False,  # AWS handles hostname verification
                    ssl_ca_certs=None
                )
            else:
                # Local development (no TLS)
                _redis_client = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
            
            # Test connection
            _redis_client.ping()
            print("Connected to Redis cache")
        except Exception as e:
            print(f"Redis unavailable ({e}), falling back to in-memory storage")
            _redis_client = None
    return _redis_client

# Fallback in-memory stores (used when Redis is unavailable)
JOB_STORE: Dict[str, JobData] = {}
RESULT_STORE: Dict[str, SearchResults] = {}

# Cache TTL settings (Redis auto-expires, no manual cleanup needed)
JOB_TTL_SECONDS = 7200  # 2 hours for job data
RESULTS_TTL_SECONDS = 3600  # 1 hour for results

def store_job(job_id: str, job_data: JobData):
    """Store job data in Redis with fallback to in-memory"""
    redis_client = get_redis_client()
    
    if redis_client:
        try:
            # Convert JobData to JSON using Pydantic's model_dump
            job_json = json.dumps(job_data.model_dump(), default=str)
            redis_client.setex(f"job:{job_id}", JOB_TTL_SECONDS, job_json)
            return
        except Exception as e:
            print(f"Redis store_job failed ({e}), using fallback")
    
    # Fallback to in-memory
    JOB_STORE[job_id] = job_data

def get_job(job_id: str) -> Optional[JobData]:
    """Get job data by ID from Redis with fallback to in-memory"""
    redis_client = get_redis_client()
    
    if redis_client:
        try:
            job_json = redis_client.get(f"job:{job_id}")
            if job_json:
                job_dict = json.loads(job_json)
                return JobData(**job_dict)
        except Exception as e:
            print(f"Redis get_job failed ({e}), using fallback")
    
    # Fallback to in-memory
    return JOB_STORE.get(job_id)

def store_results(job_id: str, results: SearchResults):
    """Store search results in Redis with fallback to in-memory"""
    redis_client = get_redis_client()
    
    if redis_client:
        try:
            # Convert SearchResults to JSON using Pydantic's model_dump
            results_json = json.dumps(results.model_dump(), default=str)
            redis_client.setex(f"results:{job_id}", RESULTS_TTL_SECONDS, results_json)
            return
        except Exception as e:
            print(f"Redis store_results failed ({e}), using fallback")
    
    # Fallback to in-memory
    RESULT_STORE[job_id] = results

def get_results(job_id: str) -> Optional[SearchResults]:
    """Get search results by job ID from Redis with fallback to in-memory"""
    redis_client = get_redis_client()
    
    if redis_client:
        try:
            results_json = redis_client.get(f"results:{job_id}")
            if results_json:
                results_dict = json.loads(results_json)
                return SearchResults(**results_dict)
        except Exception as e:
            print(f"Redis get_results failed ({e}), using fallback")
    
    # Fallback to in-memory
    return RESULT_STORE.get(job_id)

def job_exists(job_id: str) -> bool:
    """Check if job exists in Redis with fallback to in-memory"""
    redis_client = get_redis_client()
    
    if redis_client:
        try:
            return redis_client.exists(f"job:{job_id}") > 0
        except Exception as e:
            print(f"Redis job_exists failed ({e}), using fallback")
    
    # Fallback to in-memory
    return job_id in JOB_STORE

def cleanup_old_jobs():
    """Clean up old jobs - Redis auto-expires, only needed for in-memory fallback"""
    redis_client = get_redis_client()
    
    if redis_client:
        try:
            # Redis handles TTL automatically, just report stats
            job_keys = redis_client.keys("job:*")
            result_keys = redis_client.keys("results:*")
            print(f"Redis cache status: {len(job_keys)} jobs, {len(result_keys)} results")
            return
        except Exception as e:
            print(f"Redis cleanup check failed ({e})")
    
    # Fallback: manual cleanup for in-memory storage
    cutoff_time = datetime.now() - timedelta(hours=2)  # Match Redis TTL
    
    jobs_to_remove = []
    for job_id, job_data in JOB_STORE.items():
        if job_data.status in ['done', 'error'] and job_data.finished_at:
            if job_data.finished_at < cutoff_time:
                jobs_to_remove.append(job_id)
    
    for job_id in jobs_to_remove:
        JOB_STORE.pop(job_id, None)
        RESULT_STORE.pop(job_id, None)
    
    if jobs_to_remove:
        print(f"Cleaned up {len(jobs_to_remove)} old jobs from in-memory cache")
    
    total_jobs = len(JOB_STORE)
    total_results = len(RESULT_STORE)
    print(f"In-memory cache status: {total_jobs} jobs, {total_results} results")

def get_cache_stats():
    """Get cache statistics for monitoring"""
    redis_client = get_redis_client()
    
    if redis_client:
        try:
            info = redis_client.info('memory')
            job_count = len(redis_client.keys("job:*"))
            result_count = len(redis_client.keys("results:*"))
            
            return {
                "backend": "redis",
                "memory_used": info.get('used_memory_human', 'unknown'),
                "job_count": job_count,
                "result_count": result_count,
                "connected": True
            }
        except Exception as e:
            print(f"Redis stats failed ({e})")
    
    return {
        "backend": "in-memory",
        "job_count": len(JOB_STORE),
        "result_count": len(RESULT_STORE),
        "connected": False
    }