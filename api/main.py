from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from api.models import SearchRequest, JobResponse
from api.search_service import create_search_job, get_job_status, initialize_services

from dotenv import load_dotenv
load_dotenv('.env', override=True)

app = FastAPI(title="SoundByMood API", version="1.0.0")

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize data and model on startup"""
    initialize_services()

@app.get("/")
async def root():
    return {"message": "SoundByMood API", "status": "running"}

@app.post("/search")
async def create_search(request: SearchRequest, background_tasks: BackgroundTasks):
    """Create a new search job and process it in the background"""
    return await create_search_job(request, background_tasks)

@app.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """Get the status and results of a search job"""
    return await get_job_status(job_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)