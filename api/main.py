from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
import os
import time
import uuid
import psutil
from datetime import datetime

from api.models import SearchRequest, JobResponse, ImageUploadResponse
from api.search_service import create_search_job, get_job_status, initialize_services
from api.image_service import image_service
from api.database import get_db

from dotenv import load_dotenv
load_dotenv('.env', override=True)

# Generate unique worker ID for this process
WORKER_ID = str(uuid.uuid4())[:8]
print(f"Worker {WORKER_ID} starting up at {datetime.utcnow().isoformat()}")

app = FastAPI(title="SoundByMood API", version="1.0.0")

def check_system_overload():
    """Check if this worker is overloaded based on system resources"""
    # Memory pressure check
    memory_percent = psutil.virtual_memory().percent
    if memory_percent > 90:
        return True, f"High memory usage ({memory_percent}%)"
    
    # CPU pressure check  
    cpu_percent = psutil.cpu_percent(interval=1)
    if cpu_percent > 90:
        return True, f"High CPU usage ({cpu_percent}%)"
    
    return False, None

def check_rate_limit(client_ip: str):
    """Check if client IP has exceeded rate limits"""
    from api.storage import get_redis_client
    
    redis_client = get_redis_client()
    if not redis_client:
        # No rate limiting if Redis unavailable
        return False, None
    
    try:
        # Check limits: 3/minute, 30/hour, 100/day
        # Use hash tags to ensure all keys hash to the same slot in Redis Cluster
        minute_key = f"rate_limit:{{{client_ip}}}:minute"
        hour_key = f"rate_limit:{{{client_ip}}}:hour" 
        day_key = f"rate_limit:{{{client_ip}}}:day"
        
        minute_count = int(redis_client.get(minute_key) or 0)
        hour_count = int(redis_client.get(hour_key) or 0)
        day_count = int(redis_client.get(day_key) or 0)
        
        if minute_count >= 3:
            ttl = redis_client.ttl(minute_key)
            return True, f"Rate limit exceeded: 3 searches per minute. Please wait {ttl} seconds."
        
        if hour_count >= 30:
            ttl = redis_client.ttl(hour_key)
            return True, f"Rate limit exceeded: 30 searches per hour. Please wait {ttl//60} minutes."
        
        if day_count >= 100:
            ttl = redis_client.ttl(day_key)
            return True, f"Rate limit exceeded: 100 searches per day. Please wait {ttl//3600} hours."
        
        # Increment counters
        pipe = redis_client.pipeline()
        pipe.incr(minute_key)
        pipe.expire(minute_key, 60)  # 1 minute
        pipe.incr(hour_key)
        pipe.expire(hour_key, 3600)  # 1 hour
        pipe.incr(day_key)
        pipe.expire(day_key, 86400)  # 24 hours
        pipe.execute()
        
        return False, None
        
    except Exception as e:
        print(f"Rate limit check failed: {e}")
        return False, None  # Allow request if rate limiting fails

# System overload and rate limiting middleware
@app.middleware("http")
async def protection_middleware(request: Request, call_next):
    # Only apply to search endpoint
    if request.url.path == "/search":
        client_ip = request.client.host if request.client else "unknown"
        
        # Check rate limits
        is_rate_limited, rate_limit_msg = check_rate_limit(client_ip)
        if is_rate_limited:
            return JSONResponse(
                status_code=429,
                content={"error": rate_limit_msg},
                headers={"Retry-After": "60"}
            )
        
        # Check system overload
        is_overloaded, overload_msg = check_system_overload()
        if is_overloaded:
            return JSONResponse(
                status_code=503,
                content={"error": f"System temporarily overloaded: {overload_msg}. Please retry in a moment."},
                headers={"Retry-After": "30"}
            )
    
    return await call_next(request)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    timestamp = datetime.utcnow().isoformat()
    
    # Log incoming request
    print(f"[{WORKER_ID}] {timestamp} {request.method} {request.url.path}")
    
    # Process request
    response = await call_next(request)
    
    # Log response with timing
    process_time = round((time.time() - start_time) * 1000, 2)
    print(f"[{WORKER_ID}] {response.status_code} {request.url.path} ({process_time}ms)")
    
    return response

# CORS middleware only in development
environment = os.getenv('ENVIRONMENT', 'development')
if environment == 'development':
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure properly for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Mount static files for frontend assets
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    # Mount assets directory specifically
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    
    # Mount other static files (favicon, etc.)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
else:
    print(f"Warning: Static directory not found at {static_dir}")

@app.on_event("startup")
async def startup_event():
    """Initialize data and model on startup"""
    initialize_services()

@app.on_event("shutdown")
async def shutdown_event():
    """Graceful shutdown - cleanup resources"""
    try:
        from api.database import close_db
        close_db()
        print("Server shutdown complete")
    except Exception as e:
        print(f"Shutdown cleanup error (non-fatal): {e}")

@app.get("/health")
async def health_check():
    """Enhanced health check for load balancer (no database dependency)"""
    try:
        from api.storage import get_cache_stats
        import psutil
        from datetime import datetime
        
        memory_percent = psutil.virtual_memory().percent
        cache_stats = get_cache_stats()
        
        return {
            "status": "healthy",
            "memory_usage": f"{memory_percent}%",
            "cache_backend": cache_stats["backend"],
            "active_jobs": cache_stats["job_count"],
            "cached_results": cache_stats["result_count"],
            "redis_connected": cache_stats["connected"],
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        # Fallback to simple response if monitoring fails
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/")
async def root():
    # Serve the frontend index.html for the root path
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    index_path = os.path.join(static_dir, "index.html")
    
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        print(f"Warning: Frontend index.html not found at {index_path}")
        return {"message": "SoundByMood API", "status": "running", "note": "Frontend not built"}

@app.post("/search")
async def create_search(
    search_request: SearchRequest, 
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db)
):
    """Create a new search job and process it in the background"""
    # Get client IP for user session tracking
    client_ip = request.client.host if request.client else None
    
    return await create_search_job(search_request, background_tasks, db, client_ip)

