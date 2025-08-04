"""
Service for managing playlists (linked to search sessions)
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from api.db_models import Playlist
from api.music_service import MusicService
import uuid

class PlaylistService:
    
    @staticmethod
    def create_or_update_playlist(db: Session, search_session_id: str, track_ids: List[str]) -> Playlist:
        """Create or update playlist for a search session with full track list"""
        
        # Find existing playlist for this search session
        existing_playlist = db.query(Playlist).filter_by(search_session_id=search_session_id).first()
        
        if existing_playlist:
            # Update existing playlist
            existing_playlist.track_ids = track_ids
            db.commit()
            db.refresh(existing_playlist)
            return existing_playlist
        else:
            # Create new playlist
            new_playlist = Playlist(
                id=str(uuid.uuid4()),
                search_session_id=search_session_id,
                track_ids=track_ids,
                access_count=0
            )
            db.add(new_playlist)
            db.commit()
            db.refresh(new_playlist)
            return new_playlist
    
    @staticmethod
    def get_playlist_for_export(db: Session, playlist_id: str) -> Optional[Dict[str, Any]]:
        """Get playlist data for sharing/export (increments access_count)"""
        
        # Get playlist from database
        playlist = db.query(Playlist).filter_by(id=playlist_id).first()
        if not playlist:
            return None
        
        # Increment access count for analytics
        playlist.access_count += 1
        db.commit()
        
        # Get track data using music service
        music_service = MusicService()
        music_service.initialize()
        
        tracks = music_service.get_tracks_by_spotify_ids(playlist.track_ids)
        
        return {
            "playlist_id": playlist.id,
            "search_session_id": playlist.search_session_id,
            "track_count": len(playlist.track_ids),
            "tracks": [track.dict() for track in tracks],
            "created_at": playlist.created_at.isoformat(),
            "access_count": playlist.access_count
        }