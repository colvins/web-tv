<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useMessage } from 'naive-ui'
import { useRoute, useRouter } from 'vue-router'

import { ApiError } from '@/api/client'
import { getVodDetail, getVodEpisodePlay, type VodBrowseDetailResponse, type VodEpisodePlayResponse } from '@/api/sourceConfigs'
import VodDetailDesktopLayout from '@/components/vod/VodDetailDesktopLayout.vue'
import VodDetailMobileLayout from '@/components/vod/VodDetailMobileLayout.vue'
import { useVodPlayback } from '@/composables/useVodPlayback'
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
const backTarget = computed(() => ({
  name: 'vod',
  query: buildVodCatalogQuery({
    ...catalogState.value,
    sourceId: sourceConfigId.value || catalogState.value.sourceId,
  }),
}))

const cleanDescription = computed(() => detail.value?.description?.trim() ?? '')

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
      vod_id: vodId.value,
    })
  } catch (error) {
    detail.value = null
    detailError.value = error instanceof ApiError ? error.message : 'Unable to load VOD detail'
  } finally {
    detailLoading.value = false
  }
}

async function playEpisode(groupSourceName: string, episodeIndex: number) {
  if (!detail.value?.vod_id) return

  const key = `${groupSourceName}:${episodeIndex}`
  episodeLoadingKey.value = key
  episodeError.value = null

  try {
    const episode: VodEpisodePlayResponse = await getVodEpisodePlay({
      source_config_id: sourceConfigId.value,
      vod_id: detail.value.vod_id,
      source_name: groupSourceName,
      episode_index: episodeIndex,
    })
    await playback.loadEpisode(episode)
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
      :clean-description="cleanDescription"
      :episode-loading-key="episodeLoadingKey"
      :episode-error="episodeError"
      :playback="playback"
      @go-back="goBack"
      @refresh="loadDetail"
      @play-episode="playEpisode"
    />

    <VodDetailMobileLayout
      v-else
      :detail="detail"
      :detail-loading="detailLoading"
      :detail-error="detailError"
      :clean-description="cleanDescription"
      :episode-loading-key="episodeLoadingKey"
      :episode-error="episodeError"
      :playback="playback"
      @go-back="goBack"
      @refresh="loadDetail"
      @play-episode="playEpisode"
    />
  </div>
</template>
