<script setup lang="ts">
import { LoaderCircle, Maximize, Pause, Play, Tv, Volume2, VolumeX } from 'lucide-vue-next'

import type { LivePlayback } from '@/composables/useLivePlayback'

defineProps<{
  playback: LivePlayback
}>()
</script>

<template>
  <div
    class="player-shell glass-panel z-30 mx-auto w-full max-w-5xl border border-white/12 bg-black/72 shadow-[0_24px_80px_rgba(0,0,0,0.42)] backdrop-blur-2xl transition md:sticky md:top-4 lg:top-6 xl:top-8"
    :class="
      playback.isFullscreen.value
        ? 'overflow-visible rounded-none border-transparent shadow-none'
        : 'overflow-hidden rounded-[2rem] sm:rounded-[2.5rem]'
    "
    data-player-shell
    @mouseenter="playback.handlePlayerPointerEnter"
    @mouseleave="playback.handlePlayerPointerLeave"
    @mousemove="playback.handlePlayerInteraction"
    @pointermove="playback.handlePlayerInteraction"
    @pointerdown="playback.handlePlayerInteraction"
    @click="playback.handlePlayerInteraction"
    @keydown="playback.handlePlayerInteraction"
    @touchstart.passive="playback.handlePlayerInteraction"
    @focusin="playback.handlePlayerFocusIn"
    @focusout="playback.handlePlayerFocusOut"
  >
    <div
      class="player-video-frame relative bg-black"
      :class="playback.isFullscreen.value ? 'h-full min-h-screen w-full overflow-visible rounded-none' : 'aspect-video'"
    >
      <video
        :ref="playback.setVideoElement"
        class="player-video h-full w-full bg-black object-contain"
        :class="playback.isFullscreen.value ? 'rounded-none' : ''"
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

      <div
        class="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/78 via-black/15 to-black/45 transition-opacity duration-300"
        :class="playback.controlsVisible.value ? 'opacity-100' : 'opacity-0'"
      ></div>

      <div
        class="absolute inset-0 flex flex-col justify-between p-4 transition-opacity duration-300 sm:p-6"
        :class="playback.controlsVisible.value ? 'pointer-events-auto opacity-100' : 'pointer-events-none opacity-0'"
      >
        <div class="flex items-start justify-between gap-3 sm:gap-4">
          <div class="min-w-0">
            <p class="text-[11px] uppercase tracking-[0.28em] text-white/42 sm:text-xs">Now Playing</p>
            <div v-if="playback.selectedChannel.value" class="mt-3 flex items-center gap-3">
              <img
                v-if="playback.selectedChannel.value.tvg_logo"
                :src="playback.selectedChannel.value.tvg_logo"
                :alt="playback.selectedChannel.value.name"
                class="h-11 w-11 rounded-2xl bg-white/8 object-contain p-2 sm:h-12 sm:w-12"
              />
              <div
                v-else
                class="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/10 sm:h-12 sm:w-12"
              >
                <Tv class="h-5 w-5 text-white/68 sm:h-6 sm:w-6" />
              </div>
              <div class="min-w-0">
                <h3 class="truncate text-lg font-semibold text-white sm:text-2xl">
                  {{ playback.selectedChannel.value.name }}
                </h3>
                <p class="truncate text-sm text-white/56">
                  {{ playback.selectedChannel.value.group_title ?? 'Ungrouped' }}
                </p>
              </div>
            </div>
            <div v-else class="mt-3">
              <h3 class="text-lg font-semibold text-white sm:text-2xl">No channel selected</h3>
              <p class="mt-2 max-w-md text-sm text-white/56">Choose a channel from the list to load a stream.</p>
            </div>
          </div>
          <div
            class="shrink-0 rounded-full border px-3 py-1 text-[11px] uppercase tracking-[0.24em] sm:text-xs"
            :class="
              playback.playbackState.value === 'error'
                ? 'border-rose-400/40 bg-rose-500/15 text-rose-100'
                : playback.playbackState.value === 'loading'
                  ? 'border-amber-300/35 bg-amber-400/10 text-amber-100'
                  : playback.playbackState.value === 'ready'
                    ? 'border-emerald-300/30 bg-emerald-400/10 text-emerald-100'
                    : 'border-white/12 bg-white/8 text-white/56'
            "
          >
            {{
              playback.playbackState.value === 'idle'
                ? 'Idle'
                : playback.playbackState.value === 'loading'
                  ? 'Loading'
                  : playback.playbackState.value === 'ready'
                    ? playback.isPlaying.value
                      ? 'Playing'
                      : 'Ready'
                    : 'Error'
            }}
          </div>
        </div>

        <div class="space-y-3">
          <p class="max-w-2xl text-sm leading-6 text-white/72 drop-shadow">
            {{ playback.playbackState.value === 'error' ? playback.playbackError.value : playback.playerStatusText.value }}
          </p>

          <div class="flex w-fit max-w-full items-center gap-3 rounded-full">
            <button
              class="player-control-button tv-focus-card flex h-12 w-12 items-center justify-center rounded-full text-white transition disabled:cursor-not-allowed disabled:opacity-40 sm:h-14 sm:w-14"
              :disabled="!playback.selectedChannel.value || playback.playbackState.value === 'loading'"
              @click.stop="playback.togglePlayback"
            >
              <Pause v-if="playback.isPlaying.value" class="h-5 w-5 sm:h-6 sm:w-6" />
              <Play v-else class="ml-0.5 h-5 w-5 sm:h-6 sm:w-6" />
            </button>
            <button
              class="player-control-button tv-focus-card flex h-12 w-12 items-center justify-center rounded-full text-white transition disabled:cursor-not-allowed disabled:opacity-40 sm:h-14 sm:w-14"
              :disabled="!playback.selectedChannel.value"
              @click.stop="playback.toggleMute"
            >
              <VolumeX v-if="playback.isMuted.value" class="h-5 w-5 sm:h-6 sm:w-6" />
              <Volume2 v-else class="h-5 w-5 sm:h-6 sm:w-6" />
            </button>
            <button
              class="player-control-button tv-focus-card flex h-12 w-12 items-center justify-center rounded-full text-white transition disabled:cursor-not-allowed disabled:opacity-40 sm:h-14 sm:w-14"
              :disabled="!playback.selectedChannel.value"
              @click.stop="playback.toggleFullscreen"
            >
              <Maximize class="h-5 w-5 sm:h-6 sm:w-6" />
            </button>
            <div
              class="hidden min-h-12 items-center rounded-full border border-white/14 bg-black/46 px-4 text-sm text-white/72 shadow-[0_12px_32px_rgba(0,0,0,0.32)] backdrop-blur-xl sm:flex"
            >
              <LoaderCircle
                v-if="playback.playbackState.value === 'loading'"
                class="mr-2 h-4 w-4 animate-spin text-amber-100"
              />
              <span>
                {{
                  playback.playbackState.value === 'idle'
                    ? 'Select a channel'
                    : playback.playbackState.value === 'loading'
                      ? 'Loading stream'
                      : playback.playbackState.value === 'error'
                        ? 'Playback error'
                        : playback.isFullscreen.value
                          ? 'Fullscreen active'
                          : 'Player ready'
                }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.player-control-button {
  border: 1px solid rgb(255 255 255 / 0.24);
  background: rgb(0 0 0 / 0.68);
  box-shadow:
    0 12px 32px rgb(0 0 0 / 0.45),
    inset 0 1px 0 rgb(255 255 255 / 0.12);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
}

.player-control-button:hover,
.player-control-button:focus-visible {
  background: rgb(16 16 18 / 0.78);
}

.player-shell:fullscreen {
  border: 0;
  border-radius: 0;
  box-shadow: none;
  overflow: visible;
}

.player-shell:fullscreen .player-video-frame,
.player-shell:fullscreen video {
  border-radius: 0;
  overflow: visible;
}

.player-shell:-webkit-full-screen {
  border: 0;
  border-radius: 0;
  box-shadow: none;
  overflow: visible;
}

.player-shell:-webkit-full-screen .player-video-frame,
.player-shell:-webkit-full-screen video {
  border-radius: 0;
  overflow: visible;
}
</style>
