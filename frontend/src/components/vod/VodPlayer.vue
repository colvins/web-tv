<script setup lang="ts">
import { Maximize, Pause, Play, Volume2, VolumeX } from 'lucide-vue-next'
import { NButton } from 'naive-ui'

import type { VodPlayback } from '@/composables/useVodPlayback'

defineProps<{
  playback: VodPlayback
  episodeError: string | null
}>()
</script>

<template>
  <div
    class="mt-4 overflow-hidden rounded-[1.5rem] border border-white/10 bg-black/32"
    data-vod-player-shell
  >
    <div class="relative aspect-video bg-black">
      <video
        :ref="playback.setVideoElement"
        class="h-full w-full bg-black object-contain"
        playsinline
        controlslist="nodownload noplaybackrate"
        preload="none"
        @canplay="playback.handleCanPlay"
        @error="playback.handleVideoError"
        @pause="playback.handlePause"
        @playing="playback.handlePlaying"
        @volumechange="playback.handleVolumeChange"
        @waiting="playback.handleWaiting"
      ></video>
      <div class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 via-black/30 to-transparent p-4">
        <div class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div class="min-w-0">
            <p class="text-[11px] uppercase tracking-[0.22em] text-white/42">Player</p>
            <h4 class="mt-2 truncate text-lg font-semibold text-white">
              {{ playback.currentEpisode.value?.episode_name ?? 'Select an episode' }}
            </h4>
            <p class="mt-2 text-sm text-white/62">{{ playback.playerStatusText.value }}</p>
            <p v-if="episodeError || playback.errorMessage.value" class="mt-2 text-xs text-red-100">
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
              {{ playback.playbackState.value }}
            </span>
            <NButton round secondary :disabled="!playback.currentEpisode.value" @click="playback.togglePlayback">
              <template #icon>
                <Pause v-if="playback.isPlaying.value" class="h-4 w-4" />
                <Play v-else class="h-4 w-4" />
              </template>
              {{ playback.isPlaying.value ? 'Pause' : 'Play' }}
            </NButton>
            <NButton round secondary :disabled="!playback.currentEpisode.value" @click="playback.toggleMute">
              <template #icon>
                <VolumeX v-if="playback.isMuted.value" class="h-4 w-4" />
                <Volume2 v-else class="h-4 w-4" />
              </template>
              {{ playback.isMuted.value ? 'Unmute' : 'Mute' }}
            </NButton>
            <NButton round secondary :disabled="!playback.currentEpisode.value" @click="playback.toggleFullscreen">
              <template #icon><Maximize class="h-4 w-4" /></template>
              Fullscreen
            </NButton>
          </div>
        </div>
      </div>
    </div>
    <div class="grid gap-3 border-t border-white/10 bg-black/26 p-4 sm:grid-cols-3">
      <div class="rounded-2xl border border-white/10 bg-white/6 p-3 text-sm text-white/70">
        <p class="text-[11px] uppercase tracking-[0.16em] text-white/40">Stream host</p>
        <p class="mt-2 break-all">{{ playback.streamHost.value }}</p>
      </div>
      <div class="rounded-2xl border border-white/10 bg-white/6 p-3 text-sm text-white/70">
        <p class="text-[11px] uppercase tracking-[0.16em] text-white/40">Stream type</p>
        <p class="mt-2">{{ playback.streamTypeGuess.value }}</p>
      </div>
      <div class="rounded-2xl border border-white/10 bg-white/6 p-3 text-sm text-white/70">
        <p class="text-[11px] uppercase tracking-[0.16em] text-white/40">Playback path</p>
        <p class="mt-2">
          {{
            playback.currentEpisode.value?.is_hls_like
              ? playback.nativeHlsSupported.value
                ? 'Native HLS'
                : playback.hlsJsSupported.value
                  ? 'hls.js'
                  : 'Unsupported'
              : 'Native video'
          }}
        </p>
      </div>
    </div>
  </div>
</template>
