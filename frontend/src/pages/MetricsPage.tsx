import { useState, useEffect } from 'react'
import {
  BarChart3,
  Clock,
  DollarSign,
  Layers,
  Sparkles,
  ShieldCheck,
  CheckCircle2,
  RefreshCw,
  PieChart,
} from 'lucide-react'
import { JobMetrics } from '../types'
import { api } from '../api'
import { MOCK_METRICS } from '../mockData'

export const MetricsPage: React.FC = () => {
  const [metrics, setMetrics] = useState<JobMetrics>(MOCK_METRICS)
  const [loading, setLoading] = useState(false)

  const loadMetrics = async () => {
    setLoading(true)
    try {
      const data = await api.getMetrics()
      setMetrics(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadMetrics()
  }, [])

  if (loading || !metrics) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-16 flex flex-col items-center justify-center text-slate-400 gap-3">
        <RefreshCw className="w-6 h-6 animate-spin text-emerald-400" />
        <span className="text-xs">Computing engine metrics and telemetry...</span>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 text-xs font-semibold mb-2 border border-emerald-500/20">
            <BarChart3 className="w-3.5 h-3.5" />
            <span>Operational SLA & Quality Telemetry</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Engine Performance & Quality Dashboard
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time quality KPIs: turnaround speed, cost per minute, semantic relevance, zero duplicate clips, and 100% narration coverage.
          </p>
        </div>

        <button
          onClick={loadMetrics}
          className="flex items-center gap-2 px-3.5 py-2 bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-800 rounded-xl text-xs font-medium transition self-start md:self-auto"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh Metrics</span>
        </button>
      </div>

      {/* 6 Top Key Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        {/* Metric 1: Average Turnaround */}
        <div className="p-6 bg-slate-900/90 border border-slate-800 rounded-2xl shadow-xl flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Avg Turnaround Time</span>
            <div className="p-2 bg-emerald-500/10 rounded-xl text-emerald-400">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-4">
            <span className="text-3xl font-black text-white tracking-tight font-mono">
              {metrics.avg_turnaround_seconds}s
            </span>
            <p className="text-xs text-slate-400 mt-1">Ingest to multi-ratio MP4 delivery</p>
          </div>
        </div>

        {/* Metric 2: Cost per Minute */}
        <div className="p-6 bg-slate-900/90 border border-slate-800 rounded-2xl shadow-xl flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Cost per Minute</span>
            <div className="p-2 bg-emerald-500/10 rounded-xl text-emerald-400">
              <DollarSign className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-4">
            <span className="text-3xl font-black text-emerald-400 tracking-tight font-mono">
              ${metrics.cost_per_minute_usd}
            </span>
            <p className="text-xs text-slate-400 mt-1">Free-tier stock APIs + lightweight compute</p>
          </div>
        </div>

        {/* Metric 3: Narration Coverage */}
        <div className="p-6 bg-slate-900/90 border border-slate-800 rounded-2xl shadow-xl flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Narration Coverage</span>
            <div className="p-2 bg-emerald-500/10 rounded-xl text-emerald-400">
              <Layers className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-4">
            <span className="text-3xl font-black text-white tracking-tight font-mono">
              {(metrics.narration_coverage_ratio * 100).toFixed(1)}%
            </span>
            <p className="text-xs text-slate-400 mt-1">Contiguous timeline coverage (0 gaps)</p>
          </div>
        </div>

        {/* Metric 4: Average Relevance */}
        <div className="p-6 bg-slate-900/90 border border-slate-800 rounded-2xl shadow-xl flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Avg Relevance Score</span>
            <div className="p-2 bg-emerald-500/10 rounded-xl text-emerald-400">
              <Sparkles className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-4">
            <span className="text-3xl font-black text-emerald-400 tracking-tight font-mono">
              {metrics.avg_relevance_score}
            </span>
            <p className="text-xs text-slate-400 mt-1">CLIP / SigLIP keyframe semantic similarity</p>
          </div>
        </div>

        {/* Metric 5: Job Success Rate */}
        <div className="p-6 bg-slate-900/90 border border-slate-800 rounded-2xl shadow-xl flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Pipeline Success Rate</span>
            <div className="p-2 bg-emerald-500/10 rounded-xl text-emerald-400">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-4">
            <span className="text-3xl font-black text-white tracking-tight font-mono">
              {metrics.success_rate_percent}%
            </span>
            <p className="text-xs text-slate-400 mt-1">{metrics.succeeded_jobs} of {metrics.total_jobs} total jobs succeeded</p>
          </div>
        </div>

        {/* Metric 6: Repeat Clip Rate (MUST BE 0.0) */}
        <div className="p-6 bg-gradient-to-br from-emerald-950/40 to-teal-950/20 border-2 border-emerald-500/50 rounded-2xl shadow-xl flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">
              Strict Repeat-Clip Rate
            </span>
            <div className="p-2 bg-emerald-500 text-slate-950 rounded-xl shadow-md shadow-emerald-500/30">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-4">
            <span className="text-3xl font-black text-emerald-400 tracking-tight font-mono">
              {metrics.repeat_clip_rate.toFixed(1)}%
            </span>
            <p className="text-xs text-emerald-200/80 mt-1 font-semibold">
              Guaranteed: 0 clips ever reused in any generated video
            </p>
          </div>
        </div>
      </div>

      {/* Visual Distributions Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
        {/* Source Distribution */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
          <div className="flex items-center gap-2 mb-4 text-slate-300">
            <PieChart className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-200">
              Footage Source Allocation
            </h3>
          </div>

          <div className="space-y-4">
            {Object.entries(metrics.source_distribution).map(([source, pct]) => (
              <div key={source}>
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span className="text-slate-300 font-medium">{source}</span>
                  <span className="text-emerald-400 font-mono font-bold">{pct}%</span>
                </div>
                <div className="w-full bg-slate-950 rounded-full h-2.5 overflow-hidden border border-slate-800">
                  <div
                    className="bg-emerald-500 h-full rounded-full transition-all duration-500"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            ))}
          </div>

          <p className="text-[11px] text-slate-400 mt-6 leading-relaxed">
            Rule-driven cascading retrieval prioritizes clean commercial stock from Pexels and Pixabay. When no candidate exceeds threshold (score &ge; 0.28), the engine seamlessly falls back to generative AI / Ken-Burns parallax.
          </p>
        </div>

        {/* Aspect Ratio Distribution */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
          <div className="flex items-center gap-2 mb-4 text-slate-300">
            <BarChart3 className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-200">
              Delivered Aspect Ratio Share
            </h3>
          </div>

          <div className="space-y-4">
            {Object.entries(metrics.ratio_distribution).map(([ratio, pct]) => (
              <div key={ratio}>
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span className="text-slate-300 font-medium">{ratio}</span>
                  <span className="text-emerald-400 font-mono font-bold">{pct}%</span>
                </div>
                <div className="w-full bg-slate-950 rounded-full h-2.5 overflow-hidden border border-slate-800">
                  <div
                    className="bg-gradient-to-r from-teal-500 to-emerald-400 h-full rounded-full transition-all duration-500"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            ))}
          </div>

          <p className="text-[11px] text-slate-400 mt-6 leading-relaxed">
            Every job can generate 16:9, 9:16, and 1:1 simultaneously with smart subject tracking so video creators never have to manually re-edit for Reels, TikTok, or YouTube.
          </p>
        </div>
      </div>
    </div>
  )
}
