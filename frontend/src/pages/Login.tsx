import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { apiClient } from '../api/client'
import { Shield, Terminal } from 'lucide-react'

export default function Login() {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const { setToken, setUser } = useAuthStore()
  const navigate = useNavigate()

  const handleLogin = async () => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams()
      params.append('username', username)
      params.append('password', password)
      const { data } = await apiClient.post('/auth/token', params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
      setToken(data.access_token)

      const { data: me } = await apiClient.get('/auth/me', {
        headers: { Authorization: `Bearer ${data.access_token}` }
      })
      setUser(me)
      navigate('/')
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async () => {
    setLoading(true)
    setError(null)
    try {
      await apiClient.post('/auth/register', { username, email, password })
      setMode('login')
      setError(null)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-2 text-green-400 text-2xl font-bold mb-2">
            <Shield size={28} />
            PwnLab
          </div>
          <p className="text-gray-500 text-sm">Docker Security Lab Platform</p>
        </div>

        <div className="terminal-card">
          <div className="flex gap-1 mb-4 bg-gray-800 p-1 rounded">
            {(['login', 'register'] as const).map((m) => (
              <button
                key={m}
                className={`flex-1 py-1.5 text-sm rounded transition-colors ${
                  mode === m ? 'bg-gray-900 text-green-400' : 'text-gray-500 hover:text-gray-300'
                }`}
                onClick={() => { setMode(m); setError(null) }}
              >
                {m}
              </button>
            ))}
          </div>

          <div className="space-y-3">
            <div>
              <label className="text-xs text-gray-400 block mb-1">Username</label>
              <input
                className="input-terminal text-sm"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (mode === 'login' ? handleLogin() : handleRegister())}
                autoFocus
              />
            </div>
            {mode === 'register' && (
              <div>
                <label className="text-xs text-gray-400 block mb-1">Email</label>
                <input
                  className="input-terminal text-sm"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
            )}
            <div>
              <label className="text-xs text-gray-400 block mb-1">Password</label>
              <input
                className="input-terminal text-sm"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (mode === 'login' ? handleLogin() : handleRegister())}
              />
            </div>

            {error && <div className="text-red-400 text-xs bg-red-950 p-2 rounded">{error}</div>}

            <button
              className="btn-primary w-full text-sm"
              onClick={mode === 'login' ? handleLogin : handleRegister}
              disabled={loading}
            >
              {loading ? 'Please wait...' : mode === 'login' ? 'Login' : 'Register'}
            </button>
          </div>

          <p className="text-xs text-gray-600 text-center mt-4">
            <Terminal size={10} className="inline mr-1" />
            CLI: <code className="text-gray-500">pwnlab auth login</code>
          </p>
        </div>
      </div>
    </div>
  )
}
