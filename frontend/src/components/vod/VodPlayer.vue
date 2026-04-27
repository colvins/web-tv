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
    <div class="flex items-center justify-between gap-3 border-b border-white/10 bg-black/24" :class="compact ? 'px-3 py-3' : 'px-4 py-3'">
      <h4 class="min-w-0 truncate font-semibold text-white" :class="compact ? 'text-base' : 'text-lg'">
        {{ playback.currentEpisode.value?.episode_name ?? '请选择剧集' }}
      </h4>
    </div>

    <div class="aspect-video bg-black">
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
    </div>
    <div v-if="episodeError || playback.errorMessage.value" class="border-t border-red-300/18 bg-red-400/10 text-red-100" :class="compact ? 'px-3 py-2 text-[11px]' : 'px-4 py-3 text-xs'">
      {{ episodeError ?? playback.errorMessage.value }}
    </div>
  </div>
</template>
