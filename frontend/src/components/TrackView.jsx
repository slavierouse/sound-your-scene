import { useState, useEffect, useRef } from 'react'
import { BookmarkIcon, BookmarkSlashIcon } from '@heroicons/react/24/outline'
import { bookmarkService } from '../services/bookmarkService'
import { emit } from '../services/trackingService'

function TrackView({ track, index, jobId, originalQuery, relevanceIndex, onBookmarkChange, bookmarkKey, hideBookmarkButton = false }) {
  const [isBookmarked, setIsBookmarked] = useState(false)
  const embedRef = useRef(null)
  const hasTrackedPlay = useRef(false)
  
  useEffect(() => {
    setIsBookmarked(bookmarkService.isBookmarked(track.spotify_track_id))
  }, [track.spotify_track_id, bookmarkKey])

  // Create Spotify embed with specific event listener
  useEffect(() => {
    if (!embedRef.current || !track.spotify_track_id) return

    const embedContainer = embedRef.current
    const embedId = `spotify-embed-${track.spotify_track_id}-${index}`
    
    // Create iframe programmatically with unique ID
    const iframe = document.createElement('iframe')
    iframe.id = embedId
    iframe.src = `https://open.spotify.com/embed/track/${track.spotify_track_id}?theme=0`
    iframe.width = '100%'
    iframe.height = '152'
    iframe.frameBorder = '0'
    iframe.allowFullscreen = true
    iframe.allow = 'autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture'
    iframe.loading = 'lazy'
    iframe.style.borderRadius = '12px'
    iframe.title = `Spotify player for ${track.track} by ${track.artist}`
    
    // Clear container and add iframe
    embedContainer.innerHTML = ''
    embedContainer.appendChild(iframe)

    // Listen for messages from this specific embed
    const handleMessage = (event) => {
      if (event.origin !== 'https://open.spotify.com') return
      if (event.source !== iframe.contentWindow) return // Only from our iframe
      
      try {
        // event.data is already parsed if it's an object
        const data = typeof event.data === 'string' ? JSON.parse(event.data) : event.data
        console.log('Spotify embed message:', data) // Debug: see what messages we get
        
        if (data.type === 'playback_update' && data.payload) {
          const payload = data.payload
          // Track when playback starts (not paused and position near 0) - but only once
          if (!payload.isPaused && payload.position <= 1000 && !hasTrackedPlay.current) {
            hasTrackedPlay.current = true
            console.log('Tracking play for:', track.track)
            emit.play(track, index + 1, jobId)
          }
        }
      } catch (error) {
        console.log('Error parsing Spotify message:', error, event.data)
      }
    }

    window.addEventListener('message', handleMessage)
    
    return () => {
      window.removeEventListener('message', handleMessage)
    }
  }, [track.spotify_track_id, track.track, track.artist, index])

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
                onClick={() => {
                  emit.click('youtube', track, index + 1, jobId)
                  // Don't prevent default - let link open normally
                }}
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
                onClick={() => {
                  emit.click('spotify', track, index + 1, jobId)
                  // Don't prevent default - let link open normally
                }}
              >
                Spotify
              </a>
            )}
          </div>
          
          {/* Spotify Embed */}
          {track.spotify_track_id && (
            <div 
              ref={embedRef}
              className="mt-3 sm:mt-4 w-full overflow-hidden"
            >
              {/* Iframe will be created programmatically */}
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
        
        {/* Bookmark Button - Hidden in playlist permalink view */}
        {!hideBookmarkButton && (
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
        )}
      </div>
    </div>
  )
}

export default TrackView