import { apiRequest } from './client'

export type SourceType = 'json' | 'm3u' | 'txt' | 'm3u8'

export type SourceConfig = {
  id: string
  name: string
  source_type: SourceType
  url: string
  enabled: boolean
  last_import_at: string | null
  last_success_at: string | null
  last_error: string | null
  vod_site_count: number
  live_channel_count: number
  created_at: string
  updated_at: string
}

export type SourceConfigPayload = {
  name: string
  source_type: SourceType
  url: string
  enabled: boolean
}

export type ImportJobStatus = 'pending' | 'running' | 'success' | 'failed'
export type DetectedFormat =
  | 'plain_json'
  | 'catvod_json'
  | 'm3u'
  | 'txt'
  | 'base64_json'
  | 'binary_wrapped'
  | 'unknown'

export type ImportJob = {
  id: string
  source_config_id: string
  status: ImportJobStatus
  source_url: string
  content_type: string | null
  content_length: number | null
  content_sha256: string | null
  raw_preview: string | null
  detected_format: DetectedFormat | null
  detection_confidence: number | null
  detection_note: string | null
  error_message: string | null
  started_at: string | null
  finished_at: string | null
  created_at: string
  updated_at: string
}

export type VodSite = {
  id: string
  source_config_id: string | null
  import_job_id: string | null
  site_key: string
  site_name: string
  site_type: number | null
  api: string | null
  searchable: boolean | null
  changeable: boolean | null
  quick_search: boolean | null
  filterable: boolean | null
  player_type: number | null
  enabled: boolean
  sort_order: number
  analysis_note: string | null
  created_at: string
  updated_at: string
}

export type LiveExtractionStats = {
  groups_count: number
  channels_count: number
  created_count: number
  updated_count: number
  disabled_missing_count: number
  warnings: string[]
}

export type LiveChannelGroup = {
  id: string
  source_config_id: string
  name: string
  sort_order: number
  channel_count: number
  created_at: string
  updated_at: string
}

export type LiveChannel = {
  id: string
  source_config_id: string
  group_id: string | null
  name: string
  tvg_id: string | null
  tvg_name: string | null
  tvg_logo: string | null
  group_title: string | null
  stream_url: string
  raw_extinf: Record<string, unknown>
  enabled: boolean
  sort_order: number
  created_at: string
  updated_at: string
}

export type LiveChannelDiagnosisLevel =
  | 'playable_likely'
  | 'browser_format_unsupported'
  | 'cors_or_browser_block_likely'
  | 'upstream_unreachable'
  | 'upstream_error'
  | 'segment_error'
  | 'unknown'

export type LiveChannelDiagnosis = {
  channel_id: string
  channel_name: string
  group_name: string | null
  stream_host: string | null
  final_host: string | null
  http_status: number | null
  content_type: string | null
  content_length: number | null
  redirect_count: number
  stream_type_guess: 'hls_m3u8' | 'mpeg_ts' | 'mp4' | 'flv' | 'unknown'
  body_preview: string | null
  m3u8_info: {
    playlist_kind: string | null
    has_media_segments: boolean
    sample_segment_path: string | null
    preview_text: string | null
  } | null
  sample_segment_check: {
    status_code: number | null
    content_type: string | null
    content_length: number | null
    final_host: string | null
    warning: string | null
  } | null
  diagnosis_level: LiveChannelDiagnosisLevel
  diagnosis_summary: string
  suggested_next_step: string
  browser_playback_profile: string | null
  browser_playback_url: string | null
  warnings: string[]
}

export type CurrentVodSite = {
  id: string
  source_config_id: string | null
  site_key: string
  site_name: string
  site_type: number | null
  api: string | null
  enabled: boolean
  source_name: string | null
}

export type VodCapabilityAnalysisSummary = {
  total_sites: number
  generic_candidate_count: number
  spider_required_count: number
  unsupported_special_count: number
  missing_or_invalid_count: number
  unknown_count: number
}

