import { useState } from 'react'
import {
  UploadCloud,
  FileText,
  ListTree,
  Mic,
  Volume2,
  Sparkles,
  ShieldAlert,
  Subtitles,
  ArrowRight,
  RefreshCw,
  Check,
  X,
  FileCheck,
} from 'lucide-react'
import { AspectRatio, HardCaseSample } from '../types'
import { CreateJobPayload } from '../api'
import { HARD_CASE_SAMPLES } from '../mockData'

interface NewJobPageProps {
  onSubmit: (payload: CreateJobPayload) => Promise<void>
  onOpenCurlWithPayload: (payload: CreateJobPayload) => void
  isLoading: boolean
}

type InputMode = 'script' | 'audio' | 'scenes'

export const NewJobPage: React.FC<NewJobPageProps> = ({
  onSubmit,
  onOpenCurlWithPayload,
  isLoading,
}) => {
  const [inputMode, setInputMode] = useState<InputMode>('script')
  const [scriptText, setScriptText] = useState(
    'Trust is earned slowly, brick by brick, but lost in an instant. True growth begins when teams align on shared integrity. Together, technology and human creativity unlock the future.'
  )
  const [audioFile, setAudioFile] = useState<File | null>(null)
  const [audioUrl, setAudioUrl] = useState('')
  const [sceneJson, setSceneJson] = useState(
    JSON.stringify(
      [
        { text: 'Trust is earned slowly, brick by brick.', visual_hint: 'handshake in boardroom' },
        { text: 'True growth begins when teams align on integrity.', visual_hint: 'engineering team coding' },
        { text: 'Together, technology unlocks the future.', visual_hint: 'digital financial charts' },
      ],
      null,
      2
    )
  )
  const [jsonError, setJsonError] = useState<string | null>(null)

  // Settings
  const [voice, setVoice] = useState('en-US-Standard')
  const [isPlayingVoice, setIsPlayingVoice] = useState(false)
  const [aspectRatios, setAspectRatios] = useState<AspectRatio[]>(['16:9', '9:16', '1:1'])
  const [stylePreset, setStylePreset] = useState('cinematic')
  const [customStyle, setCustomStyle] = useState('')
  const [avoidTags, setAvoidTags] = useState<string[]>(['watermark', 'violence', 'logos'])
  const [newTagInput, setNewTagInput] = useState('')
  const [burnInCaptions, setBurnInCaptions] = useState(true)
  const [srtCaptions, setSrtCaptions] = useState(true)
  const [idempotencyKey] = useState(() => `key-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 6)}`)

  // Toggle aspect ratios
  const toggleRatio = (ratio: AspectRatio) => {
    if (aspectRatios.includes(ratio)) {
      if (aspectRatios.length === 1) return // Keep at least one
      setAspectRatios(aspectRatios.filter(r => r !== ratio))
    } else {
      setAspectRatios([...aspectRatios, ratio])
    }
  }

  // Add Avoid tag
  const addAvoidTag = () => {
    const trimmed = newTagInput.trim().toLowerCase()
    if (trimmed && !avoidTags.includes(trimmed)) {
      setAvoidTags([...avoidTags, trimmed])
      setNewTagInput('')
    }
  }

  const removeAvoidTag = (tagToRemove: string) => {
    setAvoidTags(avoidTags.filter(t => t !== tagToRemove))
  }

  // Load sample hard-case preset
  const loadHardCase = (sample: HardCaseSample) => {
    setInputMode('script')
    setScriptText(sample.script)
    setVoice(sample.voice)
    setStylePreset(sample.style)
    setAvoidTags(sample.avoid)
    setCustomStyle(sample.visual_hint)
  }

  // Play synthetic voice preview
  const handlePlayVoicePreview = () => {
    setIsPlayingVoice(true)
    const utterance = new SpeechSynthesisUtterance('IncuBrix automated voice synthesis preview.')
    utterance.rate = 1.0
    utterance.onend = () => setIsPlayingVoice(false)
    utterance.onerror = () => setIsPlayingVoice(false)
    window.speechSynthesis?.speak(utterance)
    setTimeout(() => setIsPlayingVoice(false), 2000)
  }

  // Build current payload
  const buildPayload = (): CreateJobPayload => {
    let scenesPayload: Array<{ text: string; visual_hint?: string }> | undefined
    if (inputMode === 'scenes') {
      try {
        scenesPayload = JSON.parse(sceneJson)
      } catch {
        // fallback
      }
    }

    return {
      script_text: inputMode === 'script' ? scriptText : undefined,
      audio_url: inputMode === 'audio' ? (audioUrl || 'sample://clean_voice.wav') : undefined,
      scenes: scenesPayload,
      voice,
      aspect_ratios: aspectRatios,
      style: customStyle ? `${stylePreset}, ${customStyle}` : stylePreset,
      avoid: avoidTags,
      burn_in_captions: burnInCaptions,
      srt_captions: srtCaptions,
      idempotency_key: idempotencyKey,
    }
  }

  // Validation
  let isValid = true
  let validationMessage = ''

  if (inputMode === 'script' && scriptText.trim().length === 0) {
    isValid = false
    validationMessage = 'Script text cannot be empty'
  } else if (inputMode === 'audio' && !audioFile && !audioUrl) {
    isValid = false
    validationMessage = 'Please upload or provide an audio voiceover URL'
  } else if (inputMode === 'scenes') {
    try {
      const parsed = JSON.parse(sceneJson)
      if (!Array.isArray(parsed) || parsed.length === 0) {
        isValid = false
        validationMessage = 'Scene list must be a non-empty array'
      }
    } catch (e: any) {
      isValid = false
      validationMessage = `Invalid JSON syntax: ${e.message}`
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!isValid || isLoading) return
    await onSubmit(buildPayload())
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 text-xs font-semibold mb-2 border border-emerald-500/20">
            <Sparkles className="w-3.5 h-3.5" />
            <span>10-Stage Autonomous Video Pipeline</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Generate License-Clean B-Roll Video
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Provide a voiceover audio, script, or scene list. We handle transcription, disambiguation, footage retrieval, 9:16 smart cropping, and multi-ratio rendering.
          </p>
        </div>

        {/* Sample Presets Dropdown */}
        <div className="flex items-center gap-2">
          <div className="dropdown relative">
            <button
              type="button"
              className="flex items-center gap-2 px-3.5 py-2 bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-800 rounded-xl text-xs font-medium transition"
              onClick={() => {
                const el = document.getElementById('hard-case-menu')
                el?.classList.toggle('hidden')
              }}
            >
              <FileCheck className="w-4 h-4 text-emerald-400" />
              <span>Load Hard Case Sample</span>
            </button>
            <div
              id="hard-case-menu"
              className="hidden absolute right-0 mt-2 w-72 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl p-2 z-20"
            >
              <div className="text-[11px] font-semibold text-slate-400 px-2 py-1 uppercase tracking-wider">
                Select Hard-Case Input
              </div>
              {HARD_CASE_SAMPLES.map(sample => (
                <button
                  key={sample.id}
                  type="button"
                  onClick={() => {
                    loadHardCase(sample)
                    document.getElementById('hard-case-menu')?.classList.add('hidden')
                  }}
                  className="w-full text-left p-2.5 rounded-lg hover:bg-slate-800/80 transition flex flex-col gap-0.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-200">{sample.title}</span>
                    <span className="text-[10px] bg-emerald-500/10 text-emerald-400 px-1.5 py-0.5 rounded font-mono">
                      {sample.tag}
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-400 line-clamp-1">{sample.description}</span>
                </button>
              ))}
            </div>
          </div>

          <button
            type="button"
            onClick={() => onOpenCurlWithPayload(buildPayload())}
            className="flex items-center gap-2 px-3.5 py-2 bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-800 rounded-xl text-xs font-medium transition"
          >
            <span>cURL</span>
          </button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Main Left Column: Inputs */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          {/* Input Mode Selector */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
              1. Choose Input Source
            </label>
            <div className="grid grid-cols-3 gap-2 p-1 bg-slate-950 rounded-xl border border-slate-800/80 mb-6">
              <button
                type="button"
                onClick={() => setInputMode('script')}
                className={`flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-semibold transition ${
                  inputMode === 'script'
                    ? 'bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`}
              >
                <FileText className="w-4 h-4" />
                <span>Script Text</span>
              </button>
              <button
                type="button"
                onClick={() => setInputMode('audio')}
                className={`flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-semibold transition ${
                  inputMode === 'audio'
                    ? 'bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`}
              >
                <UploadCloud className="w-4 h-4" />
                <span>Voiceover Audio</span>
              </button>
              <button
                type="button"
                onClick={() => setInputMode('scenes')}
                className={`flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-semibold transition ${
                  inputMode === 'scenes'
                    ? 'bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`}
              >
                <ListTree className="w-4 h-4" />
                <span>Scene List JSON</span>
              </button>
            </div>

            {/* Mode 1: Script Text */}
            {inputMode === 'script' && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label htmlFor="script-textarea" className="text-xs text-slate-300 font-medium">
                    Paste Script for Multilingual TTS & Auto-Segmentation:
                  </label>
                  <span className="text-[11px] text-slate-400 font-mono">
                    {scriptText.split(/\s+/).filter(Boolean).length} words • ~
                    {Math.max(2.5, scriptText.split(/\s+/).filter(Boolean).length / 2.5).toFixed(1)}s duration
                  </span>
                </div>
                <textarea
                  id="script-textarea"
                  value={scriptText}
                  onChange={e => setScriptText(e.target.value)}
                  rows={6}
                  placeholder="Paste script sentences here. Our pipeline will synthesize speech and split into semantic scenes..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-4 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-500 transition resize-y font-sans leading-relaxed"
                />
              </div>
            )}

            {/* Mode 2: Audio File Upload */}
            {inputMode === 'audio' && (
              <div className="flex flex-col gap-4">
                <div
                  onDragOver={e => e.preventDefault()}
                  onDrop={e => {
                    e.preventDefault()
                    if (e.dataTransfer.files?.[0]) setAudioFile(e.dataTransfer.files[0])
                  }}
                  className="border-2 border-dashed border-slate-800 hover:border-emerald-500/50 bg-slate-950 rounded-xl p-8 flex flex-col items-center justify-center text-center cursor-pointer transition group"
                  onClick={() => document.getElementById('audio-upload-input')?.click()}
                >
                  <input
                    id="audio-upload-input"
                    type="file"
                    accept=".mp3,.wav,.m4a,audio/*"
                    className="hidden"
                    onChange={e => {
                      if (e.target.files?.[0]) setAudioFile(e.target.files[0])
                    }}
                  />
                  <div className="p-3 bg-slate-900 group-hover:bg-emerald-500/10 rounded-2xl text-emerald-400 mb-3 transition">
                    <Mic className="w-6 h-6" />
                  </div>
                  {audioFile ? (
                    <div>
                      <p className="text-sm font-semibold text-emerald-400">{audioFile.name}</p>
                      <p className="text-xs text-slate-400 mt-1">
                        {(audioFile.size / 1024 / 1024).toFixed(2)} MB • Ready for VAD & Whisper transcription
                      </p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-sm font-semibold text-slate-200">
                        Drag and drop audio file, or <span className="text-emerald-400 underline">browse</span>
                      </p>
                      <p className="text-xs text-slate-400 mt-1">MP3, WAV, M4A up to 10 minutes</p>
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400">Or use public audio URL:</span>
                  <input
                    type="url"
                    value={audioUrl}
                    onChange={e => setAudioUrl(e.target.value)}
                    placeholder="https://example.com/voiceover.mp3"
                    className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                  />
                </div>
              </div>
            )}

            {/* Mode 3: Predefined Scene List JSON */}
            {inputMode === 'scenes' && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label htmlFor="scene-json-textarea" className="text-xs text-slate-300 font-medium">
                    Pre-segmented Scenes JSON (<code className="text-emerald-400">[&#123;text, visual_hint&#125;]</code>):
                  </label>
                  <button
                    type="button"
                    onClick={() => {
                      try {
                        const parsed = JSON.parse(sceneJson)
                        setSceneJson(JSON.stringify(parsed, null, 2))
                        setJsonError(null)
                      } catch (e: any) {
                        setJsonError(e.message)
                      }
                    }}
                    className="text-[11px] text-emerald-400 hover:underline"
                  >
                    Format JSON
                  </button>
                </div>
                <textarea
                  id="scene-json-textarea"
                  value={sceneJson}
                  onChange={e => {
                    setSceneJson(e.target.value)
                    setJsonError(null)
                  }}
                  rows={8}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-4 text-xs text-emerald-400/90 font-mono focus:outline-none focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-500 transition"
                />
                {jsonError && <p className="text-xs text-rose-400 mt-1 font-mono">Error: {jsonError}</p>}
              </div>
            )}
          </div>

          {/* Voice & Aesthetic Style */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col gap-6">
            {/* Voice Picker */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  2. Voice & Language (TTS)
                </label>
                <button
                  type="button"
                  onClick={handlePlayVoicePreview}
                  className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400 hover:text-emerald-300 transition"
                >
                  <Volume2 className={`w-4 h-4 ${isPlayingVoice ? 'animate-bounce' : ''}`} />
                  <span>{isPlayingVoice ? 'Synthesizing...' : 'Test Voice Preview'}</span>
                </button>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {[
                  { id: 'en-US-Standard', label: 'English (US Standard)', lang: 'EN' },
                  { id: 'en-US-Neural', label: 'English (Neural Studio)', lang: 'EN' },
                  { id: 'hi-IN-Standard', label: 'Hindi (Standard)', lang: 'HI' },
                  { id: 'ta-IN-Standard', label: 'Tamil (Standard)', lang: 'TA' },
                ].map(v => (
                  <button
                    key={v.id}
                    type="button"
                    onClick={() => setVoice(v.id)}
                    className={`flex flex-col p-3 rounded-xl border text-left transition ${
                      voice === v.id
                        ? 'bg-emerald-500/10 border-emerald-500 text-white'
                        : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <span className="text-[10px] font-bold text-emerald-400 font-mono">{v.lang}</span>
                    <span className="text-xs font-semibold mt-1 line-clamp-1">{v.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Style Presets */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
                3. Visual Aesthetic Style
              </label>
              <div className="flex flex-wrap gap-2 mb-3">
                {[
                  { id: 'cinematic', label: 'Cinematic 4K' },
                  { id: 'minimalist', label: 'Minimalist Tech' },
                  { id: 'corporate', label: 'Corporate Clean' },
                  { id: 'documentary', label: 'Documentary Warm' },
                  { id: 'urban', label: 'Vibrant Urban' },
                ].map(s => (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => setStylePreset(s.id)}
                    className={`px-3.5 py-1.5 rounded-lg text-xs font-medium border transition ${
                      stylePreset === s.id
                        ? 'bg-emerald-500/15 border-emerald-500 text-emerald-300 font-semibold'
                        : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
              <input
                type="text"
                value={customStyle}
                onChange={e => setCustomStyle(e.target.value)}
                placeholder="Optional custom visual direction (e.g., 'warm dusk lighting, shallow depth of field')"
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              />
            </div>
          </div>
        </div>

        {/* Right Column: Aspect Ratios, Avoid Rules, Captions & Submit */}
        <div className="lg:col-span-5 flex flex-col gap-6">
          {/* Aspect Ratio Selector */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <div className="flex items-center justify-between mb-3">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-400">
                4. Aspect Ratios (Multi-Render)
              </label>
              <span className="text-[11px] text-slate-400 font-mono">{aspectRatios.length} selected</span>
            </div>
            <p className="text-xs text-slate-400 mb-4 leading-relaxed">
              We render independent 1080p outputs for each ratio. 9:16 automatically applies our <strong>saliency-aware crop</strong> to keep the key subject centered.
            </p>

            <div className="grid grid-cols-3 gap-3">
              {[
                { id: '16:9' as AspectRatio, label: '16:9', desc: 'Landscape (YouTube)', icon: 'w-8 h-5' },
                { id: '9:16' as AspectRatio, label: '9:16', desc: 'Vertical (Reels/Shorts)', icon: 'w-5 h-8' },
                { id: '1:1' as AspectRatio, label: '1:1', desc: 'Square (Feed)', icon: 'w-6 h-6' },
              ].map(r => {
                const selected = aspectRatios.includes(r.id)
                return (
                  <button
                    key={r.id}
                    type="button"
                    onClick={() => toggleRatio(r.id)}
                    className={`flex flex-col items-center justify-center p-4 rounded-xl border text-center transition ${
                      selected
                        ? 'bg-emerald-500/10 border-emerald-500 text-white'
                        : 'bg-slate-950 border-slate-800 text-slate-500 hover:border-slate-700'
                    }`}
                  >
                    <div
                      className={`border-2 rounded mb-2 flex items-center justify-center ${r.icon} ${
                        selected ? 'border-emerald-400 bg-emerald-500/20' : 'border-slate-700'
                      }`}
                    >
                      {selected && <Check className="w-3 h-3 text-emerald-400" />}
                    </div>
                    <span className="text-sm font-bold">{r.label}</span>
                    <span className="text-[10px] text-slate-400 line-clamp-1 mt-0.5">{r.desc}</span>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Avoid / Negative Tags */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <div className="flex items-center gap-2 mb-2 text-slate-300">
              <ShieldAlert className="w-4 h-4 text-amber-400" />
              <label className="text-xs font-bold uppercase tracking-wider text-slate-400">
                5. Avoid Rules (Strict Filtering)
              </label>
            </div>
            <p className="text-xs text-slate-400 mb-3 leading-relaxed">
              Footage containing these visual tags is automatically rejected during ranking.
            </p>

            <div className="flex flex-wrap gap-1.5 mb-3">
              {avoidTags.map(tag => (
                <span
                  key={tag}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs font-medium"
                >
                  <span>{tag}</span>
                  <button
                    type="button"
                    onClick={() => removeAvoidTag(tag)}
                    className="hover:text-white transition"
                    aria-label={`Remove avoid tag ${tag}`}
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>

            <div className="flex gap-2">
              <input
                type="text"
                value={newTagInput}
                onChange={e => setNewTagInput(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    addAvoidTag()
                  }
                }}
                placeholder="Add negative tag (e.g. 'logos', 'crowds')"
                className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              />
              <button
                type="button"
                onClick={addAvoidTag}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold transition"
              >
                Add
              </button>
            </div>
          </div>

          {/* Captions Toggles */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col gap-4">
            <label className="text-xs font-bold uppercase tracking-wider text-slate-400">
              6. Captions & Deliverables
            </label>

            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950 border border-slate-800">
              <div className="flex items-center gap-3">
                <Subtitles className="w-4 h-4 text-emerald-400" />
                <div>
                  <p className="text-xs font-semibold text-slate-200">Burn-in ASS Captions</p>
                  <p className="text-[11px] text-slate-400">Render styled synchronized subtitle strip on video</p>
                </div>
              </div>
              <input
                type="checkbox"
                checked={burnInCaptions}
                onChange={e => setBurnInCaptions(e.target.checked)}
                className="w-4 h-4 rounded text-emerald-500 focus:ring-emerald-500 bg-slate-900 border-slate-700"
              />
            </div>

            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950 border border-slate-800">
              <div className="flex items-center gap-3">
                <FileText className="w-4 h-4 text-emerald-400" />
                <div>
                  <p className="text-xs font-semibold text-slate-200">Export SRT File</p>
                  <p className="text-[11px] text-slate-400">Timecoded caption file per aspect ratio</p>
                </div>
              </div>
              <input
                type="checkbox"
                checked={srtCaptions}
                onChange={e => setSrtCaptions(e.target.checked)}
                className="w-4 h-4 rounded text-emerald-500 focus:ring-emerald-500 bg-slate-900 border-slate-700"
              />
            </div>
          </div>

          {/* Validation Feedback & Submission */}
          <div className="flex flex-col gap-3">
            {!isValid && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-300 text-xs flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 shrink-0" />
                <span>{validationMessage}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={!isValid || isLoading}
              className={`w-full py-4 rounded-xl font-bold text-sm flex items-center justify-center gap-2 shadow-2xl transition ${
                isValid && !isLoading
                  ? 'bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 shadow-emerald-500/25 active:scale-[0.98]'
                  : 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
              }`}
            >
              {isLoading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Enqueuing Media Pipeline...</span>
                </>
              ) : (
                <>
                  <span>Create B-Roll Video</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}
