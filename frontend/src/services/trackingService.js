import { apiService } from './apiService'

class TrackingService {
  constructor() {
    this.sessionData = null
    this.currentJobId = null
    this.conversationTurn = null
  }

  // Update session data from App component
  setSession(sessionData, jobId = null, conversationTurn = null) {
    this.sessionData = sessionData
    this.currentJobId = jobId
    this.conversationTurn = conversationTurn
  }

  // Simple tracking methods for components
  async click(type, track, rankPosition, jobId = null) {
    if (!this.sessionData?.userSessionId) return

    const finalJobId = jobId || this.currentJobId

    return await apiService.trackEvent({
      event_type: `${type}_click`,
      user_session_id: this.sessionData.userSessionId,
      search_session_id: this.sessionData.searchSessionId,
      job_id: finalJobId,
      spotify_track_id: track.spotify_track_id,
      rank_position: rankPosition,
      conversation_turn: this.conversationTurn
    })
  }

  async play(track, rankPosition, jobId = null) {
    if (!this.sessionData?.userSessionId) return

    return await apiService.trackEvent({
      event_type: 'spotify_embed_play',
      user_session_id: this.sessionData.userSessionId,
      search_session_id: this.sessionData.searchSessionId,
      job_id: jobId || this.currentJobId,
      spotify_track_id: track.spotify_track_id,
      rank_position: rankPosition,
      conversation_turn: this.conversationTurn
    })
  }

  async pagination(page) {
    if (!this.sessionData?.userSessionId) return

    return await apiService.trackEvent({
      event_type: 'pagination',
      user_session_id: this.sessionData.userSessionId,
      search_session_id: this.sessionData.searchSessionId,
      job_id: this.currentJobId,
      rank_position: page,
      conversation_turn: this.conversationTurn
    })
  }
}

export const emit = new TrackingService()