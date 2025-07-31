import uuid
from datetime import datetime
from fastapi import HTTPException, BackgroundTasks
from typing import Dict, Any, Optional

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
    
    # Create job entry with fallback for conversation history
    job_data = JobData(
        status=JobStatus.QUEUED,
        query_text=request.query_text,
        started_at=datetime.now(),
        finished_at=None,
        error_message=None,
        conversation_history=request.conversation_history if request.conversation_history else None,
        current_filters_json=None,
        result_count=None
    )
    
    store_job(job_id, job_data)
    
    # Start background processing with fallback
    background_tasks.add_task(
        process_search_job, 
        job_id, 
        request.query_text, 
        request.conversation_history if request.conversation_history else None,
        request.image_data
    )
    
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

async def process_search_job(job_id: str, query_text: str, existing_conversation_history: Optional[ConversationHistory] = None, image_data: Optional[str] = None):
    """Process a search job with auto-refinement tracking"""
    try:
        # Update job status to running
        job_data = get_job(job_id)
        job_data.status = JobStatus.RUNNING
        
        # Initialize or use existing conversation history
        if existing_conversation_history:
            # Continue existing conversation
            conversation_history = existing_conversation_history
            # Update original query if this is a new refinement
            if not conversation_history.steps:
                conversation_history.original_query = query_text
        else:
            # Start new conversation
            conversation_history = ConversationHistory(
                original_query=query_text,
                steps=[],
                current_step=0,
                total_auto_refinements=0
            )
        
        job_data.conversation_history = conversation_history
        store_job(job_id, job_data)
        
        # Determine if this is a refinement or initial search
        is_refinement = existing_conversation_history and len(existing_conversation_history.steps) > 0
        
        if is_refinement:
            # This is a user refinement - still run full auto-refinement process
            filters_json, final_results_df = await run_user_refinement_with_auto_refine(job_id, query_text, conversation_history)
        else:
            # This is initial search - run normal auto-refinement process
            filters_json, final_results_df = await run_auto_refine_with_tracking(job_id, query_text, image_data=image_data)
        
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

