import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { sessionsApi } from '../api/sessions'
import type { LabSession } from '../store/sessionStore'
import { Terminal, Square, Flag, AlertCircle, CheckCircle, Loader } from 'lucide-react'

export default function ActiveSession() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const [session, setSession] = useState<LabSession | null>(null)
  const [loading, setLoading] = useState(true)
  const [stopping, setStopping] = useState(false)
  const [flagInput, setFlagInput] = useState('')
  const [objectiveId, setObjectiveId] = useState('flag-1')
  const [flagResult, setFlagResult] = useState<{ correct: boolean; message: string } | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!sessionId) return
    const fetch = () => {
      sessionsApi.get(sessionId).then(setSession).catch((e) => setError('Session not found'))
      setLoading(false)
    }
    fetch()
    const interval = setInterval(fetch, 8000)
    return () => clearInterval(interval)
  }, [sessionId])

  const handleStop = async () => {
    if (!sessionId) return
    setStopping(true)
    try {
      await sessionsApi.stop(sessionId)
      setSession(prev => prev ? { ...prev, status: 'stopped' } : null)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to stop session')
    } finally {
      setStopping(false)
    }
  }

  const submitFlag = async () => {
    if (!sessionId || !flagInput.trim()) return
    try {
      const result = await sessionsApi.submitFlag(sessionId, flagInput, objectiveId)
      setFlagResult(result)
    } catch (e: any) {
      setFlagResult({ correct: false, message: e.response?.data?.detail || 'Error' })
    }
  }

  if (loading) return <div className="text-gray-500 animate-pulse">Loading session...</div>
  if (error) return <div className="text-red-400">{error}</div>
  if (!session) return null

  const shortId = session.id.slice(0, 8)

  return (
    <div className="space-y-4 max-w-2xl">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">
          Session <span className="text-cyan-400 font-mono">{shortId}</span>
        </h1>
        {['starting', 'running'].includes(session.status) && (
          <button
            className="btn-danger text-sm flex items-center gap-1.5"
            onClick={handleStop}
            disabled={stopping}
          >
            {stopping ? <Loader size={14} className="animate-spin" /> : <Square size={14} />}
            Stop Session
          </button>
        )}
      </div>

      {/* Session details */}
      <div className="terminal-card space-y-2 text-sm">
        <div className="grid grid-cols-2 gap-2">
          <div>
            <span className="text-gray-500">Status</span>
            <div className={`font-mono mt-0.5 ${
              session.status === 'running' ? 'text-green-400' :
              session.status === 'error' ? 'text-red-400' : 'text-gray-400'
            }`}>{session.status}</div>
          </div>
          <div>
            <span className="text-gray-500">Mode</span>
            <div className="text-gray-300 mt-0.5">{session.mode}</div>
          </div>
          <div>
            <span className="text-gray-500">Scenario</span>
            <div className="text-cyan-400 mt-0.5 font-mono text-xs">
              {session.blackbox ? '[hidden - blackbox]' : (session.scenario_id || '?')}
            </div>
          </div>
          <div>
            <span className="text-gray-500">Containers</span>
            <div className="text-gray-300 mt-0.5">{session.container_count}</div>
          </div>
          <div>
            <span className="text-gray-500">Network</span>
            <div className="text-gray-400 mt-0.5 font-mono text-xs">{session.docker_network_name || 'N/A'}</div>
          </div>
          <div>
            <span className="text-gray-500">Flags Captured</span>
            <div className="text-green-400 mt-0.5">{session.flags_captured.length}</div>
          </div>
        </div>
      </div>

      {/* Attacker terminal hint */}
      {session.status === 'running' && (
        <div className="terminal-card">
          <div className="flex items-center gap-2 text-gray-400 mb-2 text-xs font-bold uppercase">
            <Terminal size={12} />
            Connect to Attacker
          </div>
          <div className="bg-gray-950 rounded p-3 font-mono text-xs text-green-400">
            $ docker exec -it pwnlab-attacker-{shortId} bash
          </div>
        </div>
      )}

      {/* Flag submission */}
      {session.status === 'running' && (
        <div className="terminal-card">
          <div className="flex items-center gap-2 text-gray-400 mb-3 text-xs font-bold uppercase">
            <Flag size={12} />
            Submit Flag
          </div>
          <div className="flex gap-2">
            <input
              className="input-terminal text-sm flex-1"
              placeholder="PWNLAB{...}"
              value={flagInput}
              onChange={(e) => setFlagInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && submitFlag()}
            />
            <input
              className="input-terminal text-sm w-28"
              placeholder="flag-1"
              value={objectiveId}
              onChange={(e) => setObjectiveId(e.target.value)}
            />
            <button className="btn-primary text-sm px-4" onClick={submitFlag}>
              Submit
            </button>
          </div>
          {flagResult && (
            <div className={`mt-2 text-sm flex items-center gap-1.5 ${flagResult.correct ? 'text-green-400' : 'text-red-400'}`}>
              {flagResult.correct ? <CheckCircle size={14} /> : <AlertCircle size={14} />}
              {flagResult.message}
            </div>
          )}
        </div>
      )}

      {session.error_message && (
        <div className="text-red-400 text-sm bg-red-950 p-3 rounded border border-red-800">
          {session.error_message}
        </div>
      )}
    </div>
  )
}
