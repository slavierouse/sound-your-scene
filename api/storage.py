from typing import Dict, List
from datetime import datetime, timedelta
from api.models import JobData, SearchResults

# In-memory stores
JOB_STORE: Dict[str, JobData] = {}
RESULT_STORE: Dict[str, SearchResults] = {}

# Cache cleanup settings
CACHE_RETENTION_HOURS = 1  # Keep completed jobs for 1 hour

def store_job(job_id: str, job_data: JobData):
    """Store job data"""
    JOB_STORE[job_id] = job_data

def get_job(job_id: str) -> JobData:
    """Get job data by ID"""
    return JOB_STORE.get(job_id)

def store_results(job_id: str, results: SearchResults):
    """Store search results"""
    RESULT_STORE[job_id] = results

def get_results(job_id: str) -> SearchResults:
    """Get search results by job ID"""
    return RESULT_STORE.get(job_id)

def job_exists(job_id: str) -> bool:
    """Check if job exists"""
    return job_id in JOB_STORE

def cleanup_old_jobs():
    """Remove completed jobs older than CACHE_RETENTION_HOURS"""
    cutoff_time = datetime.now() - timedelta(hours=CACHE_RETENTION_HOURS)
    
    # Find jobs to remove
    jobs_to_remove = []
    for job_id, job_data in JOB_STORE.items():
        # Only clean up completed jobs (DONE or ERROR status)
        if job_data.status in ['done', 'error'] and job_data.finished_at:
            if job_data.finished_at < cutoff_time:
                jobs_to_remove.append(job_id)
    
    # Remove old jobs and their results
    for job_id in jobs_to_remove:
        JOB_STORE.pop(job_id, None)
        RESULT_STORE.pop(job_id, None)
    
    if jobs_to_remove:
        print(f"🧹 Cleaned up {len(jobs_to_remove)} old jobs from cache")
    
    # Log cache size for monitoring
    total_jobs = len(JOB_STORE)
    total_results = len(RESULT_STORE)
    print(f"📊 Cache status: {total_jobs} jobs, {total_results} results")