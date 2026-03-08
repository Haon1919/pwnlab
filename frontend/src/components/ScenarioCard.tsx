import React from 'react'
import { Link } from 'react-router-dom'
import type { Scenario } from '../api/scenarios'
import { Shield, Tag, Zap } from 'lucide-react'

interface Props {
  scenario: Scenario
  onStart: (id: string, wargame: boolean) => void
  loading?: boolean
}

const difficultyClass: Record<string, string> = {
  beginner: 'badge-difficulty-beginner',
  intermediate: 'badge-difficulty-intermediate',
  advanced: 'badge-difficulty-advanced',
  expert: 'badge-difficulty-expert',
}

export default function ScenarioCard({ scenario, onStart, loading }: Props) {
  return (
    <div className="terminal-card hover:border-gray-700 transition-colors flex flex-col gap-3">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-sm font-bold text-gray-100">{scenario.name}</h3>
          <p className="text-xs text-gray-500 mt-0.5">{scenario.id}</p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className={difficultyClass[scenario.difficulty] || 'badge-difficulty-beginner'}>
            {scenario.difficulty}
          </span>
          {scenario.wargame_enabled && (
            <span className="bg-purple-900 text-purple-300 text-xs px-2 py-0.5 rounded flex items-center gap-1">
              <Shield size={10} /> wargame
            </span>
          )}
        </div>
      </div>

      <div className="flex flex-wrap gap-1">
        {scenario.tags.map((tag) => (
          <span key={tag} className="flex items-center gap-0.5 text-xs text-gray-500 bg-gray-800 px-1.5 py-0.5 rounded">
            <Tag size={9} />{tag}
          </span>
        ))}
        {scenario.ai_generated && (
          <span className="flex items-center gap-0.5 text-xs text-cyan-600 bg-cyan-950 px-1.5 py-0.5 rounded">
            <Zap size={9} /> AI
          </span>
        )}
      </div>

      <div className="flex gap-2 mt-auto pt-2 border-t border-gray-800">
        <button
          className="btn-primary text-xs py-1 px-3 flex-1"
          onClick={() => onStart(scenario.id, false)}
          disabled={loading}
        >
          Start
        </button>
        {scenario.wargame_enabled && (
          <button
            className="text-xs py-1 px-3 bg-purple-800 hover:bg-purple-700 text-white rounded transition-colors"
            onClick={() => onStart(scenario.id, true)}
            disabled={loading}
          >
            War Games
          </button>
        )}
      </div>
    </div>
  )
}
