const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export const apiService = {
  async createSearch(queryText, conversationHistory = null, imageData = null, sessionData = null) {
    const requestBody = { 
      query_text: queryText,
      conversation_history: conversationHistory,
      image_data: imageData
    }
    
    // Only send session fields on refinements (when conversationHistory exists)
    if (conversationHistory && sessionData) {
      requestBody.user_session_id = sessionData.userSessionId
      requestBody.search_session_id = sessionData.searchSessionId
      requestBody.model = sessionData.model
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
  }
}