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
    <div className="p-3 sm:p-4 bg-white border border-gray-200 rounded-lg w-full">
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 sm:gap-0">
        <div className="flex-1">
          <div className="flex items-center gap-2 sm:gap-3 mb-2">
            <span className="text-xs sm:text-sm font-medium text-gray-500">#{index + 1}</span>
            <h4 className="text-sm sm:text-base font-medium text-gray-900">{track.track}</h4>
          </div>
          <p className="text-sm sm:text-base text-gray-600 mb-2 sm:mb-3">{track.artist}</p>
          {track.spotify_artist_genres && (
            <p className="text-xs sm:text-sm text-gray-600 mb-2 sm:mb-3">
              {track.spotify_artist_genres.split(',').map(genre => genre.trim()).join(', ')}
            </p>
          )}
          <div className="flex gap-3 mb-3 sm:mb-0">
            {track.url_youtube && (
              <a 
                href={track.url_youtube} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-red-600 hover:text-red-700 text-xs sm:text-sm font-medium"
              >
                YouTube
              </a>
            )}
            {track.spotify_url && (
              <a 
                href={track.spotify_url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-green-600 hover:text-green-700 text-xs sm:text-sm font-medium"
              >
                Spotify
              </a>
            )}
          </div>
          
          {/* Spotify Embed */}
          {track.spotify_track_id && (
            <div className="mt-3 sm:mt-4 w-full overflow-hidden">
              <iframe 
                style={{borderRadius: '12px'}}
                src={`https://open.spotify.com/embed/track/${track.spotify_track_id}?utm_source=generator`}
                width="100%" 
                height="152" 
                frameBorder="0" 
                allowfullscreen="" 
                allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" 
                loading="lazy"
                className="w-full max-w-full"
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
          className="flex items-center justify-center sm:justify-start gap-2 px-3 py-2 text-xs sm:text-sm font-medium rounded-lg border transition-colors hover:bg-gray-50 min-h-[36px] sm:min-h-[40px] sm:ml-4"
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