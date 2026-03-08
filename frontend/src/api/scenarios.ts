import { apiClient } from './client'

export interface Scenario {
  id: string
  name: string
  difficulty: string
  tags: string[]
  ai_generated: boolean
  is_public: boolean
  download_count: number
  wargame_enabled: boolean
  rating: number | null
  created_at: string
}

export const scenariosApi = {
  list: async (params?: { difficulty?: string; tag?: string }): Promise<Scenario[]> => {
    const { data } = await apiClient.get('/scenarios', { params })
    return data
  },

  get: async (id: string): Promise<Scenario> => {
    const { data } = await apiClient.get(`/scenarios/${id}`)
    return data
  },

  getYaml: async (id: string): Promise<string> => {
    const { data } = await apiClient.get(`/scenarios/${id}/yaml`)
    return data.yaml
  },
}