export type VodCapabilityAnalysis = {
  source_config_id: string
  source_snapshot_id: string
  source_snapshot_created_at: string
  summary: VodCapabilityAnalysisSummary
  site_analyses: Array<{
    key: string | null
    name: string | null
    type: number | string | null
    api: string | null
    api_host: string | null
    searchable: boolean | number | null
    quickSearch: boolean | number | null
    filterable: boolean | number | null
    has_ext: boolean
    ext_type: string | null
    ext_summary: string | null
    capability_level: string
    capability_reason: string
  }>
}

export type CurrentVodSiteAnalysis = {
  site_id: string
  site_name: string
  site_key: string
  site_type: number | null
  api: string | null
  source_name: string | null
  enabled: boolean
  raw_keys: string[]
  known_flags: Record<string, unknown>
  ext_analysis: {
    present: boolean
    value_type: string | null
    summary: string
    looks_like_url: boolean
    looks_like_json: boolean
    looks_like_base64: boolean
    looks_like_executable_or_opaque: boolean
  }
  support_assessment: {
    level: 'metadata_only' | 'possible_http' | 'requires_spider' | 'unsupported_unknown'
    reason: string
    next_step: string
  }
  warnings: string[]
}

export type CurrentVodSiteSpiderAnalysis = {
  site_id: string
  site_key: string
  site_name: string
  site_type: number | null
  api: string | null
  source_name: string | null
  root_config_keys: string[]
  spider_field_present: boolean
  spider_field_summary: string
  api_reference_found: boolean
  api_reference_locations: string[]
  possible_reference_type:
    | 'none'
    | 'jar_reference'
    | 'js_reference'
    | 'py_reference'
    | 'remote_url_reference'
    | 'inline_name_only'
    | 'unknown'
  possible_reference_summary: string
  support_strategy: {
    level:
      | 'unsupported_unknown'
      | 'needs_spider_runtime'
      | 'possible_js_runtime'
      | 'possible_http_adapter'
      | 'metadata_only'
    reason: string
    recommended_next_step: string
  }
  warnings: string[]
}

export type SpiderArtifact = {
  id: string
  artifact_url: string
  expected_md5: string | null
  content_type: string | null
  content_length: number | null
  sha256: string | null
  md5: string | null
  md5_matches: boolean | null
  magic_hex: string | null
  detected_kind: string | null
  probe_status: 'pending' | 'success' | 'failed'
  error_message: string | null
  probed_at: string | null
  created_at: string
  updated_at: string
}

export type SpiderArtifactEntryAnalysis = {
  id: string
  spider_artifact_id: string
  source_config_id: string
  source_snapshot_id: string | null
  analysis_status: 'success' | 'failed'
  error_message: string | null
  total_entries: number | null
  total_compressed_size: number | null
  total_uncompressed_size: number | null
  top_level_dirs: string[]
  extension_counts: Record<string, number>
  matching_api_entries: string[]
  sample_entries: string[]
  has_class: boolean
  has_dex: boolean
  has_js: boolean
  has_json: boolean
  has_assets: boolean
  has_catvod_package: boolean
  suspicious_large_entries: number
  created_at: string
  updated_at: string
}

export function listSourceConfigs(): Promise<SourceConfig[]> {
  return apiRequest<SourceConfig[]>('/configs')
}

