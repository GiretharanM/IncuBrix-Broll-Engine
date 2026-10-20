import { useState, useEffect } from 'react'
import {
  History,
  Search,
  ArrowRight,
  Copy,
  Check,
  Film,
  RefreshCw,
} from 'lucide-react'
import { JobListItem, JobStatus } from '../types'
import { api } from '../api'
import { MOCK_HISTORY_JOBS } from '../mockData'

interface HistoryPageProps {
  onOpenJobInStudio: (jobId: string) => void
  onToast: (title: string, desc?: string, type?: 'success' | 'info') => void
}

export const HistoryPage: React.FC<HistoryPageProps> = ({
  onOpenJobInStudio,
  onToast,
}) => {
  const [jobs, setJobs] = useState<JobListItem[]>(MOCK_HISTORY_JOBS)
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<'all' | JobStatus>('all')
  const [copiedId, setCopiedId] = useState<string | null>(null)

  const loadJobs = async (showSpinner = false) => {
    if (showSpinner) setLoading(true)
    try {
      const data = await api.listJobs()
      if (data && data.length > 0) {
        setJobs(data)
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadJobs(false)
  }, [])

  const handleCopyId = (id: string) => {
    navigator.clipboard.writeText(id)
    setCopiedId(id)
    onToast('Job ID Copied', id, 'info')
    setTimeout(() => setCopiedId(null), 2000)
  }

  const filteredJobs = jobs.filter(job => {
    const matchesSearch =
      job.job_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (job.script_preview && job.script_preview.toLowerCase().includes(searchQuery.toLowerCase()))
    const matchesStatus = statusFilter === 'all' || job.status === statusFilter
    return matchesSearch && matchesStatus
  })

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 text-xs font-semibold mb-2 border border-emerald-500/20">
            <History className="w-3.5 h-3.5" />
            <span>Job Log & Provenance Audit</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Render Job History
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Search, filter, and inspect past B-roll video production jobs, cost estimates, and deliverables.
          </p>
        </div>

        <button
          onClick={() => loadJobs(true)}
          className="flex items-center gap-2 px-3.5 py-2 bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-800 rounded-xl text-xs font-medium transition self-start md:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Search & Filter Bar */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 shadow-xl mb-6 flex flex-col sm:flex-row gap-3 items-center justify-between">
        <div className="relative w-full sm:max-w-md">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search by Job ID or script keywords..."
            className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-10 pr-4 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />
        </div>

        {/* Status Filter Chips */}
        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto">
          {(['all', 'succeeded', 'running', 'queued', 'failed'] as const).map(s => {
            const isSelected = statusFilter === s
            return (
              <button
                key={s}
                onClick={() => setStatusFilter(s)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition whitespace-nowrap ${
                  isSelected
                    ? 'bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20'
                    : 'bg-slate-950 border border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                {s}
              </button>
            )
          })}
        </div>
      </div>

      {/* Jobs Table */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl shadow-xl overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-slate-400 text-xs flex flex-col items-center justify-center gap-3">
            <RefreshCw className="w-6 h-6 animate-spin text-emerald-400" />
            <span>Loading job records from database...</span>
          </div>
        ) : filteredJobs.length === 0 ? (
          <div className="p-16 text-center text-slate-400 flex flex-col items-center justify-center gap-3">
            <div className="p-4 bg-slate-950 rounded-2xl border border-slate-800 text-slate-600">
              <Film className="w-8 h-8" />
            </div>
            <p className="text-sm font-semibold text-slate-200">No matching jobs found</p>
            <p className="text-xs text-slate-500 max-w-sm">
              Try adjusting your search query or status filter, or create a new job from the New Job tab.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950 text-slate-400 uppercase font-mono text-[10px] border-b border-slate-800">
                <tr>
                  <th className="py-3.5 px-4">Job ID</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4">Input & Script Preview</th>
                  <th className="py-3.5 px-4">Ratios</th>
                  <th className="py-3.5 px-4">Duration</th>
                  <th className="py-3.5 px-4">Est. Cost</th>
                  <th className="py-3.5 px-4">Created</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans">
                {filteredJobs.map(job => {
                  const statusColors = {
                    succeeded: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
                    running: 'bg-sky-500/10 text-sky-400 border-sky-500/20 animate-pulse',
                    queued: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
                    failed: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
                  }[job.status] || 'bg-slate-800 text-slate-400'

                  return (
                    <tr key={job.job_id} className="hover:bg-slate-800/30 transition">
                      <td className="py-3.5 px-4 font-mono font-semibold text-slate-300 flex items-center gap-2">
                        <span className="line-clamp-1">{job.job_id}</span>
                        <button
                          onClick={() => handleCopyId(job.job_id)}
                          aria-label="Copy job ID"
                          className="text-slate-500 hover:text-slate-300 p-1"
                        >
                          {copiedId === job.job_id ? (
                            <Check className="w-3.5 h-3.5 text-emerald-400" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </td>

                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <span className={`px-2 py-0.5 rounded-full border text-[10px] font-bold uppercase ${statusColors}`}>
                          {job.status}
                        </span>
                      </td>

                      <td className="py-3.5 px-4 max-w-xs">
                        <span className="text-[10px] font-mono text-emerald-400 uppercase font-bold block">
                          {job.input_type}
                        </span>
                        <span className="text-slate-300 line-clamp-1 text-xs mt-0.5">
                          {job.script_preview || 'No script preview'}
                        </span>
                      </td>

                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <div className="flex gap-1">
                          {job.aspect_ratios.map(r => (
                            <span
                              key={r}
                              className="px-1.5 py-0.5 bg-slate-950 border border-slate-800 rounded font-mono text-[10px] text-slate-300"
                            >
                              {r}
                            </span>
                          ))}
                        </div>
                      </td>

                      <td className="py-3.5 px-4 font-mono text-slate-300 whitespace-nowrap">
                        {job.duration_seconds.toFixed(1)}s
                      </td>

                      <td className="py-3.5 px-4 font-mono text-emerald-400 font-bold whitespace-nowrap">
                        ${job.cost_estimate_usd.toFixed(3)}
                      </td>

                      <td className="py-3.5 px-4 font-mono text-slate-400 text-[11px] whitespace-nowrap">
                        {new Date(job.created_at).toLocaleDateString([], {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </td>

                      <td className="py-3.5 px-4 text-right whitespace-nowrap">
                        <button
                          onClick={() => onOpenJobInStudio(job.job_id)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-950 hover:bg-emerald-500 hover:text-slate-950 border border-slate-800 hover:border-emerald-500 text-slate-300 text-xs font-semibold rounded-lg transition"
                        >
                          <span>Studio</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
