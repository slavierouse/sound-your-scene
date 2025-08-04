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
        """Calculate Hit Rate @ K for positions 1-10 with 95% confidence intervals
        HR@K = fraction of queries where user found at least one hit in top K positions
        """
        
        # Define hit event types (including new bookmark events)
        hit_events = ['spotify_click', 'youtube_click', 'spotify_embed_play', 'bookmark_added_click']
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
                COUNT(DISTINCT CASE WHEN jh.rank_position <= k THEN jh.job_id END) as hits,
                COUNT(DISTINCT sj.job_id) as total_jobs,
                COUNT(DISTINCT CASE WHEN jh.rank_position <= k THEN jh.job_id END) * 1.0 / 
                COUNT(DISTINCT sj.job_id) as hr_at_k
            FROM search_jobs sj
            CROSS JOIN generate_series(1, 10) as k
            LEFT JOIN job_hits jh ON sj.job_id = jh.job_id
            GROUP BY k
        )
        SELECT 
            k, 
            COALESCE(hr_at_k, 0) as hr_at_k,
            hits,
            total_jobs,
            -- Calculate 95% confidence interval using normal approximation
            CASE 
                WHEN total_jobs >= 5 AND hr_at_k > 0.01 AND hr_at_k < 0.99 THEN
                    GREATEST(0, hr_at_k - 1.96 * SQRT(hr_at_k * (1 - hr_at_k) / total_jobs))
                ELSE hr_at_k
            END as ci_lower,
            CASE 
                WHEN total_jobs >= 5 AND hr_at_k > 0.01 AND hr_at_k < 0.99 THEN
                    LEAST(1, hr_at_k + 1.96 * SQRT(hr_at_k * (1 - hr_at_k) / total_jobs))
                ELSE hr_at_k
            END as ci_upper
        FROM hr_at_k 
        ORDER BY k
        """)
        
        result = db.execute(query).fetchall()
        return [{
            "k": r.k, 
            "hr_at_k": float(r.hr_at_k),
            "ci_lower": float(r.ci_lower),
            "ci_upper": float(r.ci_upper),
            "sample_count": int(r.total_jobs)
        } for r in result]
    
    @staticmethod
    def get_recall_at_k_data(db: Session) -> List[Dict[str, Any]]:
        """Calculate Recall @ K for positions 1-10 with 95% confidence intervals
        Recall@K = fraction of relevant items retrieved in top K positions
        Relevant items = tracks that had any hit event within the search session
        """
        
        # Define hit event types (including new bookmark events)
        hit_events = ['spotify_click', 'youtube_click', 'spotify_embed_play', 'bookmark_added_click']
        hit_events_str = "','".join(hit_events)
        
        query = text(f"""
        WITH session_relevant_tracks AS (
            -- Find all tracks that had any hit within each search session
            SELECT DISTINCT
                ss.search_session_id,
                te.spotify_track_id
            FROM search_sessions ss
            JOIN search_jobs sj ON ss.search_session_id = sj.search_session_id
            JOIN track_events te ON sj.job_id = te.job_id
            WHERE te.event_type IN ('{hit_events_str}')
              AND te.spotify_track_id IS NOT NULL
              AND te.spotify_track_id != ''
        ),
        session_recall_at_k AS (
            SELECT 
                ss.search_session_id,
                k,
                COUNT(DISTINCT srt.spotify_track_id) as total_relevant_in_session,
                COUNT(DISTINCT CASE WHEN sr.rank_position <= k THEN srt.spotify_track_id END) as relevant_retrieved_at_k
            FROM search_sessions ss
            LEFT JOIN session_relevant_tracks srt ON ss.search_session_id = srt.search_session_id
            LEFT JOIN search_results sr ON ss.search_session_id = sr.search_session_id 
                                       AND srt.spotify_track_id = sr.spotify_track_id
            CROSS JOIN generate_series(1, 10) as k
            GROUP BY ss.search_session_id, k
        ),
        recall_at_k AS (
            SELECT 
                k,
                COUNT(CASE WHEN total_relevant_in_session > 0 THEN 1 END) as sessions_with_relevant,
                AVG(CASE 
                    WHEN total_relevant_in_session > 0 
                    THEN relevant_retrieved_at_k * 1.0 / total_relevant_in_session 
                    ELSE NULL 
                END) as recall_at_k
            FROM session_recall_at_k
            GROUP BY k
        )
        SELECT 
            k,
            COALESCE(recall_at_k, 0) as recall_at_k,
            sessions_with_relevant,
            -- Calculate 95% confidence interval
            CASE 
                WHEN sessions_with_relevant >= 5 AND recall_at_k > 0.01 AND recall_at_k < 0.99 THEN
                    GREATEST(0, recall_at_k - 1.96 * SQRT(recall_at_k * (1 - recall_at_k) / sessions_with_relevant))
                ELSE recall_at_k
            END as ci_lower,
            CASE 
                WHEN sessions_with_relevant >= 5 AND recall_at_k > 0.01 AND recall_at_k < 0.99 THEN
                    LEAST(1, recall_at_k + 1.96 * SQRT(recall_at_k * (1 - recall_at_k) / sessions_with_relevant))
                ELSE recall_at_k
            END as ci_upper
        FROM recall_at_k
        ORDER BY k
        """)
        
        result = db.execute(query).fetchall()
        return [{
            "k": r.k,
            "recall_at_k": float(r.recall_at_k),
            "ci_lower": float(r.ci_lower),
            "ci_upper": float(r.ci_upper),
            "sample_count": int(r.sessions_with_relevant)
        } for r in result]
    
    @staticmethod
    def get_precision_at_k_data(db: Session) -> List[Dict[str, Any]]:
        """Calculate Precision @ K for positions 1-10 with 95% confidence intervals
        Precision@K = fraction of retrieved items in top K that are relevant
        Relevant items = tracks that had any hit event within the search session
        """
        
        # Define hit event types (including new bookmark events)
        hit_events = ['spotify_click', 'youtube_click', 'spotify_embed_play', 'bookmark_added_click']
        hit_events_str = "','".join(hit_events)
        
        query = text(f"""
        WITH session_relevant_tracks AS (
            -- Find all tracks that had any hit within each search session
            SELECT DISTINCT
                ss.search_session_id,
                te.spotify_track_id
            FROM search_sessions ss
            JOIN search_jobs sj ON ss.search_session_id = sj.search_session_id
            JOIN track_events te ON sj.job_id = te.job_id
            WHERE te.event_type IN ('{hit_events_str}')
              AND te.spotify_track_id IS NOT NULL
              AND te.spotify_track_id != ''
        ),
        session_precision_at_k AS (
            SELECT 
                ss.search_session_id,
                k,
                COUNT(DISTINCT CASE WHEN sr.rank_position <= k THEN sr.spotify_track_id END) as retrieved_at_k,
                COUNT(DISTINCT CASE 
                    WHEN sr.rank_position <= k AND srt.spotify_track_id IS NOT NULL 
                    THEN sr.spotify_track_id 
                END) as relevant_retrieved_at_k
            FROM search_sessions ss
            LEFT JOIN search_results sr ON ss.search_session_id = sr.search_session_id
            LEFT JOIN session_relevant_tracks srt ON ss.search_session_id = srt.search_session_id 
                                                  AND sr.spotify_track_id = srt.spotify_track_id
            CROSS JOIN generate_series(1, 10) as k
            GROUP BY ss.search_session_id, k
        ),
        precision_at_k AS (
            SELECT 
                k,
                COUNT(CASE WHEN retrieved_at_k > 0 THEN 1 END) as sessions_with_results,
                AVG(CASE 
                    WHEN retrieved_at_k > 0 
                    THEN relevant_retrieved_at_k * 1.0 / retrieved_at_k 
                    ELSE NULL 
                END) as precision_at_k
            FROM session_precision_at_k
            GROUP BY k
        )
        SELECT 
            k,
            COALESCE(precision_at_k, 0) as precision_at_k,
            sessions_with_results,
            -- Calculate 95% confidence interval
            CASE 
                WHEN sessions_with_results >= 5 AND precision_at_k > 0.01 AND precision_at_k < 0.99 THEN
                    GREATEST(0, precision_at_k - 1.96 * SQRT(precision_at_k * (1 - precision_at_k) / sessions_with_results))
                ELSE precision_at_k
            END as ci_lower,
            CASE 
                WHEN sessions_with_results >= 5 AND precision_at_k > 0.01 AND precision_at_k < 0.99 THEN
                    LEAST(1, precision_at_k + 1.96 * SQRT(precision_at_k * (1 - precision_at_k) / sessions_with_results))
                ELSE precision_at_k
            END as ci_upper
        FROM precision_at_k
        ORDER BY k
        """)
        
        result = db.execute(query).fetchall()
        return [{
            "k": r.k,
            "precision_at_k": float(r.precision_at_k),
            "ci_lower": float(r.ci_lower),
            "ci_upper": float(r.ci_upper),
            "sample_count": int(r.sessions_with_results)
        } for r in result]
    
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
        
        hit_events = ['spotify_click', 'youtube_click', 'spotify_embed_play', 'bookmark_added_click']
        hit_events_str = "','".join(hit_events)
        
        query = text(f"""
        WITH job_hits AS (
            SELECT DISTINCT
                sr.job_id,
                sr.conversation_turn,
                sr.rank_position
            FROM search_results sr
            JOIN track_events te ON sr.spotify_track_id = te.spotify_track_id 
                                AND sr.job_id = te.job_id
            WHERE te.event_type IN ('{hit_events_str}')
              AND sr.rank_position <= 10
        ),
        hr_by_turn AS (
            SELECT 
                sj.conversation_turn,
                k,
                COUNT(DISTINCT CASE WHEN jh.rank_position <= k THEN jh.job_id END) as hits,
                COUNT(DISTINCT sj.job_id) as total_jobs,
                COUNT(DISTINCT CASE WHEN jh.rank_position <= k THEN jh.job_id END) * 1.0 / 
                COUNT(DISTINCT sj.job_id) as hr_at_k
            FROM search_jobs sj
            CROSS JOIN generate_series(1, 10) as k
            LEFT JOIN job_hits jh ON sj.job_id = jh.job_id AND sj.conversation_turn = jh.conversation_turn
            GROUP BY sj.conversation_turn, k
        )
        SELECT 
            conversation_turn, 
            k, 
            COALESCE(hr_at_k, 0) as hr_at_k,
            hits,
            total_jobs,
            -- Calculate 95% confidence interval
            CASE 
                WHEN total_jobs >= 5 AND hr_at_k > 0.01 AND hr_at_k < 0.99 THEN
                    GREATEST(0, hr_at_k - 1.96 * SQRT(hr_at_k * (1 - hr_at_k) / total_jobs))
                ELSE hr_at_k
            END as ci_lower,
            CASE 
                WHEN total_jobs >= 5 AND hr_at_k > 0.01 AND hr_at_k < 0.99 THEN
                    LEAST(1, hr_at_k + 1.96 * SQRT(hr_at_k * (1 - hr_at_k) / total_jobs))
                ELSE hr_at_k
            END as ci_upper
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
            data_by_turn[turn].append({
                "k": r.k, 
                "hr_at_k": float(r.hr_at_k),
                "ci_lower": float(r.ci_lower),
                "ci_upper": float(r.ci_upper),
                "sample_count": int(r.total_jobs)
            })
        
        return data_by_turn
    
    @staticmethod
    def get_hr_by_model(db: Session) -> Dict[str, List[Dict[str, Any]]]:
        """HR@K data segmented by model"""
        
        hit_events = ['spotify_click', 'youtube_click', 'spotify_embed_play', 'bookmark_added_click']
        hit_events_str = "','".join(hit_events)
        
        query = text(f"""
        WITH job_hits AS (
            SELECT DISTINCT
                sr.job_id,
                sj.model_used,
                sr.rank_position
            FROM search_results sr
            JOIN search_jobs sj ON sr.job_id = sj.job_id
            JOIN track_events te ON sr.spotify_track_id = te.spotify_track_id 
                                AND sr.job_id = te.job_id
            WHERE te.event_type IN ('{hit_events_str}')
              AND sr.rank_position <= 10
              AND sj.model_used IS NOT NULL
        ),
        hr_by_model AS (
            SELECT 
                sj.model_used,
                k,
                COUNT(DISTINCT CASE WHEN jh.rank_position <= k THEN jh.job_id END) as hits,
                COUNT(DISTINCT sj.job_id) as total_jobs,
                COUNT(DISTINCT CASE WHEN jh.rank_position <= k THEN jh.job_id END) * 1.0 / 
                COUNT(DISTINCT sj.job_id) as hr_at_k
            FROM search_jobs sj
            CROSS JOIN generate_series(1, 10) as k
            LEFT JOIN job_hits jh ON sj.job_id = jh.job_id AND sj.model_used = jh.model_used
            WHERE sj.model_used IS NOT NULL
            GROUP BY sj.model_used, k
        )
        SELECT 
            model_used, 
            k, 
            COALESCE(hr_at_k, 0) as hr_at_k,
            hits,
            total_jobs,
            -- Calculate 95% confidence interval
            CASE 
                WHEN total_jobs >= 5 AND hr_at_k > 0.01 AND hr_at_k < 0.99 THEN
                    GREATEST(0, hr_at_k - 1.96 * SQRT(hr_at_k * (1 - hr_at_k) / total_jobs))
                ELSE hr_at_k
            END as ci_lower,
            CASE 
                WHEN total_jobs >= 5 AND hr_at_k > 0.01 AND hr_at_k < 0.99 THEN
                    LEAST(1, hr_at_k + 1.96 * SQRT(hr_at_k * (1 - hr_at_k) / total_jobs))
                ELSE hr_at_k
            END as ci_upper
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
            data_by_model[model].append({
                "k": r.k, 
                "hr_at_k": float(r.hr_at_k),
                "ci_lower": float(r.ci_lower),
                "ci_upper": float(r.ci_upper),
                "sample_count": int(r.total_jobs)
            })
        
        return data_by_model
    
    @staticmethod
    def get_hr_by_hit_component(db: Session) -> Dict[str, List[Dict[str, Any]]]:
        """HR@K data segmented by hit component type"""
        
        hit_events = ['spotify_click', 'youtube_click', 'spotify_embed_play', 'bookmark_added_click']
        
        all_data = {}
        
        for event_type in hit_events:
            query = text(f"""
            WITH job_hits AS (
                SELECT DISTINCT
                    sr.job_id,
                    sr.rank_position
                FROM search_results sr
                JOIN track_events te ON sr.spotify_track_id = te.spotify_track_id 
                                    AND sr.job_id = te.job_id
                WHERE te.event_type = '{event_type}'
                  AND sr.rank_position <= 10
            ),
            hr_at_k AS (
                SELECT 
                    k,
                    COUNT(DISTINCT CASE WHEN jh.rank_position <= k THEN jh.job_id END) as hits,
                    COUNT(DISTINCT sj.job_id) as total_jobs,
                    COUNT(DISTINCT CASE WHEN jh.rank_position <= k THEN jh.job_id END) * 1.0 / 
                    COUNT(DISTINCT sj.job_id) as hr_at_k
                FROM search_jobs sj
                CROSS JOIN generate_series(1, 10) as k
                LEFT JOIN job_hits jh ON sj.job_id = jh.job_id
                GROUP BY k
            )
            SELECT 
                k, 
                COALESCE(hr_at_k, 0) as hr_at_k,
                hits,
                total_jobs,
                -- Calculate 95% confidence interval
                CASE 
                    WHEN total_jobs > 0 AND hr_at_k > 0 AND hr_at_k < 1 THEN
                        GREATEST(0, hr_at_k - 1.96 * SQRT(hr_at_k * (1 - hr_at_k) / total_jobs))
                    ELSE hr_at_k
                END as ci_lower,
                CASE 
                    WHEN total_jobs > 0 AND hr_at_k > 0 AND hr_at_k < 1 THEN
                        LEAST(1, hr_at_k + 1.96 * SQRT(hr_at_k * (1 - hr_at_k) / total_jobs))
                    ELSE hr_at_k
                END as ci_upper
            FROM hr_at_k 
            ORDER BY k
            """)
            
            result = db.execute(query).fetchall()
            all_data[event_type] = [{
                "k": r.k, 
                "hr_at_k": float(r.hr_at_k),
                "ci_lower": float(r.ci_lower),
                "ci_upper": float(r.ci_upper),
                "sample_count": int(r.total_jobs)
            } for r in result]
        
        return all_data
    
    @staticmethod
    def get_latency_by_conversation_turn(db: Session) -> Dict[str, List[Dict[str, Any]]]:
        """Latency CDF data segmented by conversation turn"""
        
        query = text("""
        WITH latency_data AS (
            SELECT 
                conversation_turn,
                processing_time_ms / 1000.0 as latency_seconds
            FROM search_jobs 
            WHERE processing_time_ms IS NOT NULL
              AND completed_at IS NOT NULL
        ),
        latency_percentiles AS (
            SELECT 
                conversation_turn,
                latency_seconds,
                PERCENT_RANK() OVER (PARTITION BY conversation_turn ORDER BY latency_seconds) as percentile
            FROM latency_data
        )
        SELECT 
            conversation_turn,
            latency_seconds,
            percentile
        FROM latency_percentiles
        ORDER BY conversation_turn, latency_seconds
        """)
        
        result = db.execute(query).fetchall()
        
        # Group by conversation turn
        data_by_turn = {}
        for r in result:
            turn = f"Turn {r.conversation_turn}"
            if turn not in data_by_turn:
                data_by_turn[turn] = []
            data_by_turn[turn].append({
                "latency_seconds": float(r.latency_seconds), 
                "percentile": float(r.percentile)
            })
        
        return data_by_turn
    
    @staticmethod
    def get_latency_by_model(db: Session) -> Dict[str, List[Dict[str, Any]]]:
        """Latency CDF data segmented by model"""
        
        query = text("""
        WITH latency_data AS (
            SELECT 
                model_used,
                processing_time_ms / 1000.0 as latency_seconds
            FROM search_jobs 
            WHERE processing_time_ms IS NOT NULL
              AND completed_at IS NOT NULL
              AND model_used IS NOT NULL
        ),
        latency_percentiles AS (
            SELECT 
                model_used,
                latency_seconds,
                PERCENT_RANK() OVER (PARTITION BY model_used ORDER BY latency_seconds) as percentile
            FROM latency_data
        )
        SELECT 
            model_used,
            latency_seconds,
            percentile
        FROM latency_percentiles
        ORDER BY model_used, latency_seconds
        """)
        
        result = db.execute(query).fetchall()
        
        # Group by model
        data_by_model = {}
        for r in result:
            model = r.model_used or "Unknown"
            if model not in data_by_model:
                data_by_model[model] = []
            data_by_model[model].append({
                "latency_seconds": float(r.latency_seconds), 
                "percentile": float(r.percentile)
            })
        
        return data_by_model
    
    @staticmethod
    def get_all_dashboard_data(db: Session) -> Dict[str, Any]:
        """Get all dashboard data in a single API call"""
        
        try:
            volume_metrics = DashboardService.get_volume_metrics(db)
            hr_at_k = DashboardService.get_hr_at_k_data(db)
            recall_at_k = DashboardService.get_recall_at_k_data(db)
            precision_at_k = DashboardService.get_precision_at_k_data(db)
            latency_cdf = DashboardService.get_latency_cdf_data(db)
            hr_by_turn = DashboardService.get_hr_by_conversation_turn(db)
            hr_by_model = DashboardService.get_hr_by_model(db)
            hr_by_component = DashboardService.get_hr_by_hit_component(db)
            latency_by_turn = DashboardService.get_latency_by_conversation_turn(db)
            latency_by_model = DashboardService.get_latency_by_model(db)
            
            return {
                "volume_metrics": volume_metrics,
                "performance_charts": {
                    "hr_at_k": hr_at_k,
                    "recall_at_k": recall_at_k,
                    "precision_at_k": precision_at_k,
                    "latency_cdf": latency_cdf
                },
                "segmented_charts": {
                    "by_conversation_turn": {
                        "hr_data": hr_by_turn,
                        "latency_data": latency_by_turn
                    },
                    "by_model": {
                        "hr_data": hr_by_model,
                        "latency_data": latency_by_model
                    },
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
                    "recall_at_k": [],
                    "precision_at_k": [],
                    "latency_cdf": []
                },
                "segmented_charts": {
                    "by_conversation_turn": {"hr_data": {}, "latency_data": {}}, 
                    "by_model": {"hr_data": {}, "latency_data": {}}, 
                    "by_hit_component": {}
                }
            }