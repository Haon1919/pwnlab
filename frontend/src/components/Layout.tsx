import React from 'react'
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { Terminal, BookOpen, LogOut, Shield, Cpu } from 'lucide-react'

export default function Layout() {
  const { user, logout } = useAuthStore()
  const location = useLocation()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const navLinks = [
    { to: '/', label: 'Dashboard', icon: <Terminal size={16} /> },
    { to: '/scenarios', label: 'Scenarios', icon: <BookOpen size={16} /> },
  ]

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-gray-900 border-b border-gray-800 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-green-400 font-bold text-xl flex items-center gap-2">
            <Shield size={20} className="text-green-400" />
            BlaqLiq
          </span>
          <span className="text-gray-600 text-xs">v1.0</span>
        </div>
        <nav className="flex items-center gap-1">
          {navLinks.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-sm transition-colors ${
                location.pathname === link.to
                  ? 'bg-gray-800 text-green-400'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
              }`}
            >
              {link.icon}
              {link.label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-3">
          {user && (
            <span className="text-gray-400 text-sm">
              <span className="text-gray-500">@</span>{user.username}
              <span className="ml-2 text-xs bg-gray-800 px-1.5 py-0.5 rounded text-cyan-400">{user.plan}</span>
            </span>
          )}
          <button
            onClick={handleLogout}
            className="text-gray-500 hover:text-red-400 transition-colors"
            title="Logout"
          >
            <LogOut size={16} />
          </button>
        </div>
      </header>
      {/* Main */}
      <main className="flex-1 p-6">
        <Outlet />
      </main>
    </div>
  )
}
