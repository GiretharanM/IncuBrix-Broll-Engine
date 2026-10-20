import { useState, useEffect } from 'react'
import { Sparkles, Video, CheckCircle, Clock } from 'lucide-react'

export default function App() {
  const [healthStatus, setHealthStatus] = useState<string>('Checking...')
  const [readyStatus, setReadyStatus] = useState<string>('Checking...')

  useEffect(() => {
    fetch('/health')
      .then(res => res.json())
      .then(data => setHealthStatus(data.status || 'OK'))
      .catch(() => setHealthStatus('Connecting...'))

    fetch('/ready')
      .then(res => res.json())
      .then(data => setReadyStatus(data.status || 'Ready'))
      .catch(() => setReadyStatus('Waiting for services...'))
  }, [])

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-emerald-400">
            <Video className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight">IncuBrix B-roll Engine</h1>
            <p className="text-xs text-slate-400">Automated, License-Clean B-Roll Video Studio</p>
          </div>
        </div>
        <div className="flex items-center space-x-3 text-xs">
          <span className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-slate-800 text-slate-300">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>API: {healthStatus}</span>
          </span>
          <span className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-slate-800 text-slate-300">
            <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
            <span>Ready: {readyStatus}</span>
          </span>
        </div>
      </header>

      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-10">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 mb-8 shadow-xl">
          <div className="max-w-2xl">
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 text-xs font-medium mb-4">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Phase 1 Initialized</span>
            </div>
            <h2 className="text-3xl font-extrabold tracking-tight mb-3">
              Transform Voiceover & Script into Precision B-Roll Videos
            </h2>
            <p className="text-slate-400 leading-relaxed mb-6">
              Full-stack media pipeline with word-level speech alignment, semantic scene segmentation, 
              LLM metaphor disambiguation, CLIP ranking, and 0-repeat license-clean footage generation.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8 pt-8 border-t border-slate-800/80">
            <div className="p-4 rounded-lg bg-slate-950 border border-slate-800/80">
              <div className="text-emerald-400 font-semibold mb-1 flex items-center gap-2">
                <Clock className="w-4 h-4" /> 10-Stage Pipeline
              </div>
              <p className="text-xs text-slate-400">Ingest, VAD, Whisper/TTS, Segment, LLM, Retrieval, CLIP, Normalize, Multi-render, Manifest.</p>
            </div>
            <div className="p-4 rounded-lg bg-slate-950 border border-slate-800/80">
              <div className="text-emerald-400 font-semibold mb-1 flex items-center gap-2">
                <CheckCircle className="w-4 h-4" /> Zero-Key Mock Support
              </div>
              <p className="text-xs text-slate-400">100% offline development & tests with mock STT, TTS, LLM, Footage and Vision adapters.</p>
            </div>
            <div className="p-4 rounded-lg bg-slate-950 border border-slate-800/80">
              <div className="text-emerald-400 font-semibold mb-1 flex items-center gap-2">
                <Video className="w-4 h-4" /> Multi-Ratio Output
              </div>
              <p className="text-xs text-slate-400">H.264 1080p-class renders for 16:9, 9:16 (saliency crop), and 1:1 with burned/SRT captions.</p>
            </div>
          </div>
        </div>
      </main>

      <footer className="border-t border-slate-800 px-6 py-4 text-center text-xs text-slate-500">
        IncuBrix B-roll Engine • Phase 1 Core Infrastructure
      </footer>
    </div>
  )
}
