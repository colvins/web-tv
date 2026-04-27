<script setup lang="ts">
import type { VodPlayback } from '@/composables/useVodPlayback'

withDefaults(defineProps<{
  playback: VodPlayback
  episodeError: string | null
  compact?: boolean
}>(), {
  compact: false,
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
        <h4 class="truncate font-semibold text-white" :class="compact ? 'text-base' : 'text-lg'">
          {{ playback.currentEpisode.value?.episode_name ?? '请选择剧集' }}
        </h4>
        <p v-if="episodeError || playback.errorMessage.value" class="mt-2 text-red-100" :class="compact ? 'text-[11px]' : 'text-xs'">
          {{ episodeError ?? playback.errorMessage.value }}
        </p>
      </div>
    </div>
  </div>
</template>
