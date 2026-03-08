import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import Dashboard from './pages/Dashboard'
import ScenarioLibrary from './pages/ScenarioLibrary'
import ActiveSession from './pages/ActiveSession'
import WargameView from './pages/WargameView'
import Login from './pages/Login'
import Layout from './components/Layout'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token)
  return token ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<PrivateRoute><Layout /></PrivateRoute>}>
          <Route index element={<Dashboard />} />
          <Route path="scenarios" element={<ScenarioLibrary />} />
          <Route path="sessions/:sessionId" element={<ActiveSession />} />
          <Route path="wargame/:sessionId" element={<WargameView />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
