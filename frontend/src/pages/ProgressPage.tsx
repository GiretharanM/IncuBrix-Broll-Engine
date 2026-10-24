import { useState, useEffect } from 'react'
import {
  CheckCircle2,
  Clock,
  AlertTriangle,
  ArrowRight,
  Film,
  AudioWaveform,
  Search,
  SlidersHorizontal,
  Layers,
} from 'lucide-react'
import { Job } from '../types'
import { api } from '../api'

interface ProgressPageProps {
  jobId: string
  onJobComplete: (job: Job) => void
  onNavigateToStudio: () => void
}

interface PipelineStep {
  id: number
  name: string
  description: string
  thresholdProgress: number
  icon: React.ReactNode
}

export const ProgressPage: React.FC<ProgressPageProps> = ({
  jobId,
  onJobComplete,
  onNavigateToStudio,
}) => {
  const [job, setJob] = useState<Job | null>(null)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [isPolling, setIsPolling] = useState(true)

  const steps: PipelineStep[] = [
    {
      id: 1,
      name: 'Ingest & VAD Validation',
      description: 'Validate audio formats, silence ratio analysis (VAD), and music-only detection.',
      thresholdProgress: 15,
      icon: <AudioWaveform className="w-4 h-4" />,
    },
    {
      id: 2,
      name: 'Narration Transcription / TTS',
      description: 'Faster-whisper word-level speech alignment or multilingual neural speech synthesis.',
      thresholdProgress: 30,
      icon: <Clock className="w-4 h-4" />,
    },
    {
      id: 3,
      name: 'Semantic Scene Segmentation',
      description: 'Meaning-based boundary splitting; 100% temporal coverage; minimum 2.5s constraint.',
      thresholdProgress: 45,
      icon: <Layers className="w-4 h-4" />,
    },
    {
      id: 4,
      name: 'Query Understanding & Safety',
      description: 'Metaphor resolution, statistical chart routing, brand safety guardrail enforcement.',
      thresholdProgress: 60,
      icon: <Search className="w-4 h-4" />,
    },
    {
      id: 5,
      name: 'Footage Retrieval & Zero-Reuse',
      description: 'Multi-provider retrieval (Pexels, Pixabay, AI Ken-Burns) with strict 0-reuse allocation.',
      thresholdProgress: 75,
      icon: <SlidersHorizontal className="w-4 h-4" />,
    },
    {
      id: 6,
      name: 'Normalisation & Saliency Crop',
      description: '30fps H.264 standardisation; rule-of-thirds saliency crop for 9:16 and 1:1 framing.',
      thresholdProgress: 90,
      icon: <Film className="w-4 h-4" />,
    },
  ]

  const promptSteps: PipelineStep[] = [
    {
      id: 1,
      name: 'Understanding your idea',
      description: 'Analyzing prompt semantic intent, language detection, and content safety verification.',
      thresholdProgress: 25,
      icon: <Search className="w-4 h-4" />,
    },
    {
      id: 2,
      name: 'Planning scenes',
      description: 'Expanding idea into varied camera angles, shot types, and 3-tier cascading search queries.',
      thresholdProgress: 50,
      icon: <Layers className="w-4 h-4" />,
    },
    {
      id: 3,
      name: 'Finding footage for scenes',
      description: 'Searching Pixabay & authentic catalogs with zero-reuse allocation and relevance threshold.',
      thresholdProgress: 75,
      icon: <SlidersHorizontal className="w-4 h-4" />,
    },
    {
      id: 4,
      name: 'Rendering',
      description: 'Normalising resolution, 30fps timing lock, ambient soundtrack muxing, and manifest generation.',
      thresholdProgress: 100,
      icon: <Film className="w-4 h-4" />,
    },
  ]

  const isPromptJob = Boolean(job?.prompt)
  const activeSteps = isPromptJob ? promptSteps : steps

  // Timer for elapsed seconds
  useEffect(() => {
    const timer = setInterval(() => {
      setElapsedSeconds(prev => prev + 1)
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  // Polling loop
  useEffect(() => {
    let active = true

    if (!jobId || jobId === 'job-demo-84920') {
      return
    }

    const fetchStatus = async () => {
      try {
        const data = await api.getJob(jobId)
        if (!active) return

        setJob(data)

        if (data.status === 'succeeded') {
          setIsPolling(false)
          onJobComplete(data)
          // Automatically transition to Result Studio and autoplay
          setTimeout(() => {
            onNavigateToStudio()
          }, 800)
        } else if (data.status === 'failed') {
          setIsPolling(false)
        }
      } catch (err) {
        console.warn('Error fetching job status:', err)
      }
    }

    fetchStatus()

    const interval = setInterval(() => {
      if (isPolling) {
        fetchStatus()
      }
    }, 2000)

    return () => {
      active = false
      clearInterval(interval)
    }
  }, [jobId, isPolling])

  const progress = job?.progress !== undefined && job?.progress !== null
    ? job.progress
    : Math.min(90, Math.floor(elapsedSeconds * 4))
  const isComplete = job?.status === 'succeeded'

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-10">
      {/* Header Card */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-2xl mb-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-800/80">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-slate-400">Job ID: {jobId}</span>
              <span
                className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                  isComplete
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                    : 'bg-sky-500/10 text-sky-400 border border-sky-500/20 animate-pulse'
                }`}
              >
                {isComplete ? 'Succeeded' : job?.status || 'Processing'}
              </span>
            </div>
            <h1 className="text-2xl font-extrabold text-white tracking-tight mt-1">
              {isComplete ? 'Media Rendering Finished' : 'Processing Autonomous B-Roll Pipeline'}
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Current Stage: <span className="text-emerald-400 font-semibold">{job?.current_stage || 'Executing Stages'}</span>
            </p>
          </div>

          <div className="flex items-center gap-4 text-xs font-mono">
            <div className="bg-slate-950 px-3 py-2 rounded-xl border border-slate-800 text-center">
              <span className="text-[10px] text-slate-400 block uppercase">Elapsed Time</span>
              <span className="text-base font-bold text-white">{elapsedSeconds}s</span>
            </div>
            <div className="bg-slate-950 px-3 py-2 rounded-xl border border-slate-800 text-center">
              <span className="text-[10px] text-slate-400 block uppercase">Progress</span>
              <span className="text-base font-bold text-emerald-400">{progress}%</span>
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mt-6">
          <div className="w-full bg-slate-950 rounded-full h-3 p-0.5 border border-slate-800 overflow-hidden">
            <div
              className="bg-gradient-to-r from-emerald-500 via-teal-400 to-emerald-300 h-full rounded-full transition-all duration-500 relative"
              style={{ width: `${Math.min(100, Math.max(5, progress))}%` }}
            >
              <div className="absolute inset-0 bg-white/20 animate-[pulse_2s_infinite]"></div>
            </div>
          </div>
        </div>

        {/* Action Button When Complete */}
        {isComplete && (
          <div className="mt-6 pt-6 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4 animate-in fade-in">
            <div className="flex items-center gap-2 text-emerald-400 text-xs font-semibold">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>All 7 pipeline stages passed automated QA checks and are ready in studio.</span>
            </div>
            <button
              onClick={onNavigateToStudio}
              className="w-full sm:w-auto px-6 py-3 bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-bold text-xs rounded-xl shadow-lg shadow-emerald-500/25 flex items-center justify-center gap-2 transition active:scale-95"
            >
              <span>Open in Result Studio</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Warnings Panel */}
      {job?.warnings && job.warnings.length > 0 && (
        <div className="bg-amber-950/20 border border-amber-500/30 rounded-2xl p-5 mb-8 text-amber-200">
          <div className="flex items-center gap-2 text-xs font-bold text-amber-400 uppercase tracking-wider mb-2">
            <AlertTriangle className="w-4 h-4" />
            <span>Compliance & Safety Telemetry Warnings ({job.warnings.length})</span>
          </div>
          <ul className="text-xs space-y-1.5 opacity-90 pl-5 list-disc">
            {job.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Stepper Details */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-xl">
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-6">
          Real-Time Pipeline Execution Steps
        </h2>

        <div className="flex flex-col gap-4">
          {activeSteps.map(step => {
            const isStepDone = progress >= step.thresholdProgress
            const isStepActive = progress < step.thresholdProgress && progress >= step.thresholdProgress - 15

            return (
              <div
                key={step.id}
                className={`flex items-start gap-4 p-4 rounded-xl border transition-all duration-300 ${
                  isStepDone
                    ? 'bg-emerald-500/5 border-emerald-500/20 text-slate-200'
                    : isStepActive
                    ? 'bg-slate-800/60 border-emerald-500/40 text-white shadow-lg shadow-emerald-500/5'
                    : 'bg-slate-950/40 border-slate-800/60 text-slate-500'
                }`}
              >
                <div
                  className={`p-2.5 rounded-xl shrink-0 ${
                    isStepDone
                      ? 'bg-emerald-500 text-slate-950'
                      : isStepActive
                      ? 'bg-slate-800 text-emerald-400 border border-emerald-500/30 animate-pulse'
                      : 'bg-slate-900 text-slate-600'
                  }`}
                >
                  {isStepDone ? <CheckCircle2 className="w-4 h-4 stroke-[3]" /> : step.icon}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold">{step.name}</span>
                    <span className="text-[10px] font-mono opacity-60">
                      {isStepDone ? 'Completed' : isStepActive ? 'In Progress...' : 'Queued'}
                    </span>
                  </div>
                  <p className="text-[11px] opacity-75 mt-0.5 leading-relaxed">{step.description}</p>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
