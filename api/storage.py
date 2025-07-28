from typing import Dict, List
from api.models import JobData, SearchResults

# In-memory stores
JOB_STORE: Dict[str, JobData] = {}
RESULT_STORE: Dict[str, SearchResults] = {}

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