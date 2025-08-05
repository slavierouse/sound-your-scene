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
    
    return await this.makeRequestWithRetry(`${API_BASE_URL}/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    })
  },

  async makeRequestWithRetry(url, options, maxRetries = 10) {
    let attempt = 0
    
    while (attempt < maxRetries) {
      try {
        const response = await fetch(url, options)
        
        // Handle rate limiting (429) and overload (503) with retry
        if (response.status === 429 || response.status === 503) {
          const errorData = await response.json().catch(() => ({}))
          const retryAfter = response.headers.get('Retry-After') || Math.pow(2, attempt)
          const delay = Math.min(parseInt(retryAfter) * 1000, 60000) // Max 60 seconds
          
          console.log(`Request ${response.status === 429 ? 'rate limited' : 'overloaded'}, retrying in ${delay/1000}s (attempt ${attempt + 1}/${maxRetries})`)
          
          // Throw error with retry info for UI to display
          throw new Error(`${errorData.error || 'Server busy'}. Retrying in ${Math.ceil(delay/1000)} seconds... (${attempt + 1}/${maxRetries})`)
        }
        
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}))
          throw new Error(errorData.error || errorData.detail || 'Request failed')
        }

        return response.json()
        
      } catch (error) {
        attempt++
        
        // If it's our rate limit/overload error, wait and retry
        if (error.message.includes('Retrying in') && attempt < maxRetries) {
          const delayMatch = error.message.match(/(\d+) seconds/)
          const delay = delayMatch ? parseInt(delayMatch[1]) * 1000 : Math.pow(2, attempt) * 1000
          
          await new Promise(resolve => setTimeout(resolve, delay))
          continue
        }
        
        // For other errors or max attempts reached, throw immediately
        if (attempt >= maxRetries) {
          throw new Error(`Request failed after ${maxRetries} attempts: ${error.message}`)
        }
        
        // Exponential backoff for network errors
        const delay = Math.min(Math.pow(2, attempt) * 1000, 30000) // Max 30 seconds
        console.log(`Network error, retrying in ${delay/1000}s (attempt ${attempt + 1}/${maxRetries})`)
        await new Promise(resolve => setTimeout(resolve, delay))
      }
    }
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