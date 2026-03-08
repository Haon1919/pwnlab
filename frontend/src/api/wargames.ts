import { apiClient } from './client'

export interface WargameState {
  id: number
  session_id: string
  detection_score: number
  detection_level: 'clean' | 'warning' | 'detected' | 'busted'
  is_active: boolean
  busted_at: string | null
  won_at: string | null
  last_poll_at: string | null
  created_at: string
}

export interface DetectionEvent {
  id: number
  event_type: string
  severity: string
  raw_log_line: string
  source_ip: string | null
  score_delta: number
  timestamp: string
}

export const wargamesApi = {
  getState: async (sessionId: string): Promise<WargameState> => {
    const { data } = await apiClient.get(`/wargames/${sessionId}`)
    return data
  },

  getEvents: async (sessionId: string, limit = 20): Promise<DetectionEvent[]> => {
    const { data } = await apiClient.get(`/wargames/${sessionId}/events`, { params: { limit } })
    return data
  },
}
