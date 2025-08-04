from sqlalchemy.orm import Session
from sqlalchemy import text, func
from api.db_models import UserSession, SearchSession, SearchJob, SearchResult, TrackEvent, Playlist, EmailSend
from typing import Dict, List, Any
import json

class DashboardService:
    """Service for generating performance metrics dashboard data"""
    
    @staticmethod
    def get_volume_metrics(db: Session) -> Dict[str, int]:
        """Get top-row volume metrics"""
        
        # Count unique users (distinct user_session_ids)
        users = db.query(func.count(func.distinct(UserSession.user_session_id))).scalar() or 0
        
        # Count user sessions 
        user_sessions = db.query(func.count(UserSession.user_session_id)).scalar() or 0
        
        # Count search sessions
        search_sessions = db.query(func.count(SearchSession.search_session_id)).scalar() or 0
        
        # Count search jobs
        search_jobs = db.query(func.count(SearchJob.job_id)).scalar() or 0
        
        # Count playlists
        playlists = db.query(func.count(Playlist.id)).scalar() or 0
        
        # Count successful emails sent
        emails_sent = db.query(func.count(EmailSend.id)).filter(EmailSend.success == True).scalar() or 0
        
        # Count unique email addresses
        unique_emails = db.query(func.count(func.distinct(EmailSend.email_address))).filter(EmailSend.success == True).scalar() or 0
        
        return {
            "users": users,
            "user_sessions": user_sessions, 
            "search_sessions": search_sessions,
            "search_jobs": search_jobs,
            "playlists": playlists,
            "emails_sent": emails_sent,
            "unique_emails": unique_emails
        }
    
    @staticmethod
    def get_hr_at_k_data(db: Session) -> List[Dict[str, Any]]:
        """Calculate Hit Rate @ K for positions 1-10
        HR@K = fraction of queries where user found at least one hit in top K positions
        """
        
        # Define hit event types (including new bookmark events)
        hit_events = ['spotify_click', 'youtube_click', 'spotify_embed_play', 'bookmark_added']
        hit_events_str = "','".join(hit_events)
        
        query = text(f"""
        WITH job_hits AS (
            SELECT DISTINCT
                sr.job_id,
                sr.rank_position
            FROM search_results sr
            JOIN track_events te ON sr.spotify_track_id = te.spotify_track_id 
                                AND sr.job_id = te.job_id
            WHERE te.event_type IN ('{hit_events_str}')
              AND sr.rank_position <= 10
        ),
        hr_at_k AS (
            SELECT 
                k,
                COUNT(DISTINCT CASE WHEN jh.rank_position <= k THEN jh.job_id END) * 1.0 / 
                COUNT(DISTINCT sj.job_id) as hr_at_k
            FROM search_jobs sj
            CROSS JOIN generate_series(1, 10) as k
            LEFT JOIN job_hits jh ON sj.job_id = jh.job_id
            GROUP BY k
        )
        SELECT k, COALESCE(hr_at_k, 0) as hr_at_k
        FROM hr_at_k 
        ORDER BY k
        """)
        
        result = db.execute(query).fetchall()
        return [{"k": r.k, "hr_at_k": float(r.hr_at_k)} for r in result]
    
    @staticmethod
    def get_latency_cdf_data(db: Session) -> List[Dict[str, Any]]:
        """Calculate latency CDF from search start to results loaded"""
        
        query = text("""
        WITH latency_data AS (
            SELECT 
                processing_time_ms / 1000.0 as latency_seconds
            FROM search_jobs 
            WHERE processing_time_ms IS NOT NULL
              AND completed_at IS NOT NULL
        ),
        latency_percentiles AS (
            SELECT 
                latency_seconds,
                PERCENT_RANK() OVER (ORDER BY latency_seconds) as percentile
            FROM latency_data
        )
        SELECT 
            latency_seconds,
            percentile
        FROM latency_percentiles
        ORDER BY latency_seconds
        """)
        
        result = db.execute(query).fetchall()
        return [{"latency_seconds": float(r.latency_seconds), "percentile": float(r.percentile)} for r in result]
    
    @staticmethod
    def get_hr_by_conversation_turn(db: Session) -> Dict[str, List[Dict[str, Any]]]:
        """HR@K data segmented by conversation turn"""
        
        hit_events = ['spotify_click', 'youtube_click', 'spotify_embed_play', 'bookmark_added']
        hit_events_str = "','".join(hit_events)
        
        query = text(f"""
        WITH hit_data AS (
            SELECT 
                sr.rank_position,
                sr.conversation_turn,
                CASE WHEN te.event_type IN ('{hit_events_str}') THEN 1 ELSE 0 END as is_hit
            FROM search_results sr
            LEFT JOIN track_events te ON sr.spotify_track_id = te.spotify_track_id 
                                      AND sr.job_id = te.job_id
            WHERE sr.rank_position <= 10
        ),
        hr_by_turn AS (
            SELECT 
                conversation_turn,
                k,
                COUNT(CASE WHEN is_hit = 1 AND rank_position <= k THEN 1 END) * 1.0 / 
                COUNT(CASE WHEN rank_position <= k THEN 1 END) as hr_at_k
            FROM hit_data
            CROSS JOIN generate_series(1, 10) as k
            GROUP BY conversation_turn, k
        )
        SELECT conversation_turn, k, COALESCE(hr_at_k, 0) as hr_at_k
        FROM hr_by_turn 
        ORDER BY conversation_turn, k
        """)
        
        result = db.execute(query).fetchall()
        
        # Group by conversation turn
        data_by_turn = {}
        for r in result:
            turn = f"Turn {r.conversation_turn}"
            if turn not in data_by_turn:
                data_by_turn[turn] = []
            data_by_turn[turn].append({"k": r.k, "hr_at_k": float(r.hr_at_k)})
        
        return data_by_turn
    
    @staticmethod
    def get_hr_by_model(db: Session) -> Dict[str, List[Dict[str, Any]]]:
        """HR@K data segmented by model"""
        
        hit_events = ['spotify_click', 'youtube_click', 'spotify_embed_play', 'bookmark_added']
        hit_events_str = "','".join(hit_events)
        
        query = text(f"""
        WITH hit_data AS (
            SELECT 
                sr.rank_position,
                sj.model_used,
                CASE WHEN te.event_type IN ('{hit_events_str}') THEN 1 ELSE 0 END as is_hit
            FROM search_results sr
            JOIN search_jobs sj ON sr.job_id = sj.job_id
            LEFT JOIN track_events te ON sr.spotify_track_id = te.spotify_track_id 
                                      AND sr.job_id = te.job_id
            WHERE sr.rank_position <= 10
              AND sj.model_used IS NOT NULL
        ),
        hr_by_model AS (
            SELECT 
                model_used,
                k,
                COUNT(CASE WHEN is_hit = 1 AND rank_position <= k THEN 1 END) * 1.0 / 
                COUNT(CASE WHEN rank_position <= k THEN 1 END) as hr_at_k
            FROM hit_data
            CROSS JOIN generate_series(1, 10) as k
            GROUP BY model_used, k
        )
        SELECT model_used, k, COALESCE(hr_at_k, 0) as hr_at_k
        FROM hr_by_model 
        ORDER BY model_used, k
        """)
        
        result = db.execute(query).fetchall()
        
        # Group by model
        data_by_model = {}
        for r in result:
            model = r.model_used or "Unknown"
            if model not in data_by_model:
                data_by_model[model] = []
            data_by_model[model].append({"k": r.k, "hr_at_k": float(r.hr_at_k)})
        
        return data_by_model
    
    @staticmethod
    def get_hr_by_hit_component(db: Session) -> Dict[str, List[Dict[str, Any]]]:
        """HR@K data segmented by hit component type"""
        
        hit_events = ['spotify_click', 'youtube_click', 'spotify_embed_play', 'bookmark_added']
        
        all_data = {}
        
        for event_type in hit_events:
            query = text(f"""
            WITH hit_data AS (
                SELECT 
                    sr.rank_position,
                    CASE WHEN te.event_type = '{event_type}' THEN 1 ELSE 0 END as is_hit
                FROM search_results sr
                LEFT JOIN track_events te ON sr.spotify_track_id = te.spotify_track_id 
                                          AND sr.job_id = te.job_id
                WHERE sr.rank_position <= 10
            ),
            hr_at_k AS (
                SELECT 
                    k,
                    COUNT(CASE WHEN is_hit = 1 AND rank_position <= k THEN 1 END) * 1.0 / 
                    COUNT(CASE WHEN rank_position <= k THEN 1 END) as hr_at_k
                FROM hit_data
                CROSS JOIN generate_series(1, 10) as k
                GROUP BY k
            )
            SELECT k, COALESCE(hr_at_k, 0) as hr_at_k
            FROM hr_at_k 
            ORDER BY k
            """)
            
            result = db.execute(query).fetchall()
            all_data[event_type] = [{"k": r.k, "hr_at_k": float(r.hr_at_k)} for r in result]
        
        return all_data
    
    @staticmethod
    def get_all_dashboard_data(db: Session) -> Dict[str, Any]:
        """Get all dashboard data in a single API call"""
        
        try:
            volume_metrics = DashboardService.get_volume_metrics(db)
            hr_at_k = DashboardService.get_hr_at_k_data(db)
            latency_cdf = DashboardService.get_latency_cdf_data(db)
            hr_by_turn = DashboardService.get_hr_by_conversation_turn(db)
            hr_by_model = DashboardService.get_hr_by_model(db)
            hr_by_component = DashboardService.get_hr_by_hit_component(db)
            
            return {
                "volume_metrics": volume_metrics,
                "performance_charts": {
                    "hr_at_k": hr_at_k,
                    "latency_cdf": latency_cdf
                },
                "segmented_charts": {
                    "by_conversation_turn": hr_by_turn,
                    "by_model": hr_by_model,
                    "by_hit_component": hr_by_component
                }
            }
        except Exception as e:
            print(f"Dashboard service error: {e}")
            # Return empty data structure on error
            return {
                "volume_metrics": {
                    "users": 0, "user_sessions": 0, "search_sessions": 0,
                    "search_jobs": 0, "playlists": 0, "emails_sent": 0, "unique_emails": 0
                },
                "performance_charts": {
                    "hr_at_k": [], 
                    "latency_cdf": []
                },
                "segmented_charts": {
                    "by_conversation_turn": {}, "by_model": {}, "by_hit_component": {}
                }
            }