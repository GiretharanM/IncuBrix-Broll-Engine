import React, { useState } from 'react'
import { Terminal, Copy, Check, X } from 'lucide-react'
import { CreateJobPayload } from '../api'

interface CurlModalProps {
  isOpen: boolean
  onClose: () => void
  payload: CreateJobPayload
  onCopied: () => void
}

export const CurlModal: React.FC<CurlModalProps> = ({ isOpen, onClose, payload, onCopied }) => {
  const [copied, setCopied] = useState(false)

  if (!isOpen) return null

  const curlCommand = `curl -X POST http://localhost:8000/api/v1/broll/jobs \\
  -H "Content-Type: application/json" \\
  -H "Idempotency-Key: ${payload.idempotency_key || 'idem-key-' + Math.random().toString(36).substring(2, 9)}" \\
  -d '${JSON.stringify(
    {
      script_text: payload.script_text || undefined,
      audio_url: payload.audio_url || undefined,
      scenes: payload.scenes && payload.scenes.length > 0 ? payload.scenes : undefined,
      voice: payload.voice,
      aspect_ratios: payload.aspect_ratios,
      style: payload.style,
      avoid: payload.avoid,
      burn_in_captions: payload.burn_in_captions,
      srt_captions: payload.srt_captions,
    },
    null,
    2
  )}'`

  const handleCopy = () => {
    navigator.clipboard.writeText(curlCommand)
    setCopied(true)
    onCopied()
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="curl-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in"
    >
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 shadow-2xl flex flex-col max-h-[85vh]">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-2 text-emerald-400">
            <Terminal className="w-5 h-5" />
            <h3 id="curl-modal-title" className="text-lg font-bold text-white">
              Executable cURL Command
            </h3>
          </div>
          <button
            onClick={onClose}
            aria-label="Close dialog"
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <p className="text-xs text-slate-400 mt-4 leading-relaxed">
          Run this curl command in your terminal to trigger the identical B-roll generation pipeline via the REST API.
          Supports <code className="text-emerald-400">Idempotency-Key</code> for guaranteed at-most-once processing.
        </p>

        <div className="mt-4 relative flex-1 min-h-[160px] bg-slate-950 border border-slate-800 rounded-xl p-4 overflow-auto font-mono text-xs text-slate-300 leading-relaxed">
          <pre>{curlCommand}</pre>
        </div>

        <div className="flex items-center justify-end gap-3 mt-6 pt-4 border-t border-slate-800">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
          >
            Close
          </button>
          <button
            onClick={handleCopy}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-semibold text-xs rounded-lg shadow-lg shadow-emerald-500/20 transition active:scale-95"
          >
            {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
            {copied ? 'Copied to Clipboard!' : 'Copy cURL Command'}
          </button>
        </div>
      </div>
    </div>
  )
}
