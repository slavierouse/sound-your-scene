import uuid
import random
from datetime import datetime
from fastapi import HTTPException, BackgroundTasks
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from api.models import (
    SearchRequest, JobResponse, JobData, JobStatus, 
    ConversationHistory, RefinementStep
)
from api.llm_service import LLMService
from api.music_service import MusicService
from api.storage import store_job, get_job, store_results, get_results, job_exists
from api.session_service import SessionService

# Service instances
llm_service = LLMService()
music_service = MusicService()

def initialize_services():
    """Initialize all services"""
    llm_service.initialize()
    music_service.initialize()

def assign_model_for_ab_test(search_session_id: str) -> str:
    """Assign model for A/B testing based on search session ID for consistency across turns"""
    # Use search_session_id as seed for consistent assignment per search conversation
    random.seed(search_session_id)
    
    # 50/50 split: gemini-2.5-flash vs gemini-2.5-pro
    if random.random() < 0.5:
        return "gemini-2.5-pro"
    else:
        return "gemini-2.5-flash"

async def create_search_job(request: SearchRequest, background_tasks: BackgroundTasks, db: Session = None, client_ip: str = None) -> Dict[str, str]:
    """Create a new search job and start background processing"""
    job_id = str(uuid.uuid4())
    
    # LAYER 1: Generate IDs and assignments with fallbacks (consistent pattern)
    user_session_id = request.user_session_id or str(uuid.uuid4())
    search_session_id = request.search_session_id or str(uuid.uuid4())
    assigned_model = request.model or ("gemini-2.5-pro" if random.random() < 0.5 else "gemini-2.5-flash")
    
    # LAYER 2: Existing in-memory job processing (preserve working functionality)
    job_data = JobData(
        status=JobStatus.QUEUED,
        query_text=request.query_text,
        started_at=datetime.now(),
        finished_at=None,
        error_message=None,
        model=assigned_model,
        conversation_history=request.conversation_history if request.conversation_history else None,
        current_filters_json=None,
        result_count=None
    )
    
    store_job(job_id, job_data)
    
    # LAYER 2: Core search processing (existing working logic)
    background_tasks.add_task(
        process_search_job, 
        job_id, 
        request.query_text, 
        request.conversation_history if request.conversation_history else None,
        request.image_data
    )
    
    # LAYER 3: Database persistence (runs in parallel, captures all attempts)
    background_tasks.add_task(
        async_persist_session_data,
        user_session_id,
        job_id,
        request.query_text,
        request.conversation_history,
        bool(request.image_data),
        client_ip,
        assigned_model,
        search_session_id
    )
    
    # Return immediately - no database blocking
    return {
        "job_id": job_id,
        "user_session_id": user_session_id,
        "search_session_id": search_session_id,
        "model": assigned_model
    }

async def get_job_status(job_id: str) -> JobResponse:
    """Get the status and results of a search job with database fallback"""
    
    # Try in-memory stores first (for active jobs)
    if job_exists(job_id):
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
            conversation_history=job_data.conversation_history,
            model=job_data.model
        )
        
        # Add results if job is complete
        if job_data.status == JobStatus.DONE:
            results = get_results(job_id)
            if results:
                response.results = results
        
        return response
    
    # Fallback: Check database (for completed jobs after server restart)
    try:
        return await get_job_status_from_database(job_id)
    except Exception as e:
        print(f"Database fallback failed for job_id {job_id}: {e}")
        raise HTTPException(status_code=404, detail="Job not found")

