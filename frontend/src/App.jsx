import { BrowserRouter, Routes, Route, NavLink, useNavigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard.jsx'
import NewAppraisal from './pages/NewAppraisal.jsx'
import Pipeline from './pages/Pipeline.jsx'
import Results from './pages/Results.jsx'
import Landing from './pages/Landing.jsx'

function Navbar() {
  return (
    <nav className="flex items-center justify-between px-8 py-4 border-b border-[#1a2530] bg-[#0a0f12] sticky top-0 z-50">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-[#00d4aa] flex items-center justify-center">
          <span className="text-[#020608] font-bold text-sm font-syne">IC</span>
        </div>
        <span className="font-syne font-bold text-lg text-[#e8f0f5] tracking-tight">
          Intelli-Credit
        </span>
        <span className="text-[10px] text-[#4a6070] bg-[#111820] border border-[#1a2530] px-2 py-0.5 rounded-full font-mono ml-1">
          AI ENGINE
        </span>
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
              `text-sm font-medium transition-colors ${isActive ? 'text-[#00d4aa]' : 'text-[#4a6070] hover:text-[#e8f0f5]'
              }`
            }
          >
            {label}
          </NavLink>
        ))}
      </div>

      <div className="flex items-center gap-2">
        <span className="status-dot dot-active" />
        <span className="text-xs text-[#4a6070] font-mono">Engine Active</span>
      </div>
    </nav>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-[#020608] flex flex-col">
        <Navbar />
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
