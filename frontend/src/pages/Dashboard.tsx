import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { sessionsApi } from '../api/sessions'
import type { LabSession } from '../store/sessionStore'
import { Terminal, Play, Square, AlertCircle, CheckCircle, Loader } from 'lucide-react'

const STATUS_CONFIG: Record<string, { color: string; icon: React.ReactNode }> = {
  running: { color: 'text-green-400', icon: <CheckCircle size={14} /> },
  starting: { color: 'text-yellow-400', icon: <Loader size={14} className="animate-spin" /> },
  stopping: { color: 'text-yellow-400', icon: <Loader size={14} className="animate-spin" /> },
  stopped: { color: 'text-gray-500', icon: <Square size={14} /> },
  error: { color: 'text-red-400', icon: <AlertCircle size={14} /> },
}

export default function Dashboard() {
  const { user } = useAuthStore()
  const [sessions, setSessions] = useState<LabSession[]>([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    sessionsApi.list().then(setSessions).finally(() => setLoading(false))
    const interval = setInterval(() => {
      sessionsApi.list().then(setSessions)
    }, 10000)
    return () => clearInterval(interval)
  }, [])

  const handleStop = async (id: string) => {
    try {
      await sessionsApi.stop(id)
      setSessions(prev => prev.map(s => s.id === id ? { ...s, status: 'stopped' } : s))
    } catch (e: any) {
      console.error('Stop failed:', e)
    }
  }

  const activeSessions = sessions.filter(s => ['starting', 'running'].includes(s.status))
  const pastSessions = sessions.filter(s => !['starting', 'running'].includes(s.status))

  return (
    <div className="space-y-6">
      {/* Welcome */}
      <div>
        <h1 className="text-xl font-bold text-gray-100">
          Welcome back, <span className="text-green-400">{user?.username}</span>
        </h1>
        <p className="text-gray-500 text-sm mt-1">
          {activeSessions.length} active session{activeSessions.length !== 1 ? 's' : ''} ·
          <Link to="/scenarios" className="text-cyan-400 hover:underline ml-1">Browse scenarios</Link>
        </p>
      </div>

      {/* Active Sessions */}
      {activeSessions.length > 0 && (
        <div>
          <h2 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-3">Active Sessions</h2>
          <div className="grid gap-3">
            {activeSessions.map((session) => {
              const cfg = STATUS_CONFIG[session.status] || STATUS_CONFIG.stopped
              return (
                <div key={session.id} className="terminal-card flex items-center gap-4">
                  <div className={`flex items-center gap-1.5 ${cfg.color}`}>
                    {cfg.icon}
                    <span className="text-xs font-mono uppercase">{session.status}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-mono">
                      {session.blackbox ? (
                        <span className="text-yellow-400">[BLACKBOX]</span>
                      ) : (
                        <span className="text-cyan-400">{session.scenario_id || 'unknown'}</span>
                      )}
                    </div>
                    <div className="text-xs text-gray-500 mt-0.5">
                      {session.id.slice(0, 8)} · {session.mode} · {session.container_count} containers
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Link
                      to={`/sessions/${session.id}`}
                      className="text-xs btn-secondary py-1 px-2"
                    >
                      Details
                    </Link>
                    {session.mode === 'wargame' && (
                      <Link
                        to={`/wargame/${session.id}`}
                        className="text-xs bg-purple-800 hover:bg-purple-700 text-white py-1 px-2 rounded"
                      >
                        War Games
                      </Link>
                    )}
                    <button
                      onClick={() => handleStop(session.id)}
                      className="text-xs btn-danger py-1 px-2"
                    >
                      Stop
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Quick Start */}
      <div className="terminal-card border-dashed">
        <div className="flex items-center gap-2 text-gray-400 mb-3">
          <Play size={14} />
          <span className="text-sm font-bold">Quick Start</span>
        </div>
        <p className="text-xs text-gray-500 mb-3">
          Launch a lab directly from the command line or pick a scenario from the library.
        </p>
        <div className="bg-gray-950 rounded p-3 font-mono text-xs text-green-400">
          <div>$ pwnlab session start dvwa-beginner</div>
          <div className="text-gray-600">$ pwnlab session start dvwa-hardened --wargame</div>
          <div className="text-gray-600">$ pwnlab ai blackbox</div>
        </div>
        <Link to="/scenarios" className="btn-primary inline-block mt-3 text-sm">
          Browse Scenarios →
        </Link>
      </div>

      {/* Past Sessions */}
      {pastSessions.length > 0 && (
        <div>
          <h2 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-3">Recent Sessions</h2>
          <div className="terminal-card">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-gray-500 border-b border-gray-800">
                  <th className="text-left pb-2">ID</th>
                  <th className="text-left pb-2">Scenario</th>
                  <th className="text-left pb-2">Mode</th>
                  <th className="text-left pb-2">Status</th>
                  <th className="text-left pb-2">Flags</th>
                </tr>
              </thead>
              <tbody>
                {pastSessions.slice(0, 10).map((s) => {
                  const cfg = STATUS_CONFIG[s.status] || STATUS_CONFIG.stopped
                  return (
                    <tr key={s.id} className="border-b border-gray-800 last:border-0">
                      <td className="py-1.5 font-mono text-gray-400">{s.id.slice(0, 8)}</td>
                      <td className="py-1.5 text-gray-300">
                        {s.blackbox ? '[blackbox]' : (s.scenario_id || '?')}
                      </td>
                      <td className="py-1.5 text-gray-500">{s.mode}</td>
                      <td className={`py-1.5 ${cfg.color} flex items-center gap-1`}>
                        {cfg.icon} {s.status}
                      </td>
                      <td className="py-1.5 text-gray-500">{s.flags_captured.length}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {loading && (
        <div className="text-center text-gray-500 text-sm py-8 animate-pulse">Loading sessions...</div>
      )}
    </div>
  )
}
