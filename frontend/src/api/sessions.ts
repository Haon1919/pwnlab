import { apiClient } from './client'
import type { LabSession } from '../store/sessionStore'

export interface StartSessionRequest {
  scenario_id: string
  wargame?: boolean
  blackbox?: boolean
}

export const sessionsApi = {
  list: async (): Promise<LabSession[]> => {
    const { data } = await apiClient.get('/sessions')
    return data
  },

  get: async (id: string): Promise<LabSession> => {
    const { data } = await apiClient.get(`/sessions/${id}`)
    return data
  },

  start: async (req: StartSessionRequest): Promise<LabSession> => {
    const { data } = await apiClient.post('/sessions', req)
    return data
  },

  stop: async (id: string): Promise<void> => {
    await apiClient.delete(`/sessions/${id}`)
  },

  submitFlag: async (sessionId: string, flag: string, objectiveId: string) => {
    const { data } = await apiClient.post(`/sessions/${sessionId}/flag`, {
      flag,
      objective_id: objectiveId,
    })
    return data
  },
}