async def get_job_status_from_database(job_id: str) -> JobResponse:
    """Reconstruct job status from database (fallback for server restarts)"""
    from api.database import SessionLocal
    from api.db_models import SearchJob, SearchResult
    from api.models import SearchResults, TrackResult, ConversationHistory, RefinementStep
    
    db = SessionLocal()
    try:
        # Get search job record
        search_job = db.query(SearchJob).filter_by(job_id=job_id).first()
        if not search_job:
            raise HTTPException(status_code=404, detail="Job not found in database")
        
        # Reconstruct conversation history from all jobs in the same search session
        all_jobs = db.query(SearchJob).filter_by(
            search_session_id=search_job.search_session_id
        ).order_by(SearchJob.conversation_turn).all()
        
        conversation_history = None
        if all_jobs:
            steps = []
            for job in all_jobs:
                if job.llm_message:  # Only include completed jobs
                    step = RefinementStep(
                        step_number=job.conversation_turn,
                        step_type="initial" if job.conversation_turn == 1 else "user_refine",
                        user_input=job.query_text,
                        filters_json=job.filters_json or {},
                        result_count=job.result_count or 0,
                        user_message=job.llm_message,
                        rationale=job.llm_reflection or "",
                        result_summary={},
                        timestamp=job.created_at,
                        target_range="50-150 results",
                        image_data=None
                    )
                    steps.append(step)
            
            if steps:
                conversation_history = ConversationHistory(
                    original_query=all_jobs[0].query_text,
                    steps=steps,
                    current_step=len(steps),
                    total_auto_refinements=0  # We don't track this in DB
                )
        
        # Build base response from database record
        response = JobResponse(
            job_id=job_id,
            status=JobStatus.DONE if search_job.completed_at else JobStatus.RUNNING,
            query_text=search_job.query_text,
            result_count=search_job.result_count,
            started_at=search_job.created_at,
            finished_at=search_job.completed_at,
            error_message=None,
            conversation_history=conversation_history,
            model=search_job.model_used
        )
        
        # If this specific job is completed and has results, get them
        if search_job.completed_at and search_job.result_count and search_job.result_count > 0:
            search_results = db.query(SearchResult).filter_by(
                job_id=job_id
            ).order_by(SearchResult.rank_position).limit(150).all()
            
            if search_results:
                # Get track data using clean separation approach
                from api.music_service import MusicService
                music_service = MusicService()
                music_service.initialize()
                
                # Step 1: Get spotify track IDs in rank order
                spotify_track_ids = [result.spotify_track_id for result in search_results]
                
                # Step 2: Get immutable track data from music service
                tracks = music_service.get_tracks_by_spotify_ids(spotify_track_ids)
                
                # Step 3: Apply stored rankings from database (merge query-specific data)
                track_dict = {track.spotify_track_id: track for track in tracks}
                final_tracks = []
                
                for result in search_results:
                    if result.spotify_track_id in track_dict:
                        track = track_dict[result.spotify_track_id]
                        # Override with stored rankings from database (source of truth)
                        track.relevance_score = float(result.relevance_score) if result.relevance_score else 0.0
                        track.rank_position = result.rank_position
                        final_tracks.append(track)
                
                tracks = final_tracks
                
                results = SearchResults(
                    job_id=job_id,
                    llm_message=search_job.llm_message or "Results retrieved from database after server restart",
                    llm_reflection=search_job.llm_reflection or "",
                    result_count=len(tracks),
                    tracks=tracks
                )
                response.results = results
        
        return response
        
    finally:
        db.close()

async def process_search_job(job_id: str, query_text: str, existing_conversation_history: Optional[ConversationHistory] = None, image_data: Optional[str] = None):
    """Process a search job with auto-refinement tracking"""
    try:
        # Update job status to running
        job_data = get_job(job_id)
        job_data.status = JobStatus.RUNNING
        
        # Get the assigned model for this job
        assigned_model = job_data.model or "gemini-2.5-flash"
        
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
            filters_json, final_results_df = await run_user_refinement_with_auto_refine(job_id, query_text, conversation_history, assigned_model)
        else:
            # This is initial search - run normal auto-refinement process
            filters_json, final_results_df = await run_auto_refine_with_tracking(job_id, query_text, assigned_model, image_data=image_data)
        
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
        
        # LAYER 3: Update database with search job completion (runs after job is DONE)
        import asyncio
        asyncio.create_task(async_update_search_job_completion(job_id, filters_json, final_results_df))
        
    except Exception as e:
        # Update job with error
        job_data = get_job(job_id)
        job_data.status = JobStatus.ERROR
        job_data.finished_at = datetime.now()
        job_data.error_message = str(e)
        store_job(job_id, job_data)

