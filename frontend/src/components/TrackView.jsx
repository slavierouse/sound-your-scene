import { useState, useEffect } from 'react'
import { BookmarkIcon, BookmarkSlashIcon } from '@heroicons/react/24/outline'
import { bookmarkService } from '../services/bookmarkService'

function TrackView({ track, index, jobId, originalQuery, relevanceIndex, onBookmarkChange, bookmarkKey }) {
  const [isBookmarked, setIsBookmarked] = useState(false)
  
  useEffect(() => {
    setIsBookmarked(bookmarkService.isBookmarked(track.spotify_track_id))
  }, [track.spotify_track_id, bookmarkKey])

  const handleBookmarkToggle = () => {
    try {
      if (isBookmarked) {
        bookmarkService.removeBookmark(track.spotify_track_id)
        setIsBookmarked(false)
      } else {
        bookmarkService.addBookmark(track, jobId, originalQuery, relevanceIndex)
        setIsBookmarked(true)
      }
      
      // Notify parent component of bookmark change
      if (onBookmarkChange) {
        onBookmarkChange()
      }
    } catch (error) {
      alert(error.message)
    }
  }

  return (
    <div className="p-4 bg-white border border-gray-200 rounded-lg">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-sm font-medium text-gray-500">#{index + 1}</span>
            <h4 className="font-medium text-gray-900">{track.track}</h4>
          </div>
          <p className="text-gray-600 mb-3">{track.artist}</p>
          {track.spotify_artist_genres && (
            <p className="text-gray-600 mb-3">
              {track.spotify_artist_genres.split(',').map(genre => genre.trim()).join(', ')}
            </p>
          )}
          <div className="flex gap-3">
            {track.url_youtube && (
              <a 
                href={track.url_youtube} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-red-600 hover:text-red-700 text-sm font-medium"
              >
                YouTube
              </a>
            )}
            {track.spotify_url && (
              <a 
                href={track.spotify_url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-green-600 hover:text-green-700 text-sm font-medium"
              >
                Spotify
              </a>
            )}
          </div>
          
          {/* Spotify Embed */}
          {track.spotify_track_id && (
            <div className="mt-4">
              <iframe 
                style={{borderRadius: '12px'}}
                src={`https://open.spotify.com/embed/track/${track.spotify_track_id}?utm_source=generator`}
                width="100%" 
                height="152" 
                frameBorder="0" 
                allowfullscreen="" 
                allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" 
                loading="lazy"
              />
            </div>
          )}

          {/* YouTube Embed - Commented Out */}
          {/* {track.url_youtube && (
            <div className="flex gap-3 mt-4">
              <iframe 
                width="280" height="160" 
                src={`https://www.youtube.com/embed/${track.url_youtube.replace('https://www.youtube.com/watch?v=', '')}`}
                frameborder="0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                referrerpolicy="strict-origin-when-cross-origin"
                allowfullscreen
              />
            </div>
          )} */}
        </div>
        
        {/* Bookmark Button */}
        <button
          onClick={handleBookmarkToggle}
          className="flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg border transition-colors hover:bg-gray-50"
          title={isBookmarked ? "Remove from saved" : "Save track"}
        >
          {isBookmarked ? (
            <>
              <BookmarkSlashIcon className="w-4 h-4" />
              <span>Unsave</span>
            </>
          ) : (
            <>
              <BookmarkIcon className="w-4 h-4" />
              <span>Save</span>
            </>
          )}
        </button>
      </div>
    </div>
  )
}

export default TrackView