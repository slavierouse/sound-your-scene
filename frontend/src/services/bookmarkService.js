import { APP_CONFIG } from '../config/constants'
import { apiService } from './apiService'

const STORAGE_KEY = 'soundbymood_v1_bookmarks'
const MAX_BOOKMARKS = APP_CONFIG.MAX_PLAYLIST_SIZE

class BookmarkService {
  constructor() {
    const data = this.loadData()
    this.bookmarks = data.bookmarks
    this.playlistId = data.playlistId
    this.playlistSyncCallback = null
  }

  // Set callback for playlist sync
  setPlaylistSyncCallback(callback) {
    this.playlistSyncCallback = callback
  }

  loadData() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (!stored) return { bookmarks: [], playlistId: null }
      
      const data = JSON.parse(stored)
      
      // Handle legacy format (array of bookmarks)
      if (Array.isArray(data)) {
        const filtered = data.filter(bookmark => 
          bookmark.track && 
          typeof bookmark.saved_at === 'string'
        )
        return { bookmarks: filtered, playlistId: null }
      }
      
      // Handle new format (object with bookmarks and playlistId)
      if (data && typeof data === 'object') {
        const bookmarks = Array.isArray(data.bookmarks) ? data.bookmarks.filter(bookmark => 
          bookmark.track && 
          typeof bookmark.saved_at === 'string'
        ) : []
        return { 
          bookmarks, 
          playlistId: data.playlistId || null 
        }
      }
      
      return { bookmarks: [], playlistId: null }
    } catch (error) {
      console.error('Error loading bookmark data:', error)
      return { bookmarks: [], playlistId: null }
    }
  }

  saveData() {
    try {
      const data = {
        bookmarks: this.bookmarks,
        playlistId: this.playlistId
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
    } catch (error) {
      console.error('Error saving bookmark data:', error)
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
    this.saveData()
    
    // Trigger playlist sync
    if (this.playlistSyncCallback) {
      this.playlistSyncCallback()
    }
    
    return true
  }

  removeBookmark(trackId) {
    const initialLength = this.bookmarks.length
    this.bookmarks = this.bookmarks.filter(bookmark => 
      bookmark.track.spotify_track_id !== trackId
    )
    
    if (this.bookmarks.length < initialLength) {
      this.saveData()
      
      // Trigger playlist sync
      if (this.playlistSyncCallback) {
        this.playlistSyncCallback()
      }
      
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

  getTrackIds() {
    return this.bookmarks.map(bookmark => bookmark.track.spotify_track_id)
  }

  getPlaylistId() {
    return this.playlistId
  }

  setPlaylistId(playlistId) {
    this.playlistId = playlistId
    this.saveData()
  }

  clearAllBookmarks() {
    this.bookmarks = []
    this.playlistId = null
    this.saveData()
  }

  // Session management
  clearBookmarksOnNewQuery() {
    this.clearAllBookmarks()
  }
}

export const bookmarkService = new BookmarkService()