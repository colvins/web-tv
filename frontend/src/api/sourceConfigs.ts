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

export function listSourceVodSites(sourceConfigId: string): Promise<VodSite[]> {
  return apiRequest<VodSite[]>(`/configs/${sourceConfigId}/vod-sites`)
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

export function setCurrentVodSite(vodSiteId: string): Promise<CurrentVodSite> {
  return apiRequest<CurrentVodSite>('/settings/current-vod-site', {
    method: 'PUT',
    body: JSON.stringify({ vod_site_id: vodSiteId }),
  })
}
