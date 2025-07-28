const API_BASE_URL = 'http://localhost:8000'

export const apiService = {
  async createSearch(queryText) {
    const response = await fetch(`${API_BASE_URL}/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query_text: queryText }),
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