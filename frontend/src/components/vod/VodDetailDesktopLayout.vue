<script setup lang="ts">
import { ChevronLeft } from 'lucide-vue-next'

import type { VodBrowseDetailResponse } from '@/api/sourceConfigs'
import type { VodPlayback } from '@/composables/useVodPlayback'
import VodEpisodeList from '@/components/vod/VodEpisodeList.vue'
import VodPlayer from '@/components/vod/VodPlayer.vue'

defineProps<{
  detail: VodBrowseDetailResponse | null
  detailLoading: boolean
  detailError: string | null
  episodeLoadingKey: string | null
  episodeError: string | null
  playback: VodPlayback
}>()

const emit = defineEmits<{
  goBack: []
  playEpisode: [sourceName: string, episodeIndex: number]
}>()
</script>

<template>
  <section class="grid gap-6">
    <article class="glass-panel rounded-[2.5rem] p-6 sm:p-8">
      <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-3 text-sm text-white/46">
            <button type="button" class="inline-flex items-center gap-2 text-white/74 transition hover:text-white" @click="emit('goBack')">
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
      </div>
    </article>

    <div v-if="detailLoading" class="grid gap-6">
      <article class="glass-panel rounded-[2.25rem] p-5 sm:p-6">
        <div class="aspect-video animate-pulse rounded-[1.75rem] bg-white/8"></div>
        <div class="mt-4 h-40 w-full animate-pulse rounded-[1.5rem] bg-white/8"></div>
      </article>
    </div>

    <div
      v-else-if="detailError"
      class="glass-panel rounded-[2rem] border border-red-300/18 bg-red-400/10 p-5 text-red-100"
    >
      {{ detailError }}
    </div>

    <article v-else-if="detail" class="glass-panel rounded-[2.25rem] p-5 sm:p-6">
      <VodPlayer :playback="playback" :episode-error="episodeError" />
      <div class="mt-4">
        <VodEpisodeList
          :play-sources="detail.play_sources"
          :episode-loading-key="episodeLoadingKey"
          :selected-source-name="playback.currentEpisode.value?.source_name ?? null"
          :selected-episode-index="playback.currentEpisode.value?.episode_index ?? null"
          @play-episode="(sourceName, episodeIndex) => emit('playEpisode', sourceName, episodeIndex)"
        />
      </div>
    </article>
  </section>
</template>
