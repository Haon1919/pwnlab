import React, { useEffect, useState } from 'react'
import { wargamesApi, type WargameState, type DetectionEvent } from '../api/wargames'
import { Shield, AlertTriangle, Skull, CheckCircle } from 'lucide-react'

interface Props {
  sessionId: string
  autoRefresh?: boolean
}

const LEVEL_CONFIG = {
  clean: { color: 'text-green-400', bg: 'bg-green-900/20 border-green-800', icon: <CheckCircle size={18} />, label: 'CLEAN' },
  warning: { color: 'text-yellow-400', bg: 'bg-yellow-900/20 border-yellow-800', icon: <AlertTriangle size={18} />, label: 'WARNING' },
  detected: { color: 'text-orange-400', bg: 'bg-orange-900/20 border-orange-800', icon: <Shield size={18} />, label: 'DETECTED' },
  busted: { color: 'text-red-400', bg: 'bg-red-900/20 border-red-800', icon: <Skull size={18} />, label: 'BUSTED' },
}

export default function WargameStatus({ sessionId, autoRefresh = true }: Props) {
  const [state, setState] = useState<WargameState | null>(null)
  const [events, setEvents] = useState<DetectionEvent[]>([])
  const [error, setError] = useState<string | null>(null)

  const fetchData = async () => {
    try {
      const [wgState, wgEvents] = await Promise.all([
        wargamesApi.getState(sessionId),
        wargamesApi.getEvents(sessionId, 10),
      ])
      setState(wgState)
      setEvents(wgEvents)
      setError(null)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to load wargame state')
    }
  }

  useEffect(() => {
    fetchData()
    if (autoRefresh) {
      const interval = setInterval(fetchData, 5000)
      return () => clearInterval(interval)
    }
  }, [sessionId])

  if (error) return <div className="text-red-400 text-sm">{error}</div>
  if (!state) return <div className="text-gray-500 text-sm animate-pulse">Loading detection state...</div>

  const levelCfg = LEVEL_CONFIG[state.detection_level] || LEVEL_CONFIG.clean
  const scorePercent = Math.min(state.detection_score, 100)

  return (
    <div className="space-y-4">
      {/* Detection meter */}
      <div className={`terminal-card border ${levelCfg.bg}`}>
        <div className={`flex items-center gap-2 ${levelCfg.color} font-bold mb-3`}>
          {levelCfg.icon}
          <span>Detection Level: {levelCfg.label}</span>
          {!state.is_active && <span className="text-gray-500 text-xs ml-auto">(inactive)</span>}
        </div>

        <div className="mb-2">
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>Detection Score</span>
            <span>{state.detection_score} / 100</span>
          </div>
          <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-500 rounded-full ${
                state.detection_level === 'clean' ? 'bg-green-500' :
                state.detection_level === 'warning' ? 'bg-yellow-500' :
                state.detection_level === 'detected' ? 'bg-orange-500' :
                'bg-red-500'
              }`}
              style={{ width: `${scorePercent}%` }}
            />
          </div>
        </div>

        <div className="flex gap-3 text-xs">
          <span className="text-green-600">CLEAN &lt;10</span>
          <span className="text-yellow-600">WARNING ≥10</span>
          <span className="text-orange-600">DETECTED ≥40</span>
          <span className="text-red-600">BUSTED ≥100</span>
        </div>

        {state.busted_at && (
          <div className="mt-2 text-red-400 text-xs">
            Busted at: {new Date(state.busted_at).toLocaleTimeString()}
          </div>
        )}
      </div>

      {/* Detection events */}
      {events.length > 0 && (
        <div className="terminal-card">
          <h4 className="text-xs text-gray-400 font-bold mb-2 uppercase tracking-wider">Recent Events</h4>
          <div className="space-y-1">
            {events.map((evt) => (
              <div key={evt.id} className="flex items-center gap-2 text-xs py-1 border-b border-gray-800 last:border-0">
                <span className={`font-mono ${
                  evt.severity === 'warning' ? 'text-yellow-400' :
                  evt.severity === 'detected' ? 'text-orange-400' :
                  'text-red-400'
                }`}>[{evt.severity}]</span>
                <span className="text-gray-400">{evt.event_type}</span>
                {evt.source_ip && <span className="text-gray-500">{evt.source_ip}</span>}
                <span className="ml-auto text-green-600">+{evt.score_delta}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