async def run_auto_refine_with_tracking(job_id: str, user_query: str, assigned_model: str, max_iters: int = 3, image_data: Optional[str] = None):
    """Run auto-refinement with detailed step tracking"""
    TARGET_MIN, TARGET_MAX = 50, 150
    target_range = f"{TARGET_MIN}-{TARGET_MAX}"
    MAX_ITERATIONS = max_iters  # Total iterations including initial
    
    # Step 1: Initial search
    initial_prompt = llm_service.create_initial_prompt(user_query, has_image=bool(image_data))
    filters_json = await llm_service.query_llm(initial_prompt, image_data=image_data, model=assigned_model)
    
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
    
    # Auto-refinement iterations - always do at least 1 refinement for quality
    for i in range(max_iters - 1):
        count = len(current_results)
        
        # Only stop if we're in target range AND we've done at least 1 refinement
        if TARGET_MIN <= count <= TARGET_MAX and i > 0:
            break

        # Create refinement prompt
        refine_prompt = llm_service.create_refine_prompt(
            original_query=user_query,
            previous_filters=current_filters,
            result_summary=summary,
            current_step=i+1,
            max_steps=MAX_ITERATIONS
        )
        
        # Get refined filters
        refined_filters = await llm_service.query_llm(refine_prompt, model=assigned_model)
        
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
        job_data = get_job(job_id)
        assigned_model = job_data.model or "gemini-2.5-flash"
        return await run_auto_refine_with_tracking(job_id, user_feedback, assigned_model)
    
    # Create refine prompt with original query, latest filters, and user feedback
    refine_prompt = llm_service.create_refine_prompt(
        conversation_history.original_query,
        latest_step.filters_json,
        latest_step.result_summary or {},
        user_feedback,
        current_step=1,  # User refinement is always step 1 of a new refinement cycle
        max_steps=3
    )
    
    # Get refined filters from LLM
    job_data = get_job(job_id)
    assigned_model = job_data.model or "gemini-2.5-flash"
    refined_filters = await llm_service.query_llm(refine_prompt, conversation_history, model=assigned_model)
    
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

async def run_user_refinement_with_auto_refine(job_id: str, user_feedback: str, conversation_history: ConversationHistory, assigned_model: str):
    """Handle user refinement with full auto-refinement process"""
    # Get the latest step to understand current state
    latest_step = conversation_history.steps[-1] if conversation_history.steps else None
    
    if not latest_step:
        # If no previous steps, fall back to initial search
        return await run_auto_refine_with_tracking(job_id, user_feedback, assigned_model)
    
    # Step 1: Get initial refinement based on user feedback
    refine_prompt = llm_service.create_refine_prompt(
        conversation_history.original_query,
        latest_step.filters_json,
        latest_step.result_summary or {},
        user_feedback,
        current_step=1,  # User refinement is always step 1 of a new refinement cycle
        max_steps=3
    )
    
    # Get initial refined filters from LLM
    job_data = get_job(job_id)
    assigned_model = job_data.model or "gemini-2.5-flash"
    initial_filters = await llm_service.query_llm(refine_prompt, conversation_history, model=assigned_model)
    
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
        
        # Stop if we're in a good range AND we've done at least 1 refinement
        if TARGET_MIN <= count <= TARGET_MAX and i > 0:
            break
        
        # Create refinement prompt
        target_range = f"{TARGET_MIN}-{TARGET_MAX} results"
        refine_prompt = llm_service.create_refine_prompt(
            conversation_history.original_query,
            current_filters,
            summary,
            f"Auto-refine iteration {i+1} to reach {target_range} (current: {count})",
            current_step=i+2,  # i+2 because this is after the initial user refinement (step 1)
            max_steps=MAX_ITERATIONS+1  # +1 because we have initial user refinement + MAX_ITERATIONS auto-refines
        )
        
        # Get refined filters
        refined_filters = await llm_service.query_llm(refine_prompt, conversation_history, model=assigned_model)
        
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

