const STORAGE_KEY = 'soundbymood_v1_bookmarks'
const MAX_BOOKMARKS = 100

class BookmarkService {
  constructor() {
    this.bookmarks = this.loadBookmarks()
  }

  loadBookmarks() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (!stored) return []
      
      const data = JSON.parse(stored)
      // Validate structure
      if (!Array.isArray(data)) return []
      
      return data.filter(bookmark => 
        bookmark.track && 
        bookmark.job_id && 
        bookmark.original_query && 
        typeof bookmark.saved_at === 'string'
      )
    } catch (error) {
      console.error('Error loading bookmarks:', error)
      return []
    }
  }

  saveBookmarks() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.bookmarks))
    } catch (error) {
      console.error('Error saving bookmarks:', error)
    }
  }

  addBookmark(track, jobId, originalQuery, relevanceIndex) {
    // Check if already bookmarked
    if (this.isBookmarked(track.spotify_track_id)) {
      return false
    }

    // Check limit
    if (this.bookmarks.length >= MAX_BOOKMARKS) {
      throw new Error(`Cannot save more than ${MAX_BOOKMARKS} tracks`)
    }

    const bookmark = {
      track,
      job_id: jobId,
      original_query: originalQuery,
      relevance_index: relevanceIndex,
      saved_at: new Date().toISOString()
    }

    this.bookmarks.push(bookmark)
    this.saveBookmarks()
    return true
  }

  removeBookmark(trackId) {
    const initialLength = this.bookmarks.length
    this.bookmarks = this.bookmarks.filter(bookmark => 
      bookmark.track.spotify_track_id !== trackId
    )
    
    if (this.bookmarks.length < initialLength) {
      this.saveBookmarks()
      return true
    }
    return false
  }

  isBookmarked(trackId) {
    return this.bookmarks.some(bookmark => 
      bookmark.track.spotify_track_id === trackId
    )
  }

  getBookmarks() {
    return [...this.bookmarks]
  }

  getBookmarkCount() {
    return this.bookmarks.length
  }

  clearAllBookmarks() {
    this.bookmarks = []
    this.saveBookmarks()
  }

  // Session management
  clearBookmarksOnNewQuery() {
    this.clearAllBookmarks()
  }
}

export const bookmarkService = new BookmarkService()