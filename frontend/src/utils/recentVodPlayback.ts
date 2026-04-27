export const RECENT_VOD_PLAYBACK_STORAGE_KEY = 'webtv.recentVodPlayback'
export const RECENT_VOD_PLAYBACK_LIMIT = 20

export type RecentVodPlaybackItem = {
  sourceConfigId: string
  siteKey: string | null
  vodId: string
  name: string
  poster: string | null
  categoryName: string | null
  year: string | null
  remarks: string | null
  sourceName: string | null
  episodeName: string
  episodeIndex: number
  watchedAt: string
}

function isRecentVodPlaybackItem(value: unknown): value is RecentVodPlaybackItem {
  if (!value || typeof value !== 'object') return false

  const item = value as Record<string, unknown>
  return (
    typeof item.sourceConfigId === 'string' &&
    typeof item.vodId === 'string' &&
    typeof item.name === 'string' &&
    typeof item.episodeName === 'string' &&
    typeof item.episodeIndex === 'number' &&
    typeof item.watchedAt === 'string'
  )
}

export function listRecentVodPlayback(): RecentVodPlaybackItem[] {
  if (typeof window === 'undefined') return []

  const value = window.localStorage.getItem(RECENT_VOD_PLAYBACK_STORAGE_KEY)
  if (!value) return []

  try {
    const parsed = JSON.parse(value)
    if (!Array.isArray(parsed)) return []
    return parsed.filter(isRecentVodPlaybackItem).slice(0, RECENT_VOD_PLAYBACK_LIMIT)
  } catch {
    return []
  }
}

export function saveRecentVodPlayback(items: RecentVodPlaybackItem[]) {
  if (typeof window === 'undefined') return

  window.localStorage.setItem(
    RECENT_VOD_PLAYBACK_STORAGE_KEY,
    JSON.stringify(items.slice(0, RECENT_VOD_PLAYBACK_LIMIT)),
  )
}

export function recordRecentVodPlayback(item: RecentVodPlaybackItem): RecentVodPlaybackItem[] {
  const existingItems = listRecentVodPlayback()
  const nextItems = existingItems.filter(
    (entry) => !(entry.sourceConfigId === item.sourceConfigId && entry.vodId === item.vodId),
  )
  const result = [item, ...nextItems].slice(0, RECENT_VOD_PLAYBACK_LIMIT)
  saveRecentVodPlayback(result)
  return result
}
