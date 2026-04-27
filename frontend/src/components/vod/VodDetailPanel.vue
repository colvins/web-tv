<script setup lang="ts">
import { ChevronLeft, Film } from 'lucide-vue-next'
import { NButton } from 'naive-ui'

import type { VodBrowseDetailResponse } from '@/api/sourceConfigs'
import type { VodPlayback } from '@/composables/useVodPlayback'

import VodEpisodeList from './VodEpisodeList.vue'
import VodPlayer from './VodPlayer.vue'

defineProps<{
  detail: VodBrowseDetailResponse | null
  detailTitle: string
  detailLoading: boolean
  detailError: string | null
  episodeLoadingKey: string | null
  episodeError: string | null
  playback: VodPlayback
}>()

const emit = defineEmits<{
  close: []
  playEpisode: [sourceName: string, episodeIndex: number]
}>()
</script>

<template>
  <article v-if="detail || detailLoading || detailError" class="glass-panel rounded-[2.25rem] p-6 sm:p-8">
    <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <p class="text-sm uppercase tracking-[0.26em] text-white/42">Detail</p>
        <h3 class="mt-3 text-2xl font-semibold text-white sm:text-3xl">{{ detailTitle }}</h3>
      </div>
      <NButton round secondary @click="emit('close')">
        <template #icon><ChevronLeft class="h-4 w-4" /></template>
        Back to results
      </NButton>
    </div>

    <div v-if="detailLoading" class="mt-6 grid gap-5 lg:grid-cols-[18rem_minmax(0,1fr)]">
      <div class="aspect-[3/4] animate-pulse rounded-[2rem] bg-white/8"></div>
      <div class="space-y-4">
        <div class="h-8 w-2/3 animate-pulse rounded-full bg-white/10"></div>
        <div class="h-4 w-full animate-pulse rounded-full bg-white/8"></div>
        <div class="h-4 w-5/6 animate-pulse rounded-full bg-white/8"></div>
      </div>
    </div>

    <p v-else-if="detailError" class="mt-6 rounded-3xl border border-red-300/18 bg-red-400/10 p-4 text-sm text-red-100">
      {{ detailError }}
    </p>

    <div v-else-if="detail" class="mt-6 grid gap-6 lg:grid-cols-[18rem_minmax(0,1fr)]">
      <div class="overflow-hidden rounded-[2rem] border border-white/10 bg-white/6">
        <img
          v-if="detail.poster"
          :src="detail.poster"
          :alt="detail.name"
          class="aspect-[3/4] w-full object-cover"
        />
        <div v-else class="flex aspect-[3/4] items-center justify-center text-white/30">
          <Film class="h-16 w-16" />
        </div>
      </div>

      <div class="space-y-5">
        <div class="flex flex-wrap gap-2 text-xs text-white/62">
          <span v-if="detail.category_name" class="rounded-full border border-white/10 bg-white/6 px-3 py-1">{{ detail.category_name }}</span>
          <span v-if="detail.year" class="rounded-full border border-white/10 bg-white/6 px-3 py-1">{{ detail.year }}</span>
          <span v-if="detail.area" class="rounded-full border border-white/10 bg-white/6 px-3 py-1">{{ detail.area }}</span>
          <span v-if="detail.language" class="rounded-full border border-white/10 bg-white/6 px-3 py-1">{{ detail.language }}</span>
          <span v-if="detail.remarks" class="rounded-full border border-white/10 bg-white/6 px-3 py-1">{{ detail.remarks }}</span>
        </div>

        <div class="grid gap-4 md:grid-cols-2">
          <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-4">
            <p class="text-xs uppercase tracking-[0.16em] text-white/40">Actor</p>
            <p class="mt-2 text-sm leading-6 text-white/78">{{ detail.actor ?? 'Not provided' }}</p>
          </div>
          <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-4">
            <p class="text-xs uppercase tracking-[0.16em] text-white/40">Director</p>
            <p class="mt-2 text-sm leading-6 text-white/78">{{ detail.director ?? 'Not provided' }}</p>
          </div>
        </div>

        <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-5">
          <p class="text-xs uppercase tracking-[0.16em] text-white/40">Description</p>
          <p class="mt-3 text-sm leading-7 text-white/74">{{ detail.description ?? 'No description returned by the collector.' }}</p>
        </div>

        <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-5">
          <p class="text-xs uppercase tracking-[0.16em] text-white/40">Collector metadata</p>
          <div class="mt-3 grid gap-3 sm:grid-cols-3 text-sm text-white/70">
            <p>Site: {{ detail.site.site_name ?? detail.site.site_key ?? 'Unknown' }}</p>
            <p>Host: {{ detail.site.api_host ?? 'Unknown' }}</p>
            <p>Path: {{ detail.site.api_path ?? 'Unknown' }}</p>
          </div>
          <div class="mt-3 flex flex-wrap gap-2">
            <span
              v-for="queryKey in detail.site.api_query_keys"
              :key="queryKey"
              class="rounded-full border border-white/10 bg-white/6 px-3 py-1 text-xs text-white/62"
            >
              {{ queryKey }}
            </span>
          </div>
        </div>

        <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-5">
          <div class="flex items-center justify-between gap-4">
            <p class="text-xs uppercase tracking-[0.16em] text-white/40">Play sources</p>
            <span class="text-xs text-white/46">Device-side playback only</span>
          </div>
          <VodPlayer :playback="playback" :episode-error="episodeError" />
          <VodEpisodeList
            :play-sources="detail.play_sources"
            :episode-loading-key="episodeLoadingKey"
            @play-episode="(sourceName, episodeIndex) => emit('playEpisode', sourceName, episodeIndex)"
          />
        </div>
      </div>
    </div>
  </article>
</template>
