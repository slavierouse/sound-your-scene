import { APP_CONFIG } from '../config/constants'

const API_BASE_URL = APP_CONFIG.API_BASE_URL

export const apiService = {
  async createSearch(queryText, conversationHistory = null, imageData = null, sessionData = null) {
    const requestBody = { 
      query_text: queryText,
      conversation_history: conversationHistory,
      image_data: imageData
    }
    
    // Send session fields based on context
    if (conversationHistory && sessionData) {
      // Refinement: send all session fields to continue same conversation
      requestBody.user_session_id = sessionData.userSessionId
      requestBody.search_session_id = sessionData.searchSessionId
      requestBody.model = sessionData.model
    } else if (!conversationHistory && sessionData && sessionData.userSessionId) {
      // New search by existing user: send userSessionId only (let backend create new search session)
      requestBody.user_session_id = sessionData.userSessionId
      // Don't send search_session_id or model - let backend generate new ones
    }
    
    const response = await fetch(`${API_BASE_URL}/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    })

    if (!response.ok) {
      throw new Error('Search request failed')
    }

    return response.json()
  },

  async getJobStatus(jobId) {
    const response = await fetch(`${API_BASE_URL}/jobs/${jobId}`)
    
    if (!response.ok) {
      throw new Error('Failed to fetch job status')
    }

    return response.json()
  },

  async createOrUpdatePlaylist(trackIds, searchSessionId) {
    const response = await fetch(`${API_BASE_URL}/playlists`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        track_ids: trackIds,
        search_session_id: searchSessionId
      }),
    })

    if (!response.ok) {
      throw new Error('Failed to create/update playlist')
    }

    return response.json()
  },

  async getPlaylist(playlistId) {
    const response = await fetch(`${API_BASE_URL}/playlists/${playlistId}`)
    
    if (!response.ok) {
      throw new Error('Failed to fetch playlist')
    }

    return response.json()
  },

  async emailPlaylist(playlistId, email) {
    const response = await fetch(`${API_BASE_URL}/playlists/${playlistId}/email`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email }),
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Failed to send email')
    }

    return response.json()
  },

  async trackEvent(eventData) {
    try {
      const response = await fetch(`${API_BASE_URL}/track-events`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(eventData),
      })

      if (!response.ok) {
        console.warn('Failed to track event:', eventData)
      }
      
      return response.ok
    } catch (error) {
      console.warn('Failed to track event:', eventData, error)
      return false
    }
  }
}