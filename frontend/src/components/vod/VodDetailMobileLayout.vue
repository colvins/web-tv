<script setup lang="ts">
import { ChevronLeft, RefreshCw } from 'lucide-vue-next'
import { NButton } from 'naive-ui'

import type { VodBrowseDetailResponse } from '@/api/sourceConfigs'
import type { VodPlayback } from '@/composables/useVodPlayback'
import VodEpisodeList from '@/components/vod/VodEpisodeList.vue'
import VodPlayer from '@/components/vod/VodPlayer.vue'

defineProps<{
  detail: VodBrowseDetailResponse | null
  detailLoading: boolean
  detailError: string | null
  cleanDescription: string
  episodeLoadingKey: string | null
  episodeError: string | null
  playback: VodPlayback
}>()

const emit = defineEmits<{
  goBack: []
  refresh: []
  playEpisode: [sourceName: string, episodeIndex: number]
}>()
</script>

<template>
  <section class="grid gap-4 pb-[calc(7rem+env(safe-area-inset-bottom))]">
    <article class="glass-panel rounded-[1.75rem] p-5">
      <div class="flex items-start justify-between gap-4">
        <button type="button" class="inline-flex items-center gap-2 text-sm text-white/74 transition hover:text-white" @click="emit('goBack')">
          <ChevronLeft class="h-4 w-4" aria-hidden="true" />
          返回列表
        </button>
        <NButton quaternary circle :loading="detailLoading" @click="emit('refresh')">
          <template #icon><RefreshCw class="h-4 w-4" /></template>
        </NButton>
      </div>

      <div class="mt-4 min-w-0">
        <h2 class="text-2xl font-semibold text-white">{{ detail?.name ?? '影片详情' }}</h2>
        <div v-if="detail" class="mt-4 flex flex-wrap gap-2 text-[11px] text-white/62">
          <span v-if="detail.category_name" class="rounded-full border border-white/10 bg-white/6 px-3 py-1">{{ detail.category_name }}</span>
          <span v-if="detail.year" class="rounded-full border border-white/10 bg-white/6 px-3 py-1">{{ detail.year }}</span>
          <span v-if="detail.area" class="rounded-full border border-white/10 bg-white/6 px-3 py-1">{{ detail.area }}</span>
          <span v-if="detail.language" class="rounded-full border border-white/10 bg-white/6 px-3 py-1">{{ detail.language }}</span>
          <span v-if="detail.remarks" class="rounded-full border border-white/10 bg-white/6 px-3 py-1">{{ detail.remarks }}</span>
        </div>
      </div>
    </article>

    <div v-if="detailLoading" class="grid gap-4">
      <article class="glass-panel rounded-[1.5rem] p-4">
        <div class="aspect-video animate-pulse rounded-[1.25rem] bg-white/8"></div>
      </article>
      <article class="glass-panel rounded-[1.5rem] p-4">
        <div class="h-40 animate-pulse rounded-[1.25rem] bg-white/8"></div>
      </article>
    </div>

    <div
      v-else-if="detailError"
      class="glass-panel rounded-[1.5rem] border border-red-300/18 bg-red-400/10 p-4 text-red-100"
    >
      {{ detailError }}
    </div>

    <template v-else-if="detail">
      <article class="glass-panel rounded-[1.5rem] p-4">
        <VodPlayer compact :playback="playback" :episode-error="episodeError" />
        <div class="mt-3 pb-[calc(5.5rem+env(safe-area-inset-bottom))]">
          <VodEpisodeList
            compact
            :play-sources="detail.play_sources"
            :episode-loading-key="episodeLoadingKey"
            :selected-source-name="playback.currentEpisode.value?.source_name ?? null"
            :selected-episode-index="playback.currentEpisode.value?.episode_index ?? null"
            @play-episode="(sourceName, episodeIndex) => emit('playEpisode', sourceName, episodeIndex)"
          />
        </div>
      </article>
    </template>
  </section>
</template>
