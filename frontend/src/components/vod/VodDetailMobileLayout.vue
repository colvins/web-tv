<script setup lang="ts">
import { ChevronLeft, RefreshCw } from 'lucide-vue-next'
import { NButton } from 'naive-ui'

import type { VodBrowseDetailResponse } from '@/api/sourceConfigs'
import type { VodPlayback } from '@/composables/useVodPlayback'
import VodEpisodeList from '@/components/vod/VodEpisodeList.vue'
import VodPlayer from '@/components/vod/VodPlayer.vue'
import VodPoster from '@/components/vod/VodPoster.vue'

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
        <p class="text-xs uppercase tracking-[0.16em] text-white/40">播放</p>
        <VodPlayer
          compact
          :playback="playback"
          :episode-error="episodeError"
          :show-technical-details="false"
          title="播放"
          :subtitle="null"
        />
      </article>

      <article class="glass-panel rounded-[1.5rem] p-4">
        <div class="flex items-center justify-between gap-3">
          <p class="text-xs uppercase tracking-[0.16em] text-white/40">选集</p>
          <span class="rounded-full border border-white/10 bg-white/6 px-3 py-1 text-[11px] text-white/54">
            {{ detail.play_sources.length }} 个线路
          </span>
        </div>
        <div class="mt-3">
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

      <article class="glass-panel rounded-[1.5rem] p-4">
        <div class="grid gap-4 sm:grid-cols-[7rem_minmax(0,1fr)]">
          <VodPoster
            :src="detail.poster"
            :alt="detail.name"
            class="rounded-[1.25rem] border border-white/10"
            icon-class="h-10 w-10"
            image-class="aspect-[3/4] w-full object-cover"
          />

          <div class="grid gap-3">
            <div v-if="detail.actor" class="rounded-[1.25rem] border border-white/10 bg-black/18 p-4">
              <p class="text-[11px] uppercase tracking-[0.16em] text-white/40">演员</p>
              <p class="mt-2 text-sm leading-6 text-white/78">{{ detail.actor }}</p>
            </div>
            <div v-if="detail.director" class="rounded-[1.25rem] border border-white/10 bg-black/18 p-4">
              <p class="text-[11px] uppercase tracking-[0.16em] text-white/40">导演</p>
              <p class="mt-2 text-sm leading-6 text-white/78">{{ detail.director }}</p>
            </div>
          </div>
        </div>

        <div class="mt-4 rounded-[1.25rem] border border-white/10 bg-black/18 p-4">
          <p class="text-[11px] uppercase tracking-[0.16em] text-white/40">简介</p>
          <p class="mt-3 text-sm leading-7 text-white/74">{{ cleanDescription || '暂无简介。' }}</p>
        </div>
      </article>
    </template>
  </section>
</template>
