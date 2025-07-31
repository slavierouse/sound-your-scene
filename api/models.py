from pydantic import BaseModel, create_model
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"
    CANCELED = "canceled"

# Basic request/response models
class SearchRequest(BaseModel):
    query_text: str
    conversation_history: Optional['ConversationHistory'] = None
    image_data: Optional[str] = None  # Base64 encoded image data

class RefineRequest(BaseModel):
    job_id: str
    feedback: str

# Conversation models for LLM interactions
class RefinementStep(BaseModel):
    step_number: int
    step_type: str  # "initial", "auto_refine", "user_refine"
    user_input: str  # original query or user feedback
    filters_json: Dict[str, Any]  # LLM's filter response
    result_count: int
    user_message: str  # LLM's explanation to user
    rationale: str    # LLM's reflection/reasoning
    result_summary: Optional[Dict[str, Any]] = None  # summary for next refinement
    timestamp: datetime
    target_range: Optional[str] = None  # e.g. "50-150 results"
    image_data: Optional[str] = None  # Base64 encoded image data for this step

class ConversationHistory(BaseModel):
    original_query: str
    steps: List[RefinementStep]
    current_step: int
    total_auto_refinements: int

# Results models - based on actual CSV columns
class TrackResult(BaseModel):
    # Core identifiers
    spotify_track_id: str
    track: str
    artist: str
    
    # Basic metadata
    album_release_year: int
    spotify_artist_genres: Optional[str]
    track_is_explicit: bool
    duration_ms: int
    
    # URLs
    url_youtube: Optional[str]
    spotify_url: str  # Generated from track_id
    
    # Audio features (deciles)
    danceability_decile: int
    energy_decile: int
    #speechiness_decile: int
    acousticness_decile: int
    instrumentalness_decile: int
    liveness_decile: int
    valence_decile: int
    views_decile: int
    
    # Raw views count for better sorting
    views: Optional[int] = None
    
    # Direct audio features
    loudness: float
    tempo: float
    instrumentalness: float
    
    # Computed relevance
    relevance_score: float
    rank_position: int

class SearchResults(BaseModel):
    job_id: str
    result_count: int
    tracks: List[TrackResult]
    llm_message: Optional[str]  # The user_message from LLM response
    llm_reflection: Optional[str]  # The reflection from LLM response

# Job status response
class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    query_text: str
    result_count: Optional[int] = None
    started_at: datetime
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    # When job is done
    results: Optional[SearchResults] = None
    conversation_history: Optional[ConversationHistory] = None

# Internal job storage model
class JobData(BaseModel):
    status: JobStatus
    query_text: str
    started_at: datetime
    finished_at: Optional[datetime]
    error_message: Optional[str]
    
    # Conversation and processing state
    conversation_history: Optional[ConversationHistory]
    current_filters_json: Optional[Dict[str, Any]]
    result_count: Optional[int]

# Dynamic filters model - recreated from notebook logic
def create_filters_model():
    """Create the dynamic Pydantic model for LLM filters"""
    deciles_features_list = ['danceability', 'energy','acousticness', 'liveness', 'valence','views'] #'speechiness'
    direct_use_features = ['loudness','tempo','duration_ms', 'instrumentalness']
    
    fields = {}
    
    # Decile features
    for feature in deciles_features_list:
        fields[feature+"_min_decile"] = (int, 0)
        fields[feature+"_max_decile"] = (int, 10)
        fields[feature+"_decile_weight"] = (int, 0)
    
    # Direct use features  
    for feature in direct_use_features:
        fields[feature+"_min"] = (int, -100)
        fields[feature+"_max"] = (int, 99999999)
        fields[feature+"_decile_weight"] = (int, 0)

    fields["instrumentalness_min"] = (float, 0.0)
    fields["instrumentalness_max"] = (float, 1.0)
    
    # Min/max only features
    fields['album_release_year_min'] = (int, 1900)
    fields['album_release_year_max'] = (int, 2025)
    fields['track_is_explicit_min'] = (int, 0)
    fields['track_is_explicit_max'] = (int, 1)
    
    # String features
    fields['spotify_artist_genres_include_any'] = (str, '')
    fields['spotify_artist_genres_exclude_any'] = (str, '')
    fields['spotify_artist_genres_boosted'] = (str, '')
    
    # LLM metadata
    fields['debug_tag'] = (str, '')
    fields['reflection'] = (str, '')
    fields['user_message'] = (str, '')
    
    return create_model("FiltersModel", **fields)

# Create the filters model
FiltersModel = create_filters_model()

# Image upload response model
class ImageUploadResponse(BaseModel):
    success: bool
    temp_file_id: str
    base64_data: str
    message: str