import React from 'react'
import {
  Video,
  PlusCircle,
  Activity,
  Film,
  History,
  BarChart3,
  Sun,
  Moon,
  Terminal,
} from 'lucide-react'
import { useTheme } from '../context/ThemeContext'

export type PageTab = 'new' | 'progress' | 'studio' | 'history' | 'metrics'

interface NavbarProps {
  activeTab: PageTab
  onSelectTab: (tab: PageTab) => void
  onOpenCurl: () => void
  healthStatus?: string
  readyStatus?: string
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  onSelectTab,
  onOpenCurl,
  healthStatus = 'healthy',
  readyStatus = 'ready',
}) => {
  const { theme, toggleTheme } = useTheme()

  const navItems: Array<{ id: PageTab; label: string; icon: React.ReactNode }> = [
    { id: 'new', label: 'New Job', icon: <PlusCircle className="w-4 h-4" /> },
    { id: 'progress', label: 'Live Progress', icon: <Activity className="w-4 h-4" /> },
    { id: 'studio', label: 'Result Studio', icon: <Film className="w-4 h-4" /> },
    { id: 'history', label: 'History', icon: <History className="w-4 h-4" /> },
    { id: 'metrics', label: 'Metrics', icon: <BarChart3 className="w-4 h-4" /> },
  ]

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800/80 bg-slate-950/80 dark:bg-slate-950/85 backdrop-blur-xl transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        {/* Brand */}
        <div
          onClick={() => onSelectTab('new')}
          className="flex items-center gap-3 cursor-pointer group select-none"
          role="button"
          tabIndex={0}
          onKeyDown={e => e.key === 'Enter' && onSelectTab('new')}
          aria-label="Broll Studio Home"
        >
          <div className="p-2 bg-gradient-to-tr from-emerald-600 to-teal-500 rounded-xl text-slate-950 shadow-lg shadow-emerald-500/25 group-hover:scale-105 transition-transform">
            <Video className="w-5 h-5 stroke-[2.5]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-base tracking-tight text-white dark:text-white">
                Broll Studio
              </span>
              <span className="px-1.5 py-0.5 text-[10px] font-bold tracking-wider uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-md">
                AI Engine
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-medium">Commercial Clean • Frame Accurate</p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="hidden md:flex items-center gap-1 bg-slate-900/90 p-1 rounded-xl border border-slate-800">
          {navItems.map(item => {
            const isActive = activeTab === item.id
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 select-none ${
                  isActive
                    ? 'bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
              >
                {item.icon}
                <span>{item.label}</span>
              </button>
            )
          })}
        </nav>

        {/* Status, cURL, Theme */}
        <div className="flex items-center gap-2.5">
          {/* Health Pill */}
          <div
            className="hidden sm:flex items-center gap-2 px-3 py-1 bg-slate-900 border border-slate-800 rounded-full text-xs text-slate-400"
            title={`API Health: ${healthStatus} | Ready: ${readyStatus}`}
          >
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="font-mono text-[11px] text-slate-300">API: {healthStatus}</span>
          </div>

          {/* Copy cURL Action */}
          <button
            onClick={onOpenCurl}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white rounded-lg text-xs font-medium transition"
            title="View executable cURL command"
          >
            <Terminal className="w-3.5 h-3.5 text-emerald-400" />
            <span className="hidden sm:inline">cURL</span>
          </button>

          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            aria-label="Toggle color theme"
            className="p-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-white transition"
          >
            {theme === 'dark' ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-sky-400" />}
          </button>
        </div>
      </div>

      {/* Mobile nav bar */}
      <div className="md:hidden flex items-center justify-around border-t border-slate-800/60 bg-slate-950 px-2 py-2">
        {navItems.map(item => {
          const isActive = activeTab === item.id
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              className={`flex flex-col items-center gap-1 p-1 text-[10px] font-medium transition ${
                isActive ? 'text-emerald-400' : 'text-slate-400'
              }`}
            >
              {item.icon}
              <span>{item.label}</span>
            </button>
          )
        })}
      </div>
    </header>
  )
}