async def run_auto_refine_with_tracking(job_id: str, user_query: str, max_iters: int = 3, image_data: Optional[str] = None):
    """Run auto-refinement with detailed step tracking"""
    TARGET_MIN, TARGET_MAX = 50, 150
    target_range = f"{TARGET_MIN}-{TARGET_MAX}"
    
    # Step 1: Initial search
    initial_prompt = llm_service.create_initial_prompt(user_query, has_image=bool(image_data))
    filters_json = await llm_service.query_llm(initial_prompt, image_data=image_data)
    
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
        target_range=target_range,
        image_data=image_data
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
        
        # Get image data from initial step if it exists
        job_data = get_job(job_id)
        initial_image_data = None
        if job_data.conversation_history and job_data.conversation_history.steps:
            # Look for image data in the first step (initial query)
            first_step = job_data.conversation_history.steps[0]
            if first_step.step_type == "initial" and first_step.image_data:
                initial_image_data = first_step.image_data
        
        # Record refinement step
        await add_refinement_step(
            job_id=job_id,
            step_type="auto_refine",
            user_input=f"Auto-refine iteration {i+1} (previous count: {count})",
            filters_json=refined_filters,
            result_count=len(refined_results),
            result_summary=refined_summary,
            target_range=target_range,
            image_data=initial_image_data
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

async def run_user_refinement(job_id: str, user_feedback: str, conversation_history: ConversationHistory):
    """Handle user refinement using the refine prompt paradigm"""
    # Get the latest step to understand current state
    latest_step = conversation_history.steps[-1] if conversation_history.steps else None
    
    if not latest_step:
        # If no previous steps, fall back to initial search
        return await run_auto_refine_with_tracking(job_id, user_feedback)
    
    # Create refine prompt with original query, latest filters, and user feedback
    refine_prompt = llm_service.create_refine_prompt(
        conversation_history.original_query,
        latest_step.filters_json,
        latest_step.result_summary or {},
        user_feedback
    )
    
    # Get refined filters from LLM
    refined_filters = await llm_service.query_llm(refine_prompt, conversation_history)
    
    # Search with refined filters
    refined_search = music_service.search(refined_filters)
    df_with_scores = refined_search['results']
    
    # Get image data from initial step if it exists
    initial_image_data = None
    if conversation_history.steps:
        # Look for image data in the first step (initial query)
        first_step = conversation_history.steps[0]
        if first_step.step_type == "initial" and first_step.image_data:
            initial_image_data = first_step.image_data
    
    # Create new refinement step
    new_step = RefinementStep(
        step_number=len(conversation_history.steps) + 1,
        step_type="user_refine",
        user_input=user_feedback,
        filters_json=refined_filters,
        result_count=len(df_with_scores),
        user_message=refined_filters.get('user_message', ''),
        rationale=refined_filters.get('reflection', ''),
        result_summary={"top_results": df_with_scores.head(10).to_dict('records') if len(df_with_scores) > 0 else []},
        timestamp=datetime.now(),
        image_data=initial_image_data
    )
    
    # Add step to conversation history
    conversation_history.steps.append(new_step)
    conversation_history.current_step = new_step.step_number
    
    # Update job with new conversation history
    job_data = get_job(job_id)
    job_data.conversation_history = conversation_history
    store_job(job_id, job_data)
    
    return refined_filters, df_with_scores

async def run_user_refinement_with_auto_refine(job_id: str, user_feedback: str, conversation_history: ConversationHistory):
    """Handle user refinement with full auto-refinement process"""
    # Get the latest step to understand current state
    latest_step = conversation_history.steps[-1] if conversation_history.steps else None
    
    if not latest_step:
        # If no previous steps, fall back to initial search
        return await run_auto_refine_with_tracking(job_id, user_feedback)
    
    # Step 1: Get initial refinement based on user feedback
    refine_prompt = llm_service.create_refine_prompt(
        conversation_history.original_query,
        latest_step.filters_json,
        latest_step.result_summary or {},
        user_feedback
    )
    
    # Get initial refined filters from LLM
    initial_filters = await llm_service.query_llm(refine_prompt, conversation_history)
    
    # Search with initial refined filters
    initial_search = music_service.search(initial_filters)
    current_results = initial_search['results']
    summary = initial_search["summary"]
    
    # Get image data from initial step if it exists
    job_data = get_job(job_id)
    initial_image_data = None
    if job_data.conversation_history and job_data.conversation_history.steps:
        # Look for image data in the first step (initial query)
        first_step = job_data.conversation_history.steps[0]
        if first_step.step_type == "initial" and first_step.image_data:
            initial_image_data = first_step.image_data
    
    # Record initial refinement step
    await add_refinement_step(
        job_id=job_id,
        step_type="user_refine",
        user_input=user_feedback,
        filters_json=initial_filters,
        result_count=len(current_results),
        result_summary=summary,
        target_range="50-150 results",
        image_data=initial_image_data
    )
    
    # Step 2-4: Run auto-refinement iterations like initial search
    MAX_ITERATIONS = 2  # 2 more iterations after initial user refinement
    current_filters = initial_filters
    
    for i in range(MAX_ITERATIONS):
        count = len(current_results)
        TARGET_MIN, TARGET_MAX = 50, 150
        
        # Stop if we're in a good range
        if TARGET_MIN <= count <= TARGET_MAX:
            break
        
        # Create refinement prompt
        target_range = f"{TARGET_MIN}-{TARGET_MAX} results"
        refine_prompt = llm_service.create_refine_prompt(
            conversation_history.original_query,
            current_filters,
            summary,
            f"Auto-refine iteration {i+1} to reach {target_range} (current: {count})"
        )
        
        # Get refined filters
        refined_filters = await llm_service.query_llm(refine_prompt, conversation_history)
        
        # Get refined results
        refined_search = music_service.search(refined_filters)
        refined_results = refined_search["results"]
        refined_summary = refined_search["summary"]
        
        # Get image data from initial step if it exists
        job_data = get_job(job_id)
        initial_image_data = None
        if job_data.conversation_history and job_data.conversation_history.steps:
            # Look for image data in the first step (initial query)
            first_step = job_data.conversation_history.steps[0]
            if first_step.step_type == "initial" and first_step.image_data:
                initial_image_data = first_step.image_data
        
        # Record refinement step
        await add_refinement_step(
            job_id=job_id,
            step_type="auto_refine",
            user_input=f"Auto-refine iteration {i+1} after user feedback (previous count: {count})",
            filters_json=refined_filters,
            result_count=len(refined_results),
            result_summary=refined_summary,
            target_range=target_range,
            image_data=initial_image_data
        )
        
        current_filters = refined_filters
        current_results = refined_results
        summary = refined_summary
    
    # Update total auto refinements in conversation history
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
    target_range: str = None,
    image_data: Optional[str] = None
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
        target_range=target_range,
        image_data=image_data
    )
    
    job_data.conversation_history.steps.append(refinement_step)
    job_data.conversation_history.current_step = step_number
    job_data.current_filters_json = filters_json
    
    store_job(job_id, job_data)