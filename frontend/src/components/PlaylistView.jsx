import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { apiService } from '../services/apiService'
import { bookmarkService } from '../services/bookmarkService'
import ResultsList from './ResultsList'
import FloatingActionButtonNewSearch from './FloatingActionButtonNewSearch'
import LoadingMessage from './LoadingMessage'

function PlaylistView() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [playlist, setPlaylist] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [bookmarkKey, setBookmarkKey] = useState(0)

  useEffect(() => {
    const loadPlaylist = async () => {
      try {
        setIsLoading(true)
        setError(null)
        const playlistData = await apiService.getPlaylist(id)
        setPlaylist(playlistData)
        
        // Clear existing bookmarks and load playlist tracks as bookmarks for consistency
        bookmarkService.clearAllBookmarks()
        playlistData.tracks.forEach((track, index) => {
          // Add tracks as bookmarks (without job_id and original_query since this is a shared playlist)
          bookmarkService.addBookmark(track, null, 'Shared Playlist', index)
        })
        // Restore the playlist ID so export works after viewing shared playlist
        bookmarkService.setPlaylistId(id)
        setBookmarkKey(prev => prev + 1)
        
      } catch (err) {
        console.error('Error loading playlist:', err)
        setError('Failed to load playlist. It may not exist or may have been removed.')
      } finally {
        setIsLoading(false)
      }
    }

    if (id) {
      loadPlaylist()
    }
  }, [id])

  const updateBookmarkCount = () => {
    setBookmarkKey(prev => prev + 1)
  }

  const handleNewSearch = () => {
    // Clear bookmarks and navigate to home
    bookmarkService.clearAllBookmarks()
    navigate('/')
  }

  if (isLoading) {
    return (
      <div className="min-h-screen w-full bg-light-cream font-sans">
        <div className="pt-4 px-4 sm:pt-8 sm:pl-12 flex items-center">
          <span className="text-sm sm:text-base font-medium text-gray-700 mr-4">
            Sound your scene
          </span>
          <span className="inline-block px-2 py-1 text-xs sm:px-3 sm:text-sm font-medium text-red-700 bg-red-100 rounded-full">
            Demo Version
          </span>
        </div>
        <header className="pt-4 px-4 pb-4 sm:pt-6 sm:pl-12 sm:pb-6">
          <h1 className="text-xl sm:text-2xl font-medium text-gray-900 mb-2">
            Loading Playlist...
          </h1>
        </header>
        <main className="px-4 pb-16 sm:pl-12 sm:pr-12 sm:pb-24">
          <LoadingMessage message="Loading playlist..." />
        </main>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen w-full bg-light-cream font-sans">
        <div className="pt-4 px-4 sm:pt-8 sm:pl-12 flex items-center">
          <span className="text-sm sm:text-base font-medium text-gray-700 mr-4">
            Sound your scene
          </span>
          <span className="inline-block px-2 py-1 text-xs sm:px-3 sm:text-sm font-medium text-red-700 bg-red-100 rounded-full">
            Demo Version
          </span>
        </div>
        <header className="pt-4 px-4 pb-4 sm:pt-6 sm:pl-12 sm:pb-6">
          <h1 className="text-xl sm:text-2xl font-medium text-gray-900 mb-2">
            Playlist Not Found
          </h1>
        </header>
        <main className="px-4 pb-16 sm:pl-12 sm:pr-12 sm:pb-24">
          <div className="mb-8 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-700 mb-3">{error}</p>
            <button
              onClick={handleNewSearch}
              className="px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition-colors font-medium"
            >
              Start New Search
            </button>
          </div>
        </main>
      </div>
    )
  }

  return (
    <div className="min-h-screen w-full bg-light-cream font-sans">
      <div className="pt-4 px-4 sm:pt-8 sm:pl-12 flex items-center">
        <span className="text-sm sm:text-base font-medium text-gray-700 mr-4">
          Sound your scene
        </span>
        <span className="inline-block px-2 py-1 text-xs sm:px-3 sm:text-sm font-medium text-red-700 bg-red-100 rounded-full">
          Demo Version
        </span>
      </div>
      
      {/* Header */}
      <header className="pt-4 px-4 pb-4 sm:pt-6 sm:pl-12 sm:pb-6">
        <h1 className="text-xl sm:text-2xl font-medium text-gray-900 mb-2">
          Shared Playlist
        </h1>
        <p className="text-sm sm:text-base text-gray-600">
          {playlist?.track_count || 0} tracks • Created {playlist?.created_at ? new Date(playlist.created_at).toLocaleDateString() : ''}
          {playlist?.access_count > 1 && (
            <span className="ml-2 text-gray-500">• Viewed {playlist.access_count} times</span>
          )}
        </p>
      </header>

      {/* Main Content */}
      <main className="px-4 pb-16 sm:pl-12 sm:pr-12 sm:pb-24">
        <div className="w-full max-w-4xl">
          {/* Results Display - reuse existing ResultsList component */}
          <ResultsList 
            results={null} // Not used when isViewingSaved is true
            meta={null} // Not used when isViewingSaved is true
            isViewingSaved={true} // Force saved view mode
            onBookmarkChange={updateBookmarkCount}
            onClearAll={() => {}} // No clear all for playlist view
            bookmarkKey={bookmarkKey}
            hideBookmarkButton={true} // Hide bookmark buttons in playlist permalink view
          />
        </div>
      </main>

      {/* Floating Action Buttons - only new search for playlist permalink view */}
      <FloatingActionButtonNewSearch 
        hasResults={true}
        onNewSearch={handleNewSearch}
      />
    </div>
  )
}

export default PlaylistView