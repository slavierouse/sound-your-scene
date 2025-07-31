import { useState, useMemo, useEffect } from 'react'
import TrackView from './TrackView'
import { bookmarkService } from '../services/bookmarkService'

function ResultsList({ results, meta, isViewingSaved, onBookmarkChange, onClearAll, bookmarkKey }) {
  const [currentPage, setCurrentPage] = useState(1)
  const [sortBy, setSortBy] = useState('relevance')
  const [savedTracks, setSavedTracks] = useState([])
  
  const RESULTS_PER_PAGE = 10

  // Load saved tracks when viewing saved
  useEffect(() => {
    if (isViewingSaved) {
      const tracks = bookmarkService.getBookmarks()
      setSavedTracks(tracks)
      setSortBy('saved') // Default to saved order for bookmarks
      setCurrentPage(1) // Reset to first page when switching to saved view
    }
  }, [isViewingSaved])

  // Also reload saved tracks when bookmarkKey changes (when bookmarks are added/removed)
  useEffect(() => {
    if (isViewingSaved) {
      setSavedTracks(bookmarkService.getBookmarks())
    }
  }, [bookmarkKey, isViewingSaved])

  const currentResults = isViewingSaved ? savedTracks.map(bookmark => bookmark.track) : results
  const hasResults = currentResults && currentResults.length > 0
  const isEmpty = isViewingSaved ? savedTracks.length === 0 : (meta && meta.result_count === 0)

  // Sort results based on selected criteria
  const sortedResults = useMemo(() => {
    if (!currentResults || currentResults.length === 0) return []
    
    if (isViewingSaved) {
      // For saved tracks, work with the bookmark objects to preserve order info
      const sorted = [...savedTracks].sort((a, b) => {
        switch (sortBy) {
          case 'latest':
            return b.track.album_release_year - a.track.album_release_year
          case 'popularity':
            const aViews = a.track.views || 0
            const bViews = b.track.views || 0
            return bViews - aViews
          case 'saved':
          default:
            // Sort by saved_at timestamp (first saved first)
            return new Date(a.saved_at) - new Date(b.saved_at)
        }
      })
      return sorted.map(bookmark => bookmark.track)
    } else {
      // For search results, sort the tracks directly
      const sorted = [...currentResults].sort((a, b) => {
        switch (sortBy) {
          case 'latest':
            return b.album_release_year - a.album_release_year
          case 'popularity':
            if (!a.views && !b.views) return 0
            if (!a.views) return 1
            if (!b.views) return -1
            return b.views - a.views
          case 'relevance':
          default:
            return b.relevance_score - a.relevance_score
        }
      })
      return sorted
    }
  }, [currentResults, savedTracks, sortBy, isViewingSaved])

  // Early return after all hooks are called
  if (!isViewingSaved && !results && !meta) return null

  // Calculate pagination
  const totalPages = Math.ceil(sortedResults.length / RESULTS_PER_PAGE)
  const startIndex = (currentPage - 1) * RESULTS_PER_PAGE
  const endIndex = startIndex + RESULTS_PER_PAGE
  const paginatedResults = sortedResults.slice(startIndex, endIndex)

  // Generate page numbers for pagination
  const getPageNumbers = () => {
    if (totalPages <= 7) {
      // Show all pages if 7 or fewer
      return Array.from({ length: totalPages }, (_, i) => i + 1)
    }

    const pages = new Set()
    
    // Always include first page
    pages.add(1)
    
    // Always include last page
    pages.add(totalPages)
    
    // Always include current page
    pages.add(currentPage)
    
    // Include previous page if it exists
    if (currentPage > 1) {
      pages.add(currentPage - 1)
    }
    
    // Include next page if it exists
    if (currentPage < totalPages) {
      pages.add(currentPage + 1)
    }
    
    // Convert to sorted array
    const sortedPages = Array.from(pages).sort((a, b) => a - b)
    
    // Add ellipsis where there are gaps
    const result = []
    for (let i = 0; i < sortedPages.length; i++) {
      const current = sortedPages[i]
      const next = sortedPages[i + 1]
      
      result.push(current)
      
      // Add ellipsis if there's a gap of more than 1
      if (next && next - current > 1) {
        result.push('...')
      }
    }
    
    return result
  }

  // Reset to page 1 when sorting changes
  const handleSortChange = (newSort) => {
    setSortBy(newSort)
    setCurrentPage(1)
  }

  return (
    <>
      {/* Meta Information */}
      {(meta || isViewingSaved) && (
        <div className="mb-6 sm:mb-8">
          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3 sm:gap-0">
            <h3 className="text-base sm:text-lg font-medium text-gray-900">
              {isViewingSaved 
                ? `Saved ${savedTracks.length} results`
                : `Found ${meta?.result_count || 0} results`
              }
            </h3>
            
            {/* Sort Controls - only show if we have results */}
            {hasResults && (
              <div className="flex flex-wrap gap-4 sm:gap-6 items-center">
                <span className="text-xs sm:text-sm text-gray-600">Sort by:</span>
                <div className="flex gap-4 sm:gap-6">
                  <button
                    onClick={() => handleSortChange(isViewingSaved ? 'saved' : 'relevance')}
                    className={`text-xs sm:text-sm ${(sortBy === 'relevance' || sortBy === 'saved') ? 'text-teal-600 font-medium' : 'text-gray-500 hover:text-gray-700'}`}
                  >
                    {isViewingSaved ? 'Saved' : 'Relevance'}
                  </button>
                  <button
                    onClick={() => handleSortChange('latest')}
                    className={`text-xs sm:text-sm ${sortBy === 'latest' ? 'text-teal-600 font-medium' : 'text-gray-500 hover:text-gray-700'}`}
                  >
                    Latest
                  </button>
                  <button
                    onClick={() => handleSortChange('popularity')}
                    className={`text-xs sm:text-sm ${sortBy === 'popularity' ? 'text-teal-600 font-medium' : 'text-gray-500 hover:text-gray-700'}`}
                  >
                    Popularity
                  </button>
                  
                  {/* Clear All Button - only show for saved tracks */}
                  {isViewingSaved && (
                    <button
                      onClick={() => {
                        if (confirm('Are you sure you want to clear all saved tracks?')) {
                          bookmarkService.clearAllBookmarks()
                          setSavedTracks([])
                          if (onBookmarkChange) onBookmarkChange()
                          // Switch back to search view after clearing
                          if (onClearAll) onClearAll()
                        }
                      }}
                      className="text-xs sm:text-sm text-red-600 hover:text-red-700 font-medium"
                    >
                      Clear All
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Empty State */}
      {isEmpty && (
        <div className="mb-6 sm:mb-8 p-4 sm:p-6 bg-yellow-50 border border-yellow-200 rounded-lg">
          <h4 className="text-base sm:text-lg font-medium text-yellow-800 mb-2">No results found</h4>
          <p className="text-sm sm:text-base text-yellow-700">
            Please try widening your search with different criteria, genres, or time periods.
          </p>
        </div>
      )}

      {/* Results */}
      {hasResults && (
        <div className="mb-6 sm:mb-8">
          {/* Results */}
          <div className="space-y-3 sm:space-y-4 mb-6 sm:mb-8">
            {paginatedResults.map((track, index) => (
              <TrackView 
                key={track.spotify_track_id || index} 
                track={track} 
                index={startIndex + index}
                jobId={meta?.job_id}
                originalQuery={meta?.original_query}
                relevanceIndex={track.rank_position - 1} // Convert to 0-based index
                onBookmarkChange={onBookmarkChange}
                bookmarkKey={bookmarkKey}
              />
            ))}
          </div>

          {/* Pagination - Left Aligned */}
          {totalPages > 1 && (
            <div className="flex gap-3 sm:gap-4 flex-wrap">
              {getPageNumbers().map((pageNum, index) => (
                <span key={index}>
                  {pageNum === '...' ? (
                    <span className="text-gray-400 text-xs sm:text-sm">...</span>
                  ) : (
                    <button
                      onClick={() => setCurrentPage(pageNum)}
                      className={`text-xs sm:text-sm min-h-[32px] px-2 ${
                        currentPage === pageNum
                          ? 'text-teal-600 font-medium'
                          : 'text-gray-500 hover:text-gray-700'
                      }`}
                    >
                      {pageNum}
                    </button>
                  )}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </>
  )
}

export default ResultsList