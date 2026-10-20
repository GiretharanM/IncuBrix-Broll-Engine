export type AspectRatio = '16:9' | '9:16' | '1:1'

export type JobStatus = 'queued' | 'running' | 'succeeded' | 'failed'

export interface SceneCandidate {
  id: string
  provider: 'pexels' | 'pixabay' | 'generative' | 'mock'
  external_id: string
  title: string
  preview_url: string
  download_url: string
  duration: number
  relevance_score: number
  reason?: string
  is_selected?: boolean
  ai_generated?: boolean
  licence_name: string
  attribution?: string
  width?: number
  height?: number
}

export interface Scene {
  scene_id: string
  scene_index: number
  text: string
  visual_hint?: string
  visual_query?: string
  start_time: number
  end_time: number
  duration: number
  selected_clip_id?: string
  selection_reason?: string
  relevance_score?: number
  source_choice_reason?: string
  ai_generated?: boolean
  segment_hash?: string
  provider?: string
  licence_name?: string
  attribution?: string
  download_url?: string
  preview_url?: string
}

export interface Job {
  job_id: string
  status: JobStatus
  progress: number
  current_stage: string
  aspect_ratios: AspectRatio[]
  scenes: Scene[]
  result_urls: Record<string, string>
  warnings: string[]
  error_message?: string | null
  created_at: string
  updated_at: string
  completed_at?: string | null
  voice?: string
  style?: string
  script_text?: string
  audio_url?: string
}

export interface JobListItem {
  job_id: string
  status: JobStatus
  progress: number
  input_type: string
  script_preview?: string
  aspect_ratios: AspectRatio[]
  duration_seconds: number
  cost_estimate_usd: number
  created_at: string
  completed_at?: string | null
}

export interface JobMetrics {
  total_jobs: number
  succeeded_jobs: number
  failed_jobs: number
  avg_turnaround_seconds: number
  cost_per_minute_usd: number
  narration_coverage_ratio: number
  avg_relevance_score: number
  repeat_clip_rate: number
  success_rate_percent: number
  source_distribution: Record<string, number>
  ratio_distribution: Record<string, number>
}

export interface HardCaseSample {
  id: string
  title: string
  tag: string
  description: string
  script: string
  visual_hint: string
  avoid: string[]
  style: string
  voice: string
}
