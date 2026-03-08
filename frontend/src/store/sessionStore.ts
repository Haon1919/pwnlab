import { create } from 'zustand'

export interface LabSession {
  id: string
  scenario_id: string | null
  status: string
  mode: string
  blackbox: boolean
  docker_network_name: string | null
  container_count: number
  session_offset: number | null
  flags_captured: string[]
  created_at: string
  updated_at: string
  stopped_at: string | null
  error_message: string | null
}

interface SessionState {
  sessions: LabSession[]
  activeSessions: LabSession[]
  setSessions: (sessions: LabSession[]) => void
  addSession: (session: LabSession) => void
  updateSession: (id: string, updates: Partial<LabSession>) => void
  removeSession: (id: string) => void
}

export const useSessionStore = create<SessionState>((set) => ({
  sessions: [],
  activeSessions: [],
  setSessions: (sessions) => set({
    sessions,
    activeSessions: sessions.filter((s) => ['starting', 'running'].includes(s.status))
  }),
  addSession: (session) => set((state) => ({
    sessions: [session, ...state.sessions],
    activeSessions: ['starting', 'running'].includes(session.status)
      ? [session, ...state.activeSessions]
      : state.activeSessions
  })),
  updateSession: (id, updates) => set((state) => ({
    sessions: state.sessions.map((s) => s.id === id ? { ...s, ...updates } : s),
    activeSessions: state.sessions
      .map((s) => s.id === id ? { ...s, ...updates } : s)
      .filter((s) => ['starting', 'running'].includes(s.status))
  })),
  removeSession: (id) => set((state) => ({
    sessions: state.sessions.filter((s) => s.id !== id),
    activeSessions: state.activeSessions.filter((s) => s.id !== id)
  }))
}))