export function createSourceConfig(payload: SourceConfigPayload): Promise<SourceConfig> {
  return apiRequest<SourceConfig>('/configs', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateSourceConfig(
  id: string,
  payload: Partial<SourceConfigPayload>,
): Promise<SourceConfig> {
  return apiRequest<SourceConfig>(`/configs/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteSourceConfig(id: string): Promise<void> {
  return apiRequest<void>(`/configs/${id}`, {
    method: 'DELETE',
  })
}

export function importSourceConfig(id: string): Promise<ImportJob> {
  return apiRequest<ImportJob>(`/configs/${id}/import`, {
    method: 'POST',
  })
}

export function listImportJobs(): Promise<ImportJob[]> {
  return apiRequest<ImportJob[]>('/import-jobs')
}

export function getImportJob(id: string): Promise<ImportJob> {
  return apiRequest<ImportJob>(`/import-jobs/${id}`)
}

export function extractVodSites(sourceConfigId: string): Promise<VodSite[]> {
  return apiRequest<VodSite[]>(`/configs/${sourceConfigId}/extract-sites`, {
    method: 'POST',
  })
}

export function extractLiveChannels(sourceConfigId: string): Promise<LiveExtractionStats> {
  return apiRequest<LiveExtractionStats>(`/configs/${sourceConfigId}/extract-live-channels`, {
    method: 'POST',
  })
}

export function listLiveGroups(): Promise<LiveChannelGroup[]> {
  return apiRequest<LiveChannelGroup[]>('/live/groups')
}

export function listLiveChannels(params: { group_id?: string; q?: string } = {}): Promise<LiveChannel[]> {
  const query = new URLSearchParams()
  if (params.group_id) query.set('group_id', params.group_id)
  if (params.q) query.set('q', params.q)
  const suffix = query.toString() ? `?${query.toString()}` : ''
  return apiRequest<LiveChannel[]>(`/live/channels${suffix}`)
}

export function updateLiveChannel(id: string, enabled: boolean): Promise<LiveChannel> {
  return apiRequest<LiveChannel>(`/live/channels/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ enabled }),
  })
}

export function diagnoseLiveChannel(id: string): Promise<LiveChannelDiagnosis> {
  return apiRequest<LiveChannelDiagnosis>(`/live/channels/${id}/diagnose`, {
    method: 'POST',
  })
}

export function listSourceVodSites(sourceConfigId: string): Promise<VodSite[]> {
  return apiRequest<VodSite[]>(`/configs/${sourceConfigId}/vod-sites`)
}

export function getLatestVodCapabilityAnalysis(sourceConfigId: string): Promise<VodCapabilityAnalysis | null> {
  return apiRequest<VodCapabilityAnalysis | null>(`/configs/${sourceConfigId}/vod-capability-analysis/latest`)
}

export function updateVodSite(id: string, enabled: boolean): Promise<VodSite> {
  return apiRequest<VodSite>(`/vod-sites/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ enabled }),
  })
}

export function getCurrentVodSite(): Promise<CurrentVodSite | null> {
  return apiRequest<CurrentVodSite | null>('/settings/current-vod-site')
}

export function getCurrentVodSiteAnalysis(): Promise<CurrentVodSiteAnalysis | null> {
  return apiRequest<CurrentVodSiteAnalysis | null>('/settings/current-vod-site/analysis')
}

export function getCurrentVodSiteSpiderAnalysis(): Promise<CurrentVodSiteSpiderAnalysis | null> {
  return apiRequest<CurrentVodSiteSpiderAnalysis | null>('/settings/current-vod-site/spider-analysis')
}

export function getLatestSpiderArtifact(): Promise<SpiderArtifact | null> {
  return apiRequest<SpiderArtifact | null>('/settings/current-vod-site/spider-artifact/latest')
}

export function probeSpiderArtifact(): Promise<SpiderArtifact> {
  return apiRequest<SpiderArtifact>('/settings/current-vod-site/spider-artifact/probe', {
    method: 'POST',
  })
}

export function getLatestSpiderArtifactEntryAnalysis(): Promise<SpiderArtifactEntryAnalysis | null> {
  return apiRequest<SpiderArtifactEntryAnalysis | null>(
    '/settings/current-vod-site/spider-artifact/entry-analysis/latest',
  )
}

export function analyzeSpiderArtifactEntries(): Promise<SpiderArtifactEntryAnalysis | null> {
  return apiRequest<SpiderArtifactEntryAnalysis | null>(
    '/settings/current-vod-site/spider-artifact/analyze-entries',
    {
      method: 'POST',
    },
  )
}

export function setCurrentVodSite(vodSiteId: string): Promise<CurrentVodSite> {
  return apiRequest<CurrentVodSite>('/settings/current-vod-site', {
    method: 'PUT',
    body: JSON.stringify({ vod_site_id: vodSiteId }),
  })
}
