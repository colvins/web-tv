<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useMessage } from 'naive-ui'
import { useRoute, useRouter } from 'vue-router'

import { ApiError } from '@/api/client'
import { getVodDetail, getVodEpisodePlay, type VodBrowseDetailResponse, type VodEpisodePlayResponse } from '@/api/sourceConfigs'
import VodDetailDesktopLayout from '@/components/vod/VodDetailDesktopLayout.vue'
import VodDetailMobileLayout from '@/components/vod/VodDetailMobileLayout.vue'
import { useVodPlayback } from '@/composables/useVodPlayback'
import { recordRecentVodPlayback } from '@/utils/recentVodPlayback'
import { buildVodCatalogQuery, parseVodCatalogRouteState } from '@/utils/vodRouteState'

const route = useRoute()
const router = useRouter()
const message = useMessage()

const detail = ref<VodBrowseDetailResponse | null>(null)
const detailLoading = ref(false)
const detailError = ref<string | null>(null)
const episodeLoadingKey = ref<string | null>(null)
const episodeError = ref<string | null>(null)
const playback = useVodPlayback()
const isDesktopLayout = ref(true)

let mediaQuery: MediaQueryList | undefined

const sourceConfigId = computed(() => String(route.params.sourceConfigId ?? ''))
const vodId = computed(() => String(route.params.vodId ?? ''))
const catalogState = computed(() => parseVodCatalogRouteState(route.query))
const preferredSourceName = computed(
  () => detail.value?.preferred_source_name ?? detail.value?.play_sources[0]?.source_name ?? null,
)
const backTarget = computed(() => ({
  name: 'vod',
  query: buildVodCatalogQuery({
    ...catalogState.value,
    sourceId: sourceConfigId.value || catalogState.value.sourceId,
  }),
}))

function syncLayoutMode() {
  isDesktopLayout.value = mediaQuery?.matches ?? window.innerWidth >= 768
}

async function loadDetail() {
  if (!sourceConfigId.value || !vodId.value) {
    detail.value = null
    detailError.value = 'Missing VOD detail route parameters'
    return
  }

  detailLoading.value = true
  detailError.value = null
  episodeError.value = null
  playback.destroyPlayer()

  try {
    detail.value = await getVodDetail({
      source_config_id: sourceConfigId.value,
      site_key: catalogState.value.siteKey,
      vod_id: vodId.value,
    })
  } catch (error) {
    detail.value = null
    detailError.value = error instanceof ApiError ? error.message : 'Unable to load VOD detail'
  } finally {
    detailLoading.value = false
  }
}

async function playEpisode(episodeIndex: number) {
  if (!detail.value?.vod_id) return
  const sourceName = preferredSourceName.value
  if (!sourceName) return

  const key = `${sourceName}:${episodeIndex}`
  episodeLoadingKey.value = key
  episodeError.value = null

  try {
    const episode: VodEpisodePlayResponse = await getVodEpisodePlay({
      source_config_id: sourceConfigId.value,
      site_key: catalogState.value.siteKey,
      vod_id: detail.value.vod_id,
      source_name: sourceName,
      episode_index: episodeIndex,
    })
    await playback.loadEpisode(episode)
    recordRecentVodPlayback({
      sourceConfigId: sourceConfigId.value,
      siteKey: catalogState.value.siteKey,
      vodId: String(detail.value.vod_id),
      name: detail.value.name,
      poster: detail.value.poster,
      categoryName: detail.value.category_name,
      year: detail.value.year,
      remarks: detail.value.remarks,
      sourceName,
      episodeName: episode.episode_name,
      episodeIndex: episode.episode_index,
      watchedAt: new Date().toISOString(),
    })
    await nextTick()
    document.querySelector<HTMLElement>('[data-vod-player-shell]')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  } catch (error) {
    episodeError.value = error instanceof ApiError ? error.message : 'Unable to load episode playback metadata'
    message.error(episodeError.value)
  } finally {
    episodeLoadingKey.value = null
  }
}

function goBack() {
  if (window.history.length > 1) {
    void router.back()
    return
  }
  void router.replace(backTarget.value)
}

watch(
  () => [sourceConfigId.value, vodId.value],
  () => {
    void loadDetail()
  },
  { immediate: true },
)

onMounted(() => {
  mediaQuery = window.matchMedia('(min-width: 768px)')
  syncLayoutMode()
  mediaQuery.addEventListener('change', syncLayoutMode)
})

onBeforeUnmount(() => {
  mediaQuery?.removeEventListener('change', syncLayoutMode)
})
</script>

<template>
  <div>
    <VodDetailDesktopLayout
      v-if="isDesktopLayout"
      :detail="detail"
      :detail-loading="detailLoading"
      :detail-error="detailError"
      :episode-loading-key="episodeLoadingKey"
      :episode-error="episodeError"
      :preferred-source-name="preferredSourceName"
      :playback="playback"
      @go-back="goBack"
      @play-episode="playEpisode"
    />

    <VodDetailMobileLayout
      v-else
      :detail="detail"
      :detail-loading="detailLoading"
      :detail-error="detailError"
      :episode-loading-key="episodeLoadingKey"
      :episode-error="episodeError"
      :preferred-source-name="preferredSourceName"
      :playback="playback"
      @go-back="goBack"
      @play-episode="playEpisode"
    />
  </div>
</template>
