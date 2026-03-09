import { BrowserRouter, Routes, Route, NavLink, useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Dashboard from './pages/Dashboard.jsx'
import NewAppraisal from './pages/NewAppraisal.jsx'
import Pipeline from './pages/Pipeline.jsx'
import Results from './pages/Results.jsx'
import Landing from './pages/Landing.jsx'

function Navbar({ theme, toggleTheme }) {
  return (
    <nav className="flex items-center justify-between px-8 py-4 border-b sticky top-0 z-50 glass"
         style={{ 
           borderColor: 'var(--border)',
           backgroundColor: 'var(--bg-secondary)',
           backdropFilter: 'blur(12px)'
         }}>
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center"
             style={{
               background: 'linear-gradient(135deg, var(--accent) 0%, var(--accent-dark) 100%)',
               boxShadow: '0 4px 12px rgba(0, 212, 170, 0.4)'
             }}>
          <span className="text-white font-bold text-lg font-syne">IC</span>
        </div>
        <div className="flex flex-col">
          <span className="font-syne font-bold text-lg tracking-tight"
                style={{ color: 'var(--text)' }}>
            Intelli-Credit
          </span>
          <span className="text-[10px] font-mono"
                style={{ color: 'var(--muted-dark)' }}>
            AI Credit Engine v3.0
          </span>
        </div>
      </div>

      <div className="flex items-center gap-6">
        {[
          { to: '/', label: 'Home' },
          { to: '/dashboard', label: 'Dashboard' },
          { to: '/appraisal/new', label: 'New Appraisal' },
        ].map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `text-sm font-medium transition-colors ${
                isActive 
                  ? 'text-[var(--accent)] font-semibold' 
                  : 'hover:text-[var(--accent)]'
              }`
            }
            style={{ color: ({ isActive }) => isActive ? 'var(--accent)' : 'var(--text-secondary)' }}
          >
            {label}
          </NavLink>
        ))}
      </div>

      <div className="flex items-center gap-4">
        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="p-2 rounded-lg transition-all hover:scale-110"
          style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            color: 'var(--text)'
          }}
          title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
        >
          {theme === 'dark' ? (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="5"/>
              <line x1="12" y1="1" x2="12" y2="3"/>
              <line x1="12" y1="21" x2="12" y2="23"/>
              <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
              <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
              <line x1="1" y1="12" x2="3" y2="12"/>
              <line x1="21" y1="12" x2="23" y2="12"/>
              <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
              <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
            </svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
            </svg>
          )}
        </button>
        
        <div className="flex items-center gap-2">
          <span className="status-dot dot-active" />
          <span className="text-xs font-mono" style={{ color: 'var(--muted)' }}>
            Engine Active
          </span>
        </div>
      </div>
    </nav>
  )
}

export default function App() {
  const [theme, setTheme] = useState(() => {
    // Get theme from localStorage or default to 'dark'
    return localStorage.getItem('theme') || 'dark'
  })

  useEffect(() => {
    // Apply theme to document
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  const toggleTheme = () => {
    setTheme(prevTheme => prevTheme === 'dark' ? 'light' : 'dark')
  }

  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col" 
           style={{ backgroundColor: 'var(--bg)' }}>
        <Navbar theme={theme} toggleTheme={toggleTheme} />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/appraisal/new" element={<NewAppraisal />} />
            <Route path="/appraisal/:jobId/pipeline" element={<Pipeline />} />
            <Route path="/appraisal/:jobId/results" element={<Results />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
