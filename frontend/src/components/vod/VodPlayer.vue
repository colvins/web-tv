<script setup lang="ts">
import { Maximize, Pause, Play, Volume2, VolumeX } from 'lucide-vue-next'
import { computed } from 'vue'
import { NButton } from 'naive-ui'

import type { VodPlayback } from '@/composables/useVodPlayback'

const props = withDefaults(defineProps<{
  playback: VodPlayback
  episodeError: string | null
  compact?: boolean
  title?: string
  subtitle?: string | null
}>(), {
  compact: false,
  title: '播放器',
  subtitle: '请选择剧集并保持播放器在视野内。',
})

const playbackStateLabel = computed(() => {
  switch (props.playback.playbackState.value) {
    case 'loading':
      return '加载中'
    case 'ready':
      return '可播放'
    case 'error':
      return '播放失败'
    default:
      return '未开始'
  }
})
</script>

<template>
  <div
    class="overflow-hidden border border-white/10 bg-black/32"
    :class="compact ? 'rounded-[1.25rem]' : 'mt-4 rounded-[1.5rem]'"
    data-vod-player-shell
  >
    <div class="relative aspect-video bg-black">
      <video
        :ref="playback.setVideoElement"
        class="h-full w-full bg-black object-contain"
        playsinline
        controls
        controlslist="nodownload noplaybackrate"
        preload="none"
        @canplay="playback.handleCanPlay"
        @error="playback.handleVideoError"
        @pause="playback.handlePause"
        @playing="playback.handlePlaying"
        @volumechange="playback.handleVolumeChange"
        @waiting="playback.handleWaiting"
      ></video>
      <div class="absolute inset-x-0 top-0 bg-gradient-to-b from-black/80 via-black/30 to-transparent" :class="compact ? 'p-3' : 'p-4'">
        <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div class="min-w-0">
            <p v-if="title" class="text-[11px] uppercase tracking-[0.22em] text-white/42">{{ title }}</p>
            <h4 class="mt-2 truncate font-semibold text-white" :class="compact ? 'text-base' : 'text-lg'">
              {{ playback.currentEpisode.value?.episode_name ?? '请选择剧集' }}
            </h4>
            <p v-if="subtitle" class="mt-2 text-white/62" :class="compact ? 'text-xs' : 'text-sm'">{{ subtitle }}</p>
            <p class="mt-2 text-white/62" :class="compact ? 'text-xs' : 'text-sm'">{{ playback.playerStatusText.value }}</p>
            <p v-if="episodeError || playback.errorMessage.value" class="mt-2 text-red-100" :class="compact ? 'text-[11px]' : 'text-xs'">
              {{ episodeError ?? playback.errorMessage.value }}
            </p>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <span
              class="rounded-full border px-3 py-1 text-[11px] uppercase tracking-[0.18em]"
              :class="
                playback.playbackState.value === 'error'
                  ? 'border-red-300/30 bg-red-400/12 text-red-100'
                  : playback.playbackState.value === 'loading'
                    ? 'border-amber-300/30 bg-amber-300/12 text-amber-100'
                    : playback.playbackState.value === 'ready'
                      ? 'border-emerald-300/30 bg-emerald-300/12 text-emerald-100'
                      : 'border-white/12 bg-white/8 text-white/56'
              "
            >
              {{ playbackStateLabel }}
            </span>
            <NButton round secondary :disabled="!playback.currentEpisode.value" @click="playback.togglePlayback">
              <template #icon>
                <Pause v-if="playback.isPlaying.value" class="h-4 w-4" />
                <Play v-else class="h-4 w-4" />
              </template>
              {{ playback.isPlaying.value ? '暂停' : '播放' }}
            </NButton>
            <NButton round secondary :disabled="!playback.currentEpisode.value" @click="playback.toggleMute">
              <template #icon>
                <VolumeX v-if="playback.isMuted.value" class="h-4 w-4" />
                <Volume2 v-else class="h-4 w-4" />
              </template>
              {{ playback.isMuted.value ? '取消静音' : '静音' }}
            </NButton>
            <NButton round secondary :disabled="!playback.currentEpisode.value" @click="playback.toggleFullscreen">
              <template #icon><Maximize class="h-4 w-4" /></template>
              全屏
            </NButton>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
