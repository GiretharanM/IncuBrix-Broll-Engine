import { useState, useEffect } from 'react'
import { ThemeProvider } from './context/ThemeContext'
import { Navbar, PageTab } from './components/Navbar'
import { ToastContainer, ToastMessage } from './components/Toast'
import { CurlModal } from './components/CurlModal'
import { NewJobPage } from './pages/NewJobPage'
import { ProgressPage } from './pages/ProgressPage'
import { ResultStudioPage } from './pages/ResultStudioPage'
import { HistoryPage } from './pages/HistoryPage'
import { MetricsPage } from './pages/MetricsPage'
import { Job } from './types'
import { CreateJobPayload, api } from './api'
import { DEFAULT_DEMO_JOB } from './mockData'

export default function App() {
  const [activeTab, setActiveTabState] = useState<PageTab>(() => {
    const hash = (typeof window !== 'undefined' ? window.location.hash.replace('#', '') : '')
    if (hash === 'studio-swap') return 'studio'
    if (['new', 'progress', 'studio', 'history', 'metrics'].includes(hash as PageTab)) {
      return hash as PageTab
    }
    return 'new'
  })

  const setActiveTab = (tab: PageTab) => {
    setActiveTabState(tab)
    if (typeof window !== 'undefined') {
      window.location.hash = tab
    }
  }

  useEffect(() => {
    const onHash = () => {
      const h = window.location.hash.replace('#', '')
      if (h === 'studio-swap') {
        setActiveTabState('studio')
      } else if (['new', 'progress', 'studio', 'history', 'metrics'].includes(h as PageTab)) {
        setActiveTabState(h as PageTab)
      }
    }
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  const [activeJob, setActiveJob] = useState<Job>(DEFAULT_DEMO_JOB)
  const [activeJobId, setActiveJobId] = useState<string>(DEFAULT_DEMO_JOB.job_id)
  const [isSubmittingJob, setIsSubmittingJob] = useState(false)

  // Health and Ready state
  const [healthStatus, setHealthStatus] = useState('healthy')
  const [readyStatus, setReadyStatus] = useState('ready')

  // Toast state
  const [toasts, setToasts] = useState<ToastMessage[]>([])

  // Curl modal state
  const [isCurlModalOpen, setIsCurlModalOpen] = useState(false)
  const [curlPayload, setCurlPayload] = useState<CreateJobPayload>({
    script_text: DEFAULT_DEMO_JOB.script_text,
    voice: 'en-US-Standard',
    aspect_ratios: ['16:9', '9:16', '1:1'],
    style: 'cinematic',
    avoid: ['watermark', 'violence'],
    burn_in_captions: true,
    srt_captions: true,
  })

  // Poll health and ready on mount
  useEffect(() => {
    api.checkHealth().then(res => setHealthStatus(res.status))
    api.checkReady().then(res => setReadyStatus(res.status))
  }, [])

  const addToast = (title: string, description?: string, type: 'success' | 'warning' | 'error' | 'info' = 'success') => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`
    setToasts(prev => [...prev, { id, title, description, type }])
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id))
    }, 4500)
  }

  const dismissToast = (id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }

  // Handle Job Submission
  const handleCreateJob = async (payload: CreateJobPayload) => {
    setIsSubmittingJob(true)
    try {
      const res = await api.createJob(payload)
      setActiveJobId(res.job_id)

      addToast(
        'B-Roll Job Queued',
        `Job ${res.job_id} accepted. Beginning autonomous 10-stage processing.`,
        'success'
      )

      // Navigate to live progress page
      setActiveTab('progress')
    } catch (e: any) {
      addToast('Job Creation Error', e.message || 'Failed to submit job', 'error')
    } finally {
      setIsSubmittingJob(false)
    }
  }

  // Handle Job Complete in Progress page
  const handleJobComplete = (completedJob: Job) => {
    setActiveJob(completedJob)
    addToast(
      'Media Rendering Finished!',
      'All aspect ratios, smart crops, and captions have been rendered.',
      'success'
    )
  }

  // Open job in Studio from History
  const handleOpenJobInStudio = async (jobId: string) => {
    setActiveJobId(jobId)
    const jobData = await api.getJob(jobId)
    setActiveJob(jobData)
    setActiveTab('studio')
    addToast('Loaded Job in Studio', `Viewing ${jobId}`, 'info')
  }

  // Handle clip swap in Studio
  const handleClipSwapped = (updatedJob: Job, message: string) => {
    setActiveJob(updatedJob)
    addToast('Clip Re-rendered', message, 'success')
  }

  return (
    <ThemeProvider>
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-emerald-500 selection:text-slate-950 transition-colors">
        {/* Navigation Bar */}
        <Navbar
          activeTab={activeTab}
          onSelectTab={setActiveTab}
          onOpenCurl={() => setIsCurlModalOpen(true)}
          healthStatus={healthStatus}
          readyStatus={readyStatus}
        />

        {/* Main Content Area */}
        <main className="flex-1 pb-16">
          {activeTab === 'new' && (
            <NewJobPage
              onSubmit={handleCreateJob}
              onOpenCurlWithPayload={payload => {
                setCurlPayload(payload)
                setIsCurlModalOpen(true)
              }}
              isLoading={isSubmittingJob}
            />
          )}

          {activeTab === 'progress' && (
            <ProgressPage
              jobId={activeJobId}
              onJobComplete={handleJobComplete}
              onNavigateToStudio={() => setActiveTab('studio')}
            />
          )}

          {activeTab === 'studio' && (
            <ResultStudioPage
              job={activeJob}
              onClipSwapped={handleClipSwapped}
            />
          )}

          {activeTab === 'history' && (
            <HistoryPage
              onOpenJobInStudio={handleOpenJobInStudio}
              onToast={addToast}
            />
          )}

          {activeTab === 'metrics' && <MetricsPage />}
        </main>

        {/* Global Footer */}
        <footer className="border-t border-slate-900 bg-slate-950 px-6 py-6 text-center text-xs text-slate-500">
          <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-slate-400">
              <span className="font-semibold text-slate-300">IncuBrix B-Roll Engine v1.0.0</span>
              <span>•</span>
              <span>H.264 30fps Frame-Accurate Pipeline</span>
            </div>
            <div className="text-slate-500 text-[11px]">
              OpenAPI 3.1 • Strict Zero-Reuse Policy • Commercial Clean Licences
            </div>
          </div>
        </footer>

        {/* cURL Modal */}
        <CurlModal
          isOpen={isCurlModalOpen}
          onClose={() => setIsCurlModalOpen(false)}
          payload={curlPayload}
          onCopied={() => addToast('Copied', 'cURL command copied to clipboard', 'info')}
        />

        {/* Toast Container */}
        <ToastContainer toasts={toasts} onDismiss={dismissToast} />
      </div>
    </ThemeProvider>
  )
}
