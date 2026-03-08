import React, { useState } from 'react'
import { apiClient } from '../api/client'
import { Zap, Loader, ChevronDown } from 'lucide-react'

interface Props {
  onGenerated?: (scenarioId: string) => void
}

export default function AIGenerator({ onGenerated }: Props) {
  const [prompt, setPrompt] = useState('')
  const [difficulty, setDifficulty] = useState<string>('beginner')
  const [tags, setTags] = useState('')
  const [wargame, setWargame] = useState(false)
  const [apiKey, setApiKey] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  const generate = async () => {
    if (!prompt.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const tagList = tags.split(',').map(t => t.trim()).filter(Boolean)
      const { data } = await apiClient.post('/ai/generate-scenario', {
        prompt,
        difficulty,
        tags: tagList,
        wargame,
        ...(apiKey ? { gemini_api_key: apiKey } : {}),
      })
      setResult(data)
      onGenerated?.(data.scenario_id)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Generation failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="terminal-card space-y-4">
      <div className="flex items-center gap-2 text-cyan-400 font-bold">
        <Zap size={16} />
        <span>AI Scenario Generator</span>
        <span className="text-xs text-gray-500">(Gemini)</span>
      </div>

      <div className="space-y-3">
        <div>
          <label className="text-xs text-gray-400 mb-1 block">Describe the scenario</label>
          <textarea
            className="input-terminal resize-none h-20 text-sm"
            placeholder="e.g. PHP web app with SQL injection and weak admin credentials"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Difficulty</label>
            <select
              className="input-terminal text-sm"
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value)}
            >
              {['beginner', 'intermediate', 'advanced', 'expert'].map(d => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Tags (comma-separated)</label>
            <input
              className="input-terminal text-sm"
              placeholder="web, sqli, php"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
            />
          </div>
        </div>

        <div>
          <label className="text-xs text-gray-400 mb-1 block">Gemini API Key (optional if stored)</label>
          <input
            className="input-terminal text-sm"
            type="password"
            placeholder="AIza..."
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
          />
        </div>

        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={wargame}
            onChange={(e) => setWargame(e.target.checked)}
            className="w-4 h-4 rounded accent-purple-500"
          />
          <span className="text-sm text-gray-300">Include war games detection</span>
        </label>

        <button
          className="btn-primary w-full flex items-center justify-center gap-2 text-sm"
          onClick={generate}
          disabled={loading || !prompt.trim()}
        >
          {loading ? <><Loader size={14} className="animate-spin" /> Generating...</> : <><Zap size={14} /> Generate Scenario</>}
        </button>
      </div>

      {error && (
        <div className="text-red-400 text-sm bg-red-950 p-3 rounded border border-red-800">{error}</div>
      )}

      {result && (
        <div className="bg-green-950 border border-green-800 p-3 rounded space-y-2">
          <div className="text-green-400 font-bold text-sm">✓ Generated: {result.name}</div>
          <div className="text-xs text-gray-400">
            ID: <span className="text-cyan-400">{result.scenario_id}</span>
            {' · '} Difficulty: {result.difficulty}
            {' · '} Wargame: {result.wargame_enabled ? 'yes' : 'no'}
          </div>
          {result.yaml_preview && (
            <pre className="text-xs text-gray-500 bg-gray-900 p-2 rounded overflow-auto max-h-32">
              {result.yaml_preview}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}
