import React, { useEffect, useState, useCallback } from 'react'
import { scenariosApi, type Scenario } from '../api/scenarios'
import { sessionsApi } from '../api/sessions'
import ScenarioCard from '../components/ScenarioCard'
import AIGenerator from '../components/AIGenerator'
import { Search, RefreshCw, Zap } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export default function ScenarioLibrary() {
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [loading, setLoading] = useState(true)
  const [startingId, setStartingId] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [diffFilter, setDiffFilter] = useState('')
  const [showAI, setShowAI] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await scenariosApi.list(diffFilter ? { difficulty: diffFilter } : undefined)
      setScenarios(data)
      setError(null)
    } catch (e: any) {
      setError('Failed to load scenarios')
    } finally {
      setLoading(false)
    }
  }, [diffFilter])

  useEffect(() => { load() }, [load])

  const handleStart = async (scenarioId: string, wargame: boolean) => {
    setStartingId(scenarioId)
    try {
      const session = await sessionsApi.start({ scenario_id: scenarioId, wargame })
      navigate(wargame ? `/wargame/${session.id}` : `/sessions/${session.id}`)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to start session')
      setStartingId(null)
    }
  }

  const filtered = scenarios.filter(s =>
    !search || s.name.toLowerCase().includes(search.toLowerCase()) ||
    s.id.includes(search) || s.tags.some(t => t.includes(search))
  )

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Scenario Library</h1>
        <div className="flex items-center gap-2">
          <button
            className={`flex items-center gap-1.5 text-xs py-1.5 px-3 rounded transition-colors ${
              showAI ? 'bg-cyan-800 text-cyan-200' : 'btn-secondary'
            }`}
            onClick={() => setShowAI(!showAI)}
          >
            <Zap size={12} /> AI Generator
          </button>
          <button className="btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5" onClick={load}>
            <RefreshCw size={12} /> Refresh
          </button>
        </div>
      </div>

      {showAI && (
        <AIGenerator onGenerated={(id) => { setShowAI(false); load() }} />
      )}

      {/* Filters */}
      <div className="flex gap-3">
        <div className="flex-1 relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            className="input-terminal text-sm pl-9"
            placeholder="Search scenarios..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select
          className="input-terminal text-sm w-40"
          value={diffFilter}
          onChange={(e) => setDiffFilter(e.target.value)}
        >
          <option value="">All difficulties</option>
          {['beginner', 'intermediate', 'advanced', 'expert'].map(d => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
      </div>

      {error && <div className="text-red-400 text-sm">{error}</div>}

      {loading ? (
        <div className="text-gray-500 text-sm animate-pulse">Loading scenarios...</div>
      ) : filtered.length === 0 ? (
        <div className="text-gray-500 text-sm">No scenarios found</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((scenario) => (
            <ScenarioCard
              key={scenario.id}
              scenario={scenario}
              onStart={handleStart}
              loading={startingId === scenario.id}
            />
          ))}
        </div>
      )}
    </div>
  )
}
