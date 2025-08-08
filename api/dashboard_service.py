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
        
        # Count unique users by IP address (not sessions)
        users = db.query(func.count(func.distinct(UserSession.client_ip))).filter(UserSession.client_ip.isnot(None)).scalar() or 0
        
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
    def get_genre_usage_analysis(db: Session) -> List[Dict[str, Any]]:
        """Analyze genre usage by exploding comma-separated genre fields"""
        query = text("""
        SELECT filters_json
        FROM search_jobs
        WHERE filters_json IS NOT NULL 
            AND completed_at IS NOT NULL
        """)
        
        results = db.execute(query).fetchall()
        
        genre_usage = {}
        
        for row in results:
            filters = row.filters_json
            if not filters:
                continue
            
            # Parse included genres
            if filters.get('spotify_artist_genres_include_any'):
                genres_str = str(filters['spotify_artist_genres_include_any']).strip()
                if genres_str:
                    genres = [g.strip().lower() for g in genres_str.split(',') if g.strip()]
                    for genre in genres:
                        key = ('included', genre)
                        genre_usage[key] = genre_usage.get(key, 0) + 1
            
            # Parse excluded genres
            if filters.get('spotify_artist_genres_exclude_any'):
                genres_str = str(filters['spotify_artist_genres_exclude_any']).strip()
                if genres_str:
                    genres = [g.strip().lower() for g in genres_str.split(',') if g.strip()]
                    for genre in genres:
                        key = ('excluded', genre)
                        genre_usage[key] = genre_usage.get(key, 0) + 1
            
            # Parse boosted genres  
            if filters.get('spotify_artist_genres_boosted'):
                genres_str = str(filters['spotify_artist_genres_boosted']).strip()
                if genres_str:
                    genres = [g.strip().lower() for g in genres_str.split(',') if g.strip()]
                    for genre in genres:
                        key = ('boosted', genre)
                        genre_usage[key] = genre_usage.get(key, 0) + 1
        
        # Convert to list format for frontend
        genre_list = []
        for (filter_type, genre), count in sorted(genre_usage.items(), key=lambda x: x[1], reverse=True):
            genre_list.append({
                'filter_type': filter_type,
                'genre': genre,
                'usage_count': count
            })
        
        return genre_list[:30]  # Top 30 most used genres across all filter types

    @staticmethod
    def get_hr_at_k_by_image(db: Session) -> Dict[str, List[Dict[str, Any]]]:
        """Get Hit Rate @ K data split by searches with/without images"""
        query = text("""
        WITH job_hits AS (
            SELECT 
                sj.job_id,
                ss.has_image,
                k.k_value,
                CASE WHEN COUNT(te.id) > 0 THEN 1 ELSE 0 END as has_hit
            FROM search_jobs sj
            INNER JOIN search_sessions ss ON sj.search_session_id = ss.search_session_id
            CROSS JOIN (SELECT generate_series(1, 10) as k_value) k
            LEFT JOIN track_events te ON te.job_id = sj.job_id 
                AND te.rank_position <= k.k_value
                AND te.event_type IN ('youtube_click', 'spotify_click', 'spotify_embed_play')
            WHERE sj.completed_at IS NOT NULL
            GROUP BY sj.job_id, ss.has_image, k.k_value
        ),
        hr_calc AS (
            SELECT 
                has_image,
                k_value,
                COUNT(*) as total_jobs,
                SUM(has_hit) as jobs_with_hits,
                ROUND(100.0 * SUM(has_hit) / COUNT(*), 1) as hr_at_k
            FROM job_hits
            GROUP BY has_image, k_value
            HAVING COUNT(*) >= 5
        )
        SELECT 
            has_image,
            k_value,
            total_jobs,
            jobs_with_hits,
            hr_at_k,
            CASE WHEN total_jobs >= 5 AND hr_at_k > 0.01 AND hr_at_k < 99.99 
                 THEN GREATEST(0, hr_at_k - 1.96 * SQRT(hr_at_k * (100 - hr_at_k) / total_jobs)) 
                 ELSE hr_at_k END as ci_lower,
            CASE WHEN total_jobs >= 5 AND hr_at_k > 0.01 AND hr_at_k < 99.99 
                 THEN LEAST(100, hr_at_k + 1.96 * SQRT(hr_at_k * (100 - hr_at_k) / total_jobs)) 
                 ELSE hr_at_k END as ci_upper
        FROM hr_calc
        ORDER BY has_image, k_value
        """)
        
        results = db.execute(query).fetchall()
        
        with_image = []
        without_image = []
        
        for row in results:
            data_point = {
                "k": row.k_value,
                "hr_at_k": row.hr_at_k,
                "total_jobs": row.total_jobs,
                "jobs_with_hits": row.jobs_with_hits,
                "ci_lower": row.ci_lower,
                "ci_upper": row.ci_upper
            }
            
            if row.has_image:
                with_image.append(data_point)
            else:
                without_image.append(data_point)
        
        result = {
            "with_image": with_image,
            "without_image": without_image
        }
        
        print(f"DEBUG HR@K by image: with_image={len(with_image)}, without_image={len(without_image)}")
        
        return result

    @staticmethod
    def get_conversation_turns_by_model(db: Session) -> Dict[str, List[Dict[str, Any]]]:
        """Get CDF of conversation turns by model"""
        query = text("""
        WITH session_turns AS (
            SELECT 
                ss.model_used,
                MAX(sj.conversation_turn) as max_turn
            FROM search_sessions ss
            INNER JOIN search_jobs sj ON ss.search_session_id = sj.search_session_id
            WHERE ss.model_used IS NOT NULL
            GROUP BY ss.search_session_id, ss.model_used
        ),
        turn_counts AS (
            SELECT 
                model_used,
                max_turn,
                COUNT(*) as count
            FROM session_turns
            GROUP BY model_used, max_turn
        ),
        cumulative AS (
            SELECT 
                model_used,
                max_turn,
                count,
                SUM(count) OVER (PARTITION BY model_used ORDER BY max_turn) as cumulative_count,
                SUM(count) OVER (PARTITION BY model_used) as total_count
            FROM turn_counts
        )
        SELECT 
            model_used,
            max_turn,
            count,
            ROUND(100.0 * cumulative_count / total_count, 1) as cumulative_percentage
        FROM cumulative
        ORDER BY model_used, max_turn
        """)
        
        results = db.execute(query).fetchall()
        
        model_data = {}
        for row in results:
            if row.model_used not in model_data:
                model_data[row.model_used] = []
            
            model_data[row.model_used].append({
                "turns": row.max_turn,
                "percentage": row.cumulative_percentage,
                "count": row.count
            })
        
        print(f"DEBUG Conversation turns by model: {list(model_data.keys())}, total entries: {sum(len(v) for v in model_data.values())}")
        
        return model_data

    @staticmethod
    def get_result_count_by_turn(db: Session) -> List[Dict[str, Any]]:
        """Get average result count by conversation turn"""
        query = text("""
        SELECT 
            conversation_turn,
            COUNT(*) as job_count,
            ROUND(AVG(result_count), 1) as avg_result_count,
            ROUND(STDDEV(result_count), 1) as std_dev,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY result_count) as median_result_count,
            MIN(result_count) as min_result_count,
            MAX(result_count) as max_result_count
        FROM search_jobs
        WHERE completed_at IS NOT NULL 
            AND result_count IS NOT NULL
        GROUP BY conversation_turn
        ORDER BY conversation_turn
        """)
        
        results = db.execute(query).fetchall()
        
        return [
            {
                "turn": row.conversation_turn,
                "job_count": row.job_count,
                "avg_result_count": row.avg_result_count,
                "std_dev": row.std_dev if row.std_dev else 0,
                "median_result_count": float(row.median_result_count) if row.median_result_count else 0,
                "min_result_count": row.min_result_count,
                "max_result_count": row.max_result_count
            }
            for row in results
        ]

    @staticmethod
    def get_top_filters_analysis(db: Session) -> Dict[str, List[Dict[str, Any]]]:
        """Analyze most used filters and weights from filters_json (excluding genres)"""
        query = text("""
        WITH filter_applications AS (
            -- Stage 1: Explode JSON into one row per filter application  
            SELECT job_id, 'danceability_decile_min' as filter_name, (filters_json->>'danceability_decile_min')::float as filter_value, 'min' as filter_type
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL AND filters_json->>'danceability_decile_min' IS NOT NULL
            UNION ALL SELECT job_id, 'danceability_decile_max', (filters_json->>'danceability_decile_max')::float, 'max'
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL AND filters_json->>'danceability_decile_max' IS NOT NULL
            UNION ALL SELECT job_id, 'energy_decile_min', (filters_json->>'energy_decile_min')::float, 'min'
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL AND filters_json->>'energy_decile_min' IS NOT NULL
            UNION ALL SELECT job_id, 'energy_decile_max', (filters_json->>'energy_decile_max')::float, 'max'
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL AND filters_json->>'energy_decile_max' IS NOT NULL
            UNION ALL SELECT job_id, 'acousticness_decile_min', (filters_json->>'acousticness_decile_min')::float, 'min'
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL AND filters_json->>'acousticness_decile_min' IS NOT NULL
            UNION ALL SELECT job_id, 'acousticness_decile_max', (filters_json->>'acousticness_decile_max')::float, 'max'
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL AND filters_json->>'acousticness_decile_max' IS NOT NULL
            UNION ALL SELECT job_id, 'liveness_decile_min', (filters_json->>'liveness_decile_min')::float, 'min'
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL AND filters_json->>'liveness_decile_min' IS NOT NULL
            UNION ALL SELECT job_id, 'liveness_decile_max', (filters_json->>'liveness_decile_max')::float, 'max'
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL AND filters_json->>'liveness_decile_max' IS NOT NULL
            UNION ALL SELECT job_id, 'valence_decile_min', (filters_json->>'valence_decile_min')::float, 'min'
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL AND filters_json->>'valence_decile_min' IS NOT NULL
            UNION ALL SELECT job_id, 'valence_decile_max', (filters_json->>'valence_decile_max')::float, 'max'
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL AND filters_json->>'valence_decile_max' IS NOT NULL
            UNION ALL SELECT job_id, 'views_decile_min', (filters_json->>'views_decile_min')::float, 'min'
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL AND filters_json->>'views_decile_min' IS NOT NULL
            UNION ALL SELECT job_id, 'views_decile_max', (filters_json->>'views_decile_max')::float, 'max'
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL AND filters_json->>'views_decile_max' IS NOT NULL
            UNION ALL SELECT job_id, 'tempo_min', (filters_json->>'tempo_min')::float, 'min'
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL AND filters_json->>'tempo_min' IS NOT NULL
            UNION ALL SELECT job_id, 'tempo_max', (filters_json->>'tempo_max')::float, 'max'
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL AND filters_json->>'tempo_max' IS NOT NULL
            UNION ALL SELECT job_id, 'loudness_min', (filters_json->>'loudness_min')::float, 'min'
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL AND filters_json->>'loudness_min' IS NOT NULL
            UNION ALL SELECT job_id, 'loudness_max', (filters_json->>'loudness_max')::float, 'max'
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL AND filters_json->>'loudness_max' IS NOT NULL
            UNION ALL SELECT job_id, 'duration_ms_min', (filters_json->>'duration_ms_min')::float, 'min'
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL AND filters_json->>'duration_ms_min' IS NOT NULL
            UNION ALL SELECT job_id, 'duration_ms_max', (filters_json->>'duration_ms_max')::float, 'max'
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL AND filters_json->>'duration_ms_max' IS NOT NULL
            UNION ALL SELECT job_id, 'instrumentalness_min', (filters_json->>'instrumentalness_min')::float, 'min'
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL AND filters_json->>'instrumentalness_min' IS NOT NULL
            UNION ALL SELECT job_id, 'instrumentalness_max', (filters_json->>'instrumentalness_max')::float, 'max'
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL AND filters_json->>'instrumentalness_max' IS NOT NULL
            UNION ALL SELECT job_id, 'album_release_year_min', (filters_json->>'album_release_year_min')::float, 'min'
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL AND filters_json->>'album_release_year_min' IS NOT NULL
            UNION ALL SELECT job_id, 'album_release_year_max', (filters_json->>'album_release_year_max')::float, 'max'
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL AND filters_json->>'album_release_year_max' IS NOT NULL
            UNION ALL SELECT job_id, 'track_is_explicit_min', (filters_json->>'track_is_explicit_min')::float, 'min'
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL AND filters_json->>'track_is_explicit_min' IS NOT NULL
            UNION ALL SELECT job_id, 'track_is_explicit_max', (filters_json->>'track_is_explicit_max')::float, 'max'
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL AND filters_json->>'track_is_explicit_max' IS NOT NULL
            -- Add weight fields (non-zero values only)
            UNION ALL SELECT job_id, 'danceability_decile_weight', (filters_json->>'danceability_decile_weight')::float, 'weight'
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL 
                AND filters_json->>'danceability_decile_weight' IS NOT NULL AND (filters_json->>'danceability_decile_weight')::float != 0
            UNION ALL SELECT job_id, 'energy_decile_weight', (filters_json->>'energy_decile_weight')::float, 'weight'
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL 
                AND filters_json->>'energy_decile_weight' IS NOT NULL AND (filters_json->>'energy_decile_weight')::float != 0
            UNION ALL SELECT job_id, 'acousticness_decile_weight', (filters_json->>'acousticness_decile_weight')::float, 'weight'
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL 
                AND filters_json->>'acousticness_decile_weight' IS NOT NULL AND (filters_json->>'acousticness_decile_weight')::float != 0
            UNION ALL SELECT job_id, 'liveness_decile_weight', (filters_json->>'liveness_decile_weight')::float, 'weight'
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL 
                AND filters_json->>'liveness_decile_weight' IS NOT NULL AND (filters_json->>'liveness_decile_weight')::float != 0
            UNION ALL SELECT job_id, 'valence_decile_weight', (filters_json->>'valence_decile_weight')::float, 'weight'
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL 
                AND filters_json->>'valence_decile_weight' IS NOT NULL AND (filters_json->>'valence_decile_weight')::float != 0
            UNION ALL SELECT job_id, 'views_decile_weight', (filters_json->>'views_decile_weight')::float, 'weight'
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL 
                AND filters_json->>'views_decile_weight' IS NOT NULL AND (filters_json->>'views_decile_weight')::float != 0
            UNION ALL SELECT job_id, 'tempo_weight', (filters_json->>'tempo_weight')::float, 'weight'
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL 
                AND filters_json->>'tempo_weight' IS NOT NULL AND (filters_json->>'tempo_weight')::float != 0
            UNION ALL SELECT job_id, 'loudness_weight', (filters_json->>'loudness_weight')::float, 'weight'
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL 
                AND filters_json->>'loudness_weight' IS NOT NULL AND (filters_json->>'loudness_weight')::float != 0
            UNION ALL SELECT job_id, 'duration_ms_weight', (filters_json->>'duration_ms_weight')::float, 'weight'
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL 
                AND filters_json->>'duration_ms_weight' IS NOT NULL AND (filters_json->>'duration_ms_weight')::float != 0
            UNION ALL SELECT job_id, 'instrumentalness_weight', (filters_json->>'instrumentalness_weight')::float, 'weight'
            FROM search_jobs WHERE filters_json IS NOT NULL AND completed_at IS NOT NULL 
                AND filters_json->>'instrumentalness_weight' IS NOT NULL AND (filters_json->>'instrumentalness_weight')::float != 0
        ),
        filter_defaults AS (
            -- Stage 2: Get min and max for each filter to identify defaults
            SELECT filter_name, filter_type, MIN(filter_value) as min_value, MAX(filter_value) as max_value
            FROM filter_applications WHERE filter_type IN ('min', 'max') GROUP BY filter_name, filter_type
        ),
        non_default_filters AS (
            -- Stage 3: Remove rows where value = default
            SELECT fa.* FROM filter_applications fa
            LEFT JOIN filter_defaults fd ON fa.filter_name = fd.filter_name AND fa.filter_type = fd.filter_type
            WHERE fa.filter_type = 'weight'  -- Include all weights (already filtered for non-zero)
               OR (fa.filter_type = 'min' AND fa.filter_value != fd.min_value)  -- Exclude default mins
               OR (fa.filter_type = 'max' AND fa.filter_value != fd.max_value)  -- Exclude default maxs
        )
        -- Stage 4: Generate summary stats on cleaned table
        SELECT 
            REGEXP_REPLACE(filter_name, '_decile|_min|_max|_weight', '', 'g') as field,
            filter_type, COUNT(*) as usage_count, ROUND(AVG(filter_value)::numeric, 2) as avg_value
        FROM non_default_filters GROUP BY filter_name, filter_type ORDER BY usage_count DESC LIMIT 25
        """)
        
        results = db.execute(query).fetchall()
        
        return {
            'top_filters': [
                {
                    'field': row.field,
                    'filter_type': row.filter_type,
                    'usage_count': row.usage_count,
                    'avg_value': row.avg_value
                }
                for row in results
            ]
        }

    @staticmethod
    def get_query_leaderboard(db: Session) -> List[Dict[str, Any]]:
        """Get top queries by search count and recency"""
        query = text("""
        WITH query_stats AS (
            SELECT 
                ss.original_query,
                COUNT(DISTINCT ss.search_session_id) as search_count,
                MAX(ss.started_at) as latest_search,
                MAX(sj.result_count) as latest_result_count,
                MAX(sj.conversation_turn) as max_turns,
                -- HR@10 calculation
                COUNT(DISTINCT CASE WHEN te.rank_position <= 10 THEN sj.job_id END) as jobs_with_hits_10,
                COUNT(DISTINCT sj.job_id) as total_jobs
            FROM search_sessions ss
            LEFT JOIN search_jobs sj ON ss.search_session_id = sj.search_session_id 
                AND sj.completed_at IS NOT NULL
            LEFT JOIN track_events te ON sj.job_id = te.job_id 
                AND te.event_type IN ('youtube_click', 'spotify_click', 'spotify_embed_play')
            GROUP BY ss.original_query
            HAVING COUNT(DISTINCT ss.search_session_id) >= 1  -- Include all queries
        )
        SELECT 
            original_query,
            search_count,
            latest_search,
            latest_result_count,
            max_turns,
            CASE WHEN total_jobs > 0 
                 THEN ROUND(100.0 * jobs_with_hits_10 / total_jobs, 1) 
                 ELSE 0 END as hr_at_10
        FROM query_stats
        ORDER BY search_count DESC, latest_search DESC
        LIMIT 50
        """)
        
        results = db.execute(query).fetchall()
        
        return [
            {
                "query": row.original_query[:100] + "..." if len(row.original_query) > 100 else row.original_query,
                "search_count": row.search_count,
                "latest_search": row.latest_search.isoformat() if row.latest_search else None,
                "latest_result_count": row.latest_result_count,
                "conversation_turns": row.max_turns,
                "hr_at_10": row.hr_at_10
            }
            for row in results
        ]

    @staticmethod
    def get_user_leaderboard(db: Session) -> List[Dict[str, Any]]:
        """Get top users by activity and engagement"""
        query = text("""
        WITH user_stats AS (
            SELECT 
                us.client_ip as user_identifier,
                COUNT(DISTINCT us.user_session_id) as session_count,
                COUNT(DISTINCT ss.search_session_id) as search_count,
                COUNT(DISTINCT sj.job_id) as search_job_count,
                COUNT(DISTINCT p.id) as playlist_count,
                MIN(ss.started_at) as first_search,
                MAX(ss.started_at) as latest_search,
                -- HR@10 calculation
                COUNT(DISTINCT CASE WHEN te.rank_position <= 10 THEN sj.job_id END) as jobs_with_hits_10,
                COUNT(DISTINCT sj.job_id) as total_jobs
            FROM user_sessions us
            LEFT JOIN search_sessions ss ON us.user_session_id = ss.user_session_id
            LEFT JOIN search_jobs sj ON ss.search_session_id = sj.search_session_id 
                AND sj.completed_at IS NOT NULL
            LEFT JOIN track_events te ON sj.job_id = te.job_id 
                AND te.event_type IN ('youtube_click', 'spotify_click', 'spotify_embed_play')
            LEFT JOIN playlists p ON ss.search_session_id = p.search_session_id
            WHERE us.client_ip IS NOT NULL
            GROUP BY us.client_ip
        ),
        user_recent_queries AS (
            SELECT DISTINCT ON (us.client_ip)
                us.client_ip as user_identifier,
                ss.original_query as most_recent_query
            FROM user_sessions us
            LEFT JOIN search_sessions ss ON us.user_session_id = ss.user_session_id
            WHERE us.client_ip IS NOT NULL
            ORDER BY us.client_ip, ss.started_at DESC
        ),
        ranked_users AS (
            SELECT 
                us.user_identifier,
                us.session_count,
                us.search_count,
                us.search_job_count,
                us.playlist_count,
                us.first_search,
                us.latest_search,
                urq.most_recent_query,
                CASE WHEN us.total_jobs > 0 
                     THEN ROUND(100.0 * us.jobs_with_hits_10 / us.total_jobs, 1) 
                     ELSE 0 END as hr_at_10
            FROM user_stats us
            LEFT JOIN user_recent_queries urq ON us.user_identifier = urq.user_identifier
            WHERE us.search_count > 0  -- Only users who have searched
        )
        SELECT 
            user_identifier,
            session_count,
            search_count,
            search_job_count,
            playlist_count,
            first_search,
            latest_search,
            most_recent_query,
            hr_at_10
        FROM ranked_users
        ORDER BY search_count DESC, latest_search DESC
        LIMIT 50
        """)
        
        results = db.execute(query).fetchall()
        
        return [
            {
                "user": row.user_identifier if '@' in str(row.user_identifier) else row.user_identifier[:20] + "..." if len(str(row.user_identifier)) > 20 else str(row.user_identifier),
                "session_count": row.session_count,
                "search_count": row.search_count,
                "search_job_count": row.search_job_count,
                "playlist_count": row.playlist_count,
                "first_search": row.first_search.isoformat() if row.first_search else None,
                "latest_search": row.latest_search.isoformat() if row.latest_search else None,
                "hr_at_10": row.hr_at_10,
                "most_recent_query": (row.most_recent_query[:50] + "...") if row.most_recent_query and len(row.most_recent_query) > 50 else row.most_recent_query
            }
            for row in results
        ]

    @staticmethod
    def get_all_dashboard_data(db: Session) -> Dict[str, Any]:
        """Get all dashboard data in a single API call"""
        
        try:
            # Existing analytics
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
            
            # New analytics methods
            genre_usage = DashboardService.get_genre_usage_analysis(db)
            hr_by_image = DashboardService.get_hr_at_k_by_image(db)
            conversation_turns = DashboardService.get_conversation_turns_by_model(db)
            result_by_turn = DashboardService.get_result_count_by_turn(db)
            filters_analysis = DashboardService.get_top_filters_analysis(db)
            query_leaderboard = DashboardService.get_query_leaderboard(db)
            user_leaderboard = DashboardService.get_user_leaderboard(db)
            
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
                    "by_hit_component": hr_by_component,
                    "by_image_presence": hr_by_image
                },
                "analysis_tables": {
                    "genre_usage": genre_usage,
                    "conversation_analysis": {
                        "turns_by_model": conversation_turns,
                        "result_count_by_turn": result_by_turn
                    },
                    "filters_analysis": filters_analysis,
                    "leaderboards": {
                        "top_queries": query_leaderboard,
                        "top_users": user_leaderboard
                    }
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
                    "by_hit_component": {},
                    "by_image_presence": {}
                },
                "analysis_tables": {
                    "genre_usage": [],
                    "conversation_analysis": {
                        "turns_by_model": [],
                        "result_count_by_turn": []
                    },
                    "filters_analysis": [],
                    "leaderboards": {
                        "top_queries": [],
                        "top_users": []
                    }
                }
            }