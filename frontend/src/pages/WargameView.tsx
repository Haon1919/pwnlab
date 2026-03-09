import React, { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { sessionsApi } from '../api/sessions'
import WargameStatus from '../components/WargameStatus'
import type { LabSession } from '../store/sessionStore'
import { ArrowLeft, Terminal } from 'lucide-react'

export default function WargameView() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const [session, setSession] = useState<LabSession | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!sessionId) return
    sessionsApi.get(sessionId)
      .then(setSession)
      .catch(() => setError('Session not found'))
      .finally(() => setLoading(false))
  }, [sessionId])

  if (loading) return <div className="text-gray-500 animate-pulse">Loading...</div>
  if (error) return <div className="text-red-400">{error}</div>
  if (!session) return null

  return (
    <div className="space-y-4 max-w-xl">
      <div className="flex items-center gap-3">
        <Link to="/" className="text-gray-500 hover:text-gray-300 transition-colors">
          <ArrowLeft size={16} />
        </Link>
        <h1 className="text-xl font-bold">
          War Games <span className="text-cyan-400 font-mono text-sm">{session.id.slice(0, 8)}</span>
        </h1>
      </div>

      <div className="text-xs text-gray-500">
        Scenario: {session.blackbox ? '[blackbox]' : session.scenario_id} ·
        Network: {session.docker_network_name || 'N/A'}
      </div>

      {sessionId && <WargameStatus sessionId={sessionId} autoRefresh={session.status === 'running'} />}

      {session.status === 'running' && (
        <div className="terminal-card">
          <div className="flex items-center gap-2 text-gray-400 mb-2 text-xs font-bold uppercase">
            <Terminal size={12} />
            Attack carefully — you're being watched
          </div>
          <div className="bg-gray-950 rounded p-3 font-mono text-xs text-gray-400">
            <div className="text-green-600"># Stay stealthy. Avoid aggressive scans.</div>
            <div>$ docker exec -it blaqliq-attacker-{session.id.slice(0, 8)} bash</div>
            <div className="text-yellow-600"># nmap -T1 (slow) instead of nmap -T4 (aggressive)</div>
          </div>
        </div>
      )}

      <div className="text-center">
        <Link to={`/sessions/${sessionId}`} className="text-cyan-400 hover:underline text-sm">
          → Session Details &amp; Flag Submission
        </Link>
      </div>
    </div>
  )
}
