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
  created_at: string
  updated_at: string
}

export type SourceConfigPayload = {
  name: string
  source_type: SourceType
  url: string
  enabled: boolean
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