async def async_update_search_job_completion(job_id: str, filters_json: Dict[str, Any], final_results_df):
    """LAYER 3: Update database with search job completion (runs after job is DONE in JOB_STORE)"""
    try:
        print(f"DEBUG: Starting completion update for job_id: {job_id}")
        
        # Get the completed job data from JOB_STORE
        job_data = get_job(job_id)
        if not job_data or job_data.status != JobStatus.DONE:
            print(f"DEBUG: Job not found or not completed in JOB_STORE: {job_id}")
            return
        
        # Calculate processing time
        processing_time_ms = int((job_data.finished_at - job_data.started_at).total_seconds() * 1000)
        
        # Extract LLM message and reflection from final conversation step
        llm_message = ""
        llm_reflection = ""
        chain_of_thought = ""
        
        if job_data.conversation_history and job_data.conversation_history.steps:
            final_step = job_data.conversation_history.steps[-1]
            llm_message = final_step.user_message or ""
            llm_reflection = final_step.rationale or ""
            # Create chain of thought from all steps
            chain_of_thought = f"Total steps: {len(job_data.conversation_history.steps)}, Auto refinements: {job_data.conversation_history.total_auto_refinements}"
        
        print(f"DEBUG: Extracted data - llm_message: {llm_message[:100]}..., processing_time: {processing_time_ms}ms")
        
        # Calculate result count
        result_count = len(final_results_df)
        
        # Update database (failure-safe)
        from api.database import SessionLocal
        db = SessionLocal()
        try:
            result = SessionService.update_search_job_completion(
                db, job_id, filters_json, llm_message, llm_reflection, 
                chain_of_thought, result_count, processing_time_ms
            )
            if result:
                print(f"DEBUG: Successfully updated search job completion for job_id: {job_id}")
                
                # Store final search results (only results shown to user)
                SessionService.store_search_results(
                    db, job_id, final_results_df
                )
                print(f"DEBUG: Stored {result_count} search results for job_id: {job_id}")
            else:
                print(f"DEBUG: No search job found in database for job_id: {job_id}")
        finally:
            db.close()
    except Exception as db_error:
        # Log but don't propagate database errors
        print(f"Database completion update error (non-fatal): {db_error}")
        import traceback
        traceback.print_exc()

async def async_persist_session_data(
    user_session_id: str,
    job_id: str, 
    query_text: str,
    conversation_history: Optional[ConversationHistory],
    has_image: bool,
    client_ip: str,
    assigned_model: str,
    search_session_id: str
):
    """LAYER 3: Persist session data to database (failure-safe background task)"""
    try:
        from api.database import SessionLocal
        db = SessionLocal()
        
        try:
            # Get or create user session using the EXACT ID from response
            user_session = SessionService.get_or_create_user_session(
                db, user_session_id, client_ip
            )
            
            # Determine if this is a new search session or refinement
            is_new_search = not conversation_history or len(conversation_history.steps) == 0
            
            if is_new_search:
                # Create new search session using provided search_session_id and model
                SessionService.create_search_session(
                    db, user_session.user_session_id, query_text, search_session_id, has_image, assigned_model
                )
                conversation_turn = 1
            else:
                # Refinement: search session already exists, calculate user conversation turn
                # Debug: Print all step types to understand what we're counting
                print(f"DEBUG: All steps in conversation_history:")
                for i, step in enumerate(conversation_history.steps):
                    print(f"  Step {i+1}: type='{step.step_type}', user_input='{step.user_input[:50]}...'")
                
                # Count only user-initiated steps (initial + user_refine), exclude auto_refine
                user_initiated_steps = [
                    step for step in conversation_history.steps 
                    if step.step_type in ["initial", "user_refine"]
                ]
                print(f"DEBUG: User-initiated steps:")
                for i, step in enumerate(user_initiated_steps):
                    print(f"  User step {i+1}: type='{step.step_type}', user_input='{step.user_input[:50]}...'")
                
                # The current user query is already included in conversation_history.steps
                # So len(user_initiated_steps) already counts the current turn we're processing
                # Turn 1: initial query → user_initiated_steps = 1 → conversation_turn = 1  
                # Turn 2: first refinement → user_initiated_steps = 2 → conversation_turn = 2
                conversation_turn = len(user_initiated_steps)
                print(f"DEBUG: User turn calculation - total steps: {len(conversation_history.steps)}, user steps: {len(user_initiated_steps)}, turn: {conversation_turn}")
            
            # Create search job record using the EXACT job_id and model from the API
            print(f"DEBUG: Creating search job - job_id: {job_id}, search_session_id: {search_session_id}")
            search_job = SessionService.create_search_job(
                db, search_session_id, user_session.user_session_id, job_id,
                conversation_turn, query_text, has_image, assigned_model
            )
            if search_job:
                print(f"DEBUG: Successfully created search job with id: {search_job.job_id}")
            else:
                print(f"DEBUG: Failed to create search job")
            
        finally:
            db.close()
            
    except Exception as e:
        # Log error but don't propagate - this is tracking only
        print(f"Database persistence error (non-fatal): {e}")
        return