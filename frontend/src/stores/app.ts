import { defineStore } from 'pinia'

const RECENT_VOD_PLAYBACK_STORAGE_KEY = 'webtv.recentVodPlayback'
const RECENT_VOD_PLAYBACK_LIMIT = 18

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

function parseRecentVodPlayback(value: string | null): RecentVodPlaybackItem[] {
  if (!value) return []

  try {
    const parsed = JSON.parse(value)
    if (!Array.isArray(parsed)) return []

    return parsed.filter((item): item is RecentVodPlaybackItem => {
      return (
        item &&
        typeof item === 'object' &&
        typeof item.sourceConfigId === 'string' &&
        typeof item.vodId === 'string' &&
        typeof item.name === 'string' &&
        typeof item.episodeName === 'string' &&
        typeof item.episodeIndex === 'number' &&
        typeof item.watchedAt === 'string'
      )
    })
  } catch {
    return []
  }
}

export const useAppStore = defineStore('app', {
  state: () => ({
    sidebarCollapsed: false,
    recentVodPlayback: [] as RecentVodPlaybackItem[],
    persistentStateLoaded: false,
  }),
  actions: {
    ensurePersistentStateLoaded() {
      if (this.persistentStateLoaded || typeof window === 'undefined') return

      this.recentVodPlayback = parseRecentVodPlayback(window.localStorage.getItem(RECENT_VOD_PLAYBACK_STORAGE_KEY))
      this.persistentStateLoaded = true
    },
    persistRecentVodPlayback() {
      if (typeof window === 'undefined') return

      window.localStorage.setItem(
        RECENT_VOD_PLAYBACK_STORAGE_KEY,
        JSON.stringify(this.recentVodPlayback.slice(0, RECENT_VOD_PLAYBACK_LIMIT)),
      )
    },
    recordRecentVodPlayback(item: RecentVodPlaybackItem) {
      this.ensurePersistentStateLoaded()

      const nextItems = this.recentVodPlayback.filter(
        (entry) => !(entry.sourceConfigId === item.sourceConfigId && entry.vodId === item.vodId),
      )

      this.recentVodPlayback = [item, ...nextItems].slice(0, RECENT_VOD_PLAYBACK_LIMIT)
      this.persistRecentVodPlayback()
    },
    toggleSidebar() {
      this.sidebarCollapsed = !this.sidebarCollapsed
    },
  },
})
