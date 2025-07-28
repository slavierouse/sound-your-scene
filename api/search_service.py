import uuid
from datetime import datetime
from fastapi import HTTPException, BackgroundTasks
from typing import Dict, Any

from api.models import (
    SearchRequest, JobResponse, JobData, JobStatus, 
    ConversationHistory, RefinementStep
)
from api.llm_service import LLMService
from api.music_service import MusicService
from api.storage import store_job, get_job, store_results, get_results, job_exists

# Service instances
llm_service = LLMService()
music_service = MusicService()

def initialize_services():
    """Initialize all services"""
    llm_service.initialize()
    music_service.initialize()

async def create_search_job(request: SearchRequest, background_tasks: BackgroundTasks) -> Dict[str, str]:
    """Create a new search job and start background processing"""
    job_id = str(uuid.uuid4())
    
    # Create job entry
    job_data = JobData(
        status=JobStatus.QUEUED,
        query_text=request.query_text,
        started_at=datetime.now(),
        finished_at=None,
        error_message=None,
        conversation_history=None,
        current_filters_json=None,
        result_count=None
    )
    
    store_job(job_id, job_data)
    
    # Start background processing
    background_tasks.add_task(process_search_job, job_id, request.query_text)
    
    return {"job_id": job_id}

async def get_job_status(job_id: str) -> JobResponse:
    """Get the status and results of a search job"""
    if not job_exists(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_data = get_job(job_id)
    
    # Build base response
    response = JobResponse(
        job_id=job_id,
        status=job_data.status,
        query_text=job_data.query_text,
        result_count=job_data.result_count,
        started_at=job_data.started_at,
        finished_at=job_data.finished_at,
        error_message=job_data.error_message,
        conversation_history=job_data.conversation_history
    )
    
    # Add results if job is complete
    if job_data.status == JobStatus.DONE:
        results = get_results(job_id)
        if results:
            response.results = results
    
    return response

async def process_search_job(job_id: str, query_text: str):
    """Process a search job with auto-refinement tracking"""
    try:
        # Update job status to running
        job_data = get_job(job_id)
        job_data.status = JobStatus.RUNNING
        
        # Initialize conversation history
        conversation_history = ConversationHistory(
            original_query=query_text,
            steps=[],
            current_step=0,
            total_auto_refinements=0
        )
        job_data.conversation_history = conversation_history
        store_job(job_id, job_data)
        
        # Run auto-refinement process with tracking
        filters_json, final_results_df = await run_auto_refine_with_tracking(job_id, query_text)
        
        # Convert results to API format
        api_results = music_service.convert_to_api_results(final_results_df, filters_json, job_id)
        
        # Update job with completion
        job_data = get_job(job_id)  # Get latest state
        job_data.status = JobStatus.DONE
        job_data.finished_at = datetime.now()
        job_data.current_filters_json = filters_json
        job_data.result_count = len(final_results_df)
        
        store_job(job_id, job_data)
        store_results(job_id, api_results)
        
    except Exception as e:
        # Update job with error
        job_data = get_job(job_id)
        job_data.status = JobStatus.ERROR
        job_data.finished_at = datetime.now()
        job_data.error_message = str(e)
        store_job(job_id, job_data)

async def run_auto_refine_with_tracking(job_id: str, user_query: str, max_iters: int = 3):
    """Run auto-refinement with detailed step tracking"""
    TARGET_MIN, TARGET_MAX = 50, 150
    target_range = f"{TARGET_MIN}-{TARGET_MAX}"
    
    # Step 1: Initial search
    initial_prompt = llm_service.create_initial_prompt(user_query)
    filters_json = await llm_service.query_llm(initial_prompt)
    
    # Get initial results
    search_result = music_service.search(filters_json)
    results_df = search_result["results"]
    summary = search_result["summary"]
    
    # Record initial step
    await add_refinement_step(
        job_id=job_id,
        step_type="initial",
        user_input=user_query,
        filters_json=filters_json,
        result_count=len(results_df),
        result_summary=summary,
        target_range=target_range
    )

    current_filters = filters_json
    current_results = results_df
    
    # Auto-refinement iterations
    for i in range(max_iters - 1):
        count = len(current_results)
        
        if TARGET_MIN <= count <= TARGET_MAX:
            break

        # Create refinement prompt
        refine_prompt = llm_service.create_refine_prompt(
            original_query=user_query,
            previous_filters=current_filters,
            result_summary=summary
        )
        
        # Get refined filters
        refined_filters = await llm_service.query_llm(refine_prompt)
        
        # Get refined results
        refined_search = music_service.search(refined_filters)
        refined_results = refined_search["results"]
        refined_summary = refined_search["summary"]
        
        # Record refinement step
        await add_refinement_step(
            job_id=job_id,
            step_type="auto_refine",
            user_input=f"Auto-refine iteration {i+1} (previous count: {count})",
            filters_json=refined_filters,
            result_count=len(refined_results),
            result_summary=refined_summary,
            target_range=target_range
        )
        
        current_filters = refined_filters
        current_results = refined_results
        summary = refined_summary
    
    # Update total auto refinements
    job_data = get_job(job_id)
    auto_refine_steps = len([s for s in job_data.conversation_history.steps if s.step_type == "auto_refine"])
    job_data.conversation_history.total_auto_refinements = auto_refine_steps
    store_job(job_id, job_data)
    
    return current_filters, current_results

async def add_refinement_step(
    job_id: str,
    step_type: str,
    user_input: str,
    filters_json: Dict[str, Any],
    result_count: int,
    result_summary: Dict[str, Any],
    target_range: str = None
):
    """Add a refinement step to the conversation history"""
    job_data = get_job(job_id)
    
    step_number = len(job_data.conversation_history.steps) + 1
    
    refinement_step = RefinementStep(
        step_number=step_number,
        step_type=step_type,
        user_input=user_input,
        filters_json=filters_json,
        result_count=result_count,
        user_message=filters_json.get("user_message", ""),
        rationale=filters_json.get("reflection", ""),
        result_summary=result_summary,
        timestamp=datetime.now(),
        target_range=target_range
    )
    
    job_data.conversation_history.steps.append(refinement_step)
    job_data.conversation_history.current_step = step_number
    job_data.current_filters_json = filters_json
    
    store_job(job_id, job_data)