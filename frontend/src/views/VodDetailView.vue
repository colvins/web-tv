<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { ChevronLeft, RefreshCw } from 'lucide-vue-next'
import { NButton, useMessage } from 'naive-ui'
import { useRoute, useRouter } from 'vue-router'

import { ApiError } from '@/api/client'
import { getVodDetail, getVodEpisodePlay, type VodBrowseDetailResponse, type VodEpisodePlayResponse } from '@/api/sourceConfigs'
import VodEpisodeList from '@/components/vod/VodEpisodeList.vue'
import VodPlayer from '@/components/vod/VodPlayer.vue'
import VodPoster from '@/components/vod/VodPoster.vue'
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
const playerSection = ref<HTMLElement | null>(null)

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
    playerSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
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
</script>

<template>
  <section class="grid gap-6">
    <article class="glass-panel rounded-[2.5rem] p-6 sm:p-8">
      <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-3 text-sm text-white/46">
            <button type="button" class="inline-flex items-center gap-2 text-white/74 transition hover:text-white" @click="goBack">
              <ChevronLeft class="h-4 w-4" aria-hidden="true" />
              Back to catalog
            </button>
          </div>
          <h2 class="mt-4 text-3xl font-semibold text-white sm:text-5xl">
            {{ detail?.name ?? 'VOD Detail' }}
          </h2>
          <div v-if="detail" class="mt-4 flex flex-wrap gap-2 text-xs text-white/62">
            <span v-if="detail.category_name" class="rounded-full border border-white/10 bg-white/6 px-3 py-1">{{ detail.category_name }}</span>
            <span v-if="detail.year" class="rounded-full border border-white/10 bg-white/6 px-3 py-1">{{ detail.year }}</span>
            <span v-if="detail.area" class="rounded-full border border-white/10 bg-white/6 px-3 py-1">{{ detail.area }}</span>
            <span v-if="detail.language" class="rounded-full border border-white/10 bg-white/6 px-3 py-1">{{ detail.language }}</span>
            <span v-if="detail.remarks" class="rounded-full border border-white/10 bg-white/6 px-3 py-1">{{ detail.remarks }}</span>
          </div>
        </div>
        <NButton round secondary :loading="detailLoading" @click="loadDetail">
          <template #icon><RefreshCw class="h-4 w-4" /></template>
          Refresh detail
        </NButton>
      </div>
    </article>

    <div v-if="detailLoading" class="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_22rem]">
      <article class="glass-panel rounded-[2.25rem] p-5 sm:p-6">
        <div class="aspect-video animate-pulse rounded-[1.75rem] bg-white/8"></div>
        <div class="mt-5 h-12 w-full animate-pulse rounded-[1.25rem] bg-white/8"></div>
        <div class="mt-4 h-40 w-full animate-pulse rounded-[1.5rem] bg-white/8"></div>
      </article>
      <article class="glass-panel rounded-[2.25rem] p-5 sm:p-6">
        <div class="aspect-[3/4] animate-pulse rounded-[1.75rem] bg-white/8"></div>
        <div class="mt-5 h-6 w-2/3 animate-pulse rounded-full bg-white/8"></div>
        <div class="mt-4 h-28 w-full animate-pulse rounded-[1.5rem] bg-white/8"></div>
      </article>
    </div>

    <div
      v-else-if="detailError"
      class="glass-panel rounded-[2rem] border border-red-300/18 bg-red-400/10 p-5 text-red-100"
    >
      {{ detailError }}
    </div>

    <div v-else-if="detail" class="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_22rem]">
      <div class="order-1 grid gap-6">
        <article ref="playerSection" class="glass-panel rounded-[2.25rem] p-5 sm:p-6">
          <div class="flex items-center justify-between gap-4">
            <div>
              <p class="text-sm uppercase tracking-[0.2em] text-white/40">Player</p>
              <p class="mt-2 text-sm text-white/58">Select an episode and keep the player in view.</p>
            </div>
            <span class="rounded-full border border-white/10 bg-white/6 px-3 py-1 text-xs text-white/54">
              {{ detail.play_sources.length }} source groups
            </span>
          </div>
          <VodPlayer :playback="playback" :episode-error="episodeError" />
        </article>

        <article class="glass-panel rounded-[2.25rem] p-5 sm:p-6">
          <div class="flex items-center justify-between gap-4">
            <div>
              <p class="text-sm uppercase tracking-[0.2em] text-white/40">Episodes</p>
              <p class="mt-2 text-sm text-white/58">Choose a source and episode without leaving the player area.</p>
            </div>
          </div>
          <VodEpisodeList
            :play-sources="detail.play_sources"
            :episode-loading-key="episodeLoadingKey"
            :selected-source-name="playback.currentEpisode.value?.source_name ?? null"
            :selected-episode-index="playback.currentEpisode.value?.episode_index ?? null"
            @play-episode="playEpisode"
          />
        </article>
      </div>

      <aside class="order-2 grid gap-6">
        <article class="glass-panel rounded-[2.25rem] p-5 sm:p-6">
          <VodPoster
            :src="detail.poster"
            :alt="detail.name"
            class="rounded-[1.75rem] border border-white/10"
            icon-class="h-16 w-16"
            image-class="aspect-[3/4] w-full object-cover"
          />

          <div class="mt-5 grid gap-4">
            <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-4">
              <p class="text-xs uppercase tracking-[0.16em] text-white/40">Actor</p>
              <p class="mt-2 text-sm leading-6 text-white/78">{{ detail.actor ?? 'Not provided' }}</p>
            </div>
            <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-4">
              <p class="text-xs uppercase tracking-[0.16em] text-white/40">Director</p>
              <p class="mt-2 text-sm leading-6 text-white/78">{{ detail.director ?? 'Not provided' }}</p>
            </div>
          </div>
        </article>

        <article class="glass-panel rounded-[2.25rem] p-5 sm:p-6">
          <p class="text-xs uppercase tracking-[0.16em] text-white/40">Description</p>
          <p class="mt-3 text-sm leading-7 text-white/74">{{ cleanDescription || 'No description available.' }}</p>
        </article>
      </aside>
    </div>
  </section>
</template>