@app.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """Get the status and results of a search job"""
    return await get_job_status(job_id)

@app.post("/upload-image", response_model=ImageUploadResponse)
async def upload_image(file: UploadFile = File(...)):
    """Upload and validate an image file for search context"""
    try:
        base64_data, temp_file_id = await image_service.validate_and_process_image(file)
        return ImageUploadResponse(
            success=True,
            temp_file_id=temp_file_id,
            base64_data=base64_data,
            message="Image uploaded and validated successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error during image processing")

# Simple playlist endpoints
@app.post("/playlists")
async def create_or_update_playlist(
    request: dict,  # {"track_ids": [...], "search_session_id": "..."}
    db: Session = Depends(get_db)
):
    """Create or update playlist with full track list (belongs to search session)"""
    from api.playlist_service import PlaylistService
    
    track_ids = request.get("track_ids", [])
    search_session_id = request.get("search_session_id")
    
    # Allow empty track_ids to support clearing playlists
    # if not track_ids:
    #     raise HTTPException(status_code=400, detail="track_ids required")
    if not search_session_id:
        raise HTTPException(status_code=400, detail="search_session_id required")
    
    playlist = PlaylistService.create_or_update_playlist(db, search_session_id, track_ids)
    return {"playlist_id": playlist.id, "track_count": len(playlist.track_ids)}

@app.get("/playlists/{playlist_id}")
async def get_playlist(playlist_id: str, db: Session = Depends(get_db)):
    """Get playlist for sharing/export (increments access_count)"""
    from api.playlist_service import PlaylistService
    
    playlist_data = PlaylistService.get_playlist_for_export(db, playlist_id)
    if not playlist_data:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    return playlist_data

@app.post("/track-events")
async def track_event(
    event_data: dict,  # {"event_type": "youtube_click", "spotify_track_id": "...", "user_session_id": "...", ...}
    request: Request,
    db: Session = Depends(get_db)
):
    """Record any kind of user interaction event for analytics"""
    from api.db_models import TrackEvent
    
    try:
        # Extract event data
        event_type = event_data.get("event_type")  # Required: 'bookmark', 'youtube_click', 'spotify_click', 'spotify_embed_play', 'pagination', etc.
        user_session_id = event_data.get("user_session_id")  # Required
        
        # Optional fields
        spotify_track_id = event_data.get("spotify_track_id", "")  # Optional - empty string for non-track events
        search_session_id = event_data.get("search_session_id")
        job_id = event_data.get("job_id")
        rank_position = event_data.get("rank_position")
        conversation_turn = event_data.get("conversation_turn")
        
        # Debug logging
        print(f"Track event - type: {event_type}, job_id: {job_id}, user_session: {user_session_id}")
        print(f"Full event data: {event_data}")
        
        # Validation
        if not event_type:
            raise HTTPException(status_code=400, detail="event_type required")
        if not user_session_id:
            raise HTTPException(status_code=400, detail="user_session_id required")
        
        # Create track event record
        track_event = TrackEvent(
            user_session_id=user_session_id,
            search_session_id=search_session_id,
            job_id=job_id,
            spotify_track_id=spotify_track_id,
            event_type=event_type,
            rank_position=rank_position,
            conversation_turn=conversation_turn
        )
        
        db.add(track_event)
        db.commit()
        
        return {"success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record event: {str(e)}")

@app.post("/playlists/{playlist_id}/email")
async def email_playlist(
    playlist_id: str, 
    request_body: dict,  # {"email": "user@example.com"}
    request: Request,
    db: Session = Depends(get_db)
):
    """Email playlist link to user"""
    from api.playlist_service import PlaylistService
    from api.email_service import email_service
    from api.email_security import email_security
    import os
    
    email = request_body.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="email required")
    
    # Validate email format (basic)
    if "@" not in email or "." not in email:
        raise HTTPException(status_code=400, detail="Invalid email format")
    
    # Get client IP for security checks
    client_ip = request.client.host if request.client else None
    
    # Security checks: rate limiting and abuse prevention
    is_allowed, security_error = email_security.check_rate_limits(db, client_ip, email)
    if not is_allowed:
        raise HTTPException(status_code=429, detail=security_error)
    
    # Check if playlist exists
    playlist_data = PlaylistService.get_playlist_for_export(db, playlist_id)
    if not playlist_data:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    # Generate playlist URL
    domain = os.getenv('FRONTEND_URL', 'http://localhost:5173')
    playlist_url = f"{domain}/playlist/{playlist_id}"
    
    # Send email and record in database
    try:
        success = email_service.send_playlist_email(db, playlist_id, email, playlist_url, client_ip)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send email")
        
        return {"success": True, "message": "Email sent successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email service error: {str(e)}")

@app.get("/stats")
async def get_dashboard_metrics(db: Session = Depends(get_db)):
    """Get all performance metrics for dashboard"""
    from api.dashboard_service import DashboardService
    
    try:
        data = DashboardService.get_all_dashboard_data(db)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard metrics error: {str(e)}")

# Catch-all route for frontend (must be last)
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Serve frontend for any non-API routes (SPA routing)"""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    index_path = os.path.join(static_dir, "index.html")
    
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        print(f"Warning: Frontend index.html not found at {index_path}")
        raise HTTPException(status_code=404, detail="Frontend not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)