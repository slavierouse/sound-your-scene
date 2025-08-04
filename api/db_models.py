import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from api.database import Base

def generate_uuid():
    """Generate UUID for primary keys"""
    return str(uuid.uuid4())

class UserSession(Base):
    """User sessions - one per site visit (can contain multiple searches)"""
    __tablename__ = "user_sessions"
    
    user_session_id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    user_id = Column(String, nullable=True)  # IP hash or email when captured
    client_ip = Column(String, nullable=True)  # Raw IP address for analytics
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    search_sessions = relationship("SearchSession", back_populates="user_session")
    playlists = relationship("Playlist", back_populates="user_session")

class SearchSession(Base):
    """Search sessions - one initial query + all its follow-up turns"""
    __tablename__ = "search_sessions"
    
    search_session_id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    user_session_id = Column(UUID(as_uuid=False), ForeignKey("user_sessions.user_session_id"), nullable=False)
    original_query = Column(Text, nullable=False)  # The initial search query
    has_image = Column(Boolean, default=False)  # Whether initial query included image
    model_used = Column(String, nullable=True)  # Model assigned for this search conversation
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships  
    user_session = relationship("UserSession", back_populates="search_sessions")
    search_jobs = relationship("SearchJob", back_populates="search_session")

class SearchJob(Base):
    """Individual turns within a search session (job_id from current system)"""
    __tablename__ = "search_jobs"
    
    job_id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    search_session_id = Column(UUID(as_uuid=False), ForeignKey("search_sessions.search_session_id"), nullable=False)
    user_session_id = Column(UUID(as_uuid=False), nullable=False)  # Denormalized for easy querying
    conversation_turn = Column(Integer, nullable=False)  # 1, 2, 3... within this search session
    query_text = Column(Text, nullable=False)  # Could be initial query or refinement
    has_image = Column(Boolean, default=False)
    model_used = Column(String, nullable=True)  # for A/B testing gemini models
    filters_json = Column(JSONB, nullable=True)
    llm_message = Column(Text, nullable=True)
    llm_reflection = Column(Text, nullable=True)
    chain_of_thought = Column(Text, nullable=True)  # store LLM reasoning
    result_count = Column(Integer, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    search_session = relationship("SearchSession", back_populates="search_jobs")
    search_results = relationship("SearchResult", back_populates="search_job")
    track_events = relationship("TrackEvent", back_populates="search_job")

class SearchResult(Base):
    """All results for each search job - enables HR@K calculations"""
    __tablename__ = "search_results"
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    job_id = Column(UUID(as_uuid=False), ForeignKey("search_jobs.job_id"), nullable=False)
    search_session_id = Column(UUID(as_uuid=False), nullable=False)  # Denormalized
    user_session_id = Column(UUID(as_uuid=False), nullable=False)    # Denormalized
    conversation_turn = Column(Integer, nullable=False)
    spotify_track_id = Column(String, nullable=False)
    rank_position = Column(Integer, nullable=False)  # 1, 2, 3... as ranked by LLM
    relevance_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    search_job = relationship("SearchJob", back_populates="search_results")

class TrackEvent(Base):
    """User interactions with tracks"""
    __tablename__ = "track_events"
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    user_session_id = Column(UUID(as_uuid=False), nullable=False)
    search_session_id = Column(UUID(as_uuid=False), nullable=True)
    job_id = Column(UUID(as_uuid=False), ForeignKey("search_jobs.job_id"), nullable=True)
    spotify_track_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False)  # 'bookmark', 'youtube_click', 'spotify_click', 'play'
    rank_position = Column(Integer, nullable=True)  # what position was this track when interacted with
    conversation_turn = Column(Integer, nullable=True)  # which search turn produced this track
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    search_job = relationship("SearchJob", back_populates="track_events")

class Playlist(Base):
    """Playlists for permalink feature"""
    __tablename__ = "playlists"
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    user_session_id = Column(UUID(as_uuid=False), ForeignKey("user_sessions.user_session_id"), nullable=True)
    track_ids = Column(JSONB, nullable=False)  # array of spotify_track_ids
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    access_count = Column(Integer, default=0)
    
    # Relationships
    user_session = relationship("UserSession", back_populates="playlists")