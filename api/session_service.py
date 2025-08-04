"""
Service for managing user sessions, search sessions, and database persistence
"""
import uuid
from datetime import datetime
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from api.database import get_db
from api.db_models import UserSession, SearchSession, SearchJob
import hashlib

class SessionService:
    
    @staticmethod
    def create_user_session(db: Session, user_session_id: str = None, request_ip: str = None) -> UserSession:
        """Create a new user session with specific ID"""
        user_id = None
        if request_ip:
            # Hash IP for privacy
            user_id = hashlib.sha256(request_ip.encode()).hexdigest()[:16]
        
        user_session = UserSession(
            user_session_id=user_session_id or str(uuid.uuid4()),
            user_id=user_id,
            client_ip=request_ip
        )
        db.add(user_session)
        db.commit()
        db.refresh(user_session)
        return user_session
    
    @staticmethod
    def get_or_create_user_session(db: Session, user_session_id: str = None, request_ip: str = None) -> UserSession:
        """Get existing user session or create new one with specific ID"""
        if user_session_id:
            user_session = db.query(UserSession).filter_by(user_session_id=user_session_id).first()
            if user_session:
                # Update last activity
                user_session.last_activity = datetime.utcnow()
                db.commit()
                return user_session
        
        # Create new session with the provided ID (or generate new one)
        return SessionService.create_user_session(db, user_session_id, request_ip)
    
    @staticmethod
    def create_search_session(db: Session, user_session_id: str, original_query: str, search_session_id: str = None, has_image: bool = False, model_used: str = None) -> SearchSession:
        """Create a new search session with specific ID"""
        search_session = SearchSession(
            search_session_id=search_session_id or str(uuid.uuid4()),
            user_session_id=user_session_id,
            original_query=original_query,
            has_image=has_image,
            model_used=model_used
        )
        db.add(search_session)
        db.commit()
        db.refresh(search_session)
        return search_session
    
    @staticmethod
    def create_search_job(
        db: Session,
        search_session_id: str,
        user_session_id: str,
        job_id: str,
        conversation_turn: int,
        query_text: str,
        has_image: bool = False,
        model_used: str = None
    ) -> SearchJob:
        """Create a search job (one per turn in conversation)"""
        search_job = SearchJob(
            job_id=job_id,
            search_session_id=search_session_id,
            user_session_id=user_session_id,
            conversation_turn=conversation_turn,
            query_text=query_text,
            has_image=has_image,
            model_used=model_used or "gemini-2.5-flash"
        )
        db.add(search_job)
        db.commit()
        db.refresh(search_job)
        return search_job
    
    @staticmethod
    def update_search_job_completion(
        db: Session,
        job_id: str,
        filters_json: dict,
        llm_message: str,
        llm_reflection: str,
        chain_of_thought: str,
        result_count: int,
        processing_time_ms: int
    ):
        """Update search job with completion data"""
        search_job = db.query(SearchJob).filter_by(job_id=job_id).first()
        if search_job:
            search_job.filters_json = filters_json
            search_job.llm_message = llm_message
            search_job.llm_reflection = llm_reflection
            search_job.chain_of_thought = chain_of_thought
            search_job.result_count = result_count
            search_job.processing_time_ms = processing_time_ms
            search_job.completed_at = datetime.utcnow()
            db.commit()
            return search_job
        return None
    
    @staticmethod
    def store_search_results(db: Session, job_id: str, final_results_df):
        """Store final search results (only results shown to user)"""
        # Get search job to extract metadata
        search_job = db.query(SearchJob).filter_by(job_id=job_id).first()
        if not search_job:
            return
        
        # Sort by relevance score (same as API results) and take top 150
        sorted_results = final_results_df.sort_values("relevance_score", ascending=False).head(150)
        
        # Store each result with rank position
        from api.db_models import SearchResult
        for rank, (_, row) in enumerate(sorted_results.iterrows(), 1):
            search_result = SearchResult(
                job_id=job_id,
                search_session_id=search_job.search_session_id,
                user_session_id=search_job.user_session_id,
                conversation_turn=search_job.conversation_turn,
                spotify_track_id=row["spotify_track_id"],
                rank_position=rank,
                relevance_score=float(row["relevance_score"])
            )
            db.add(search_result)
        
        db.commit()