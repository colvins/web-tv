<script setup lang="ts">
import { computed, ref } from 'vue'
import { Check, ChevronDown, Copy, LoaderCircle, Maximize, Pause, Play, Tv, Volume2, VolumeX } from 'lucide-vue-next'

import type { LivePlayback } from '@/composables/useLivePlayback'

const props = defineProps<{
  playback: LivePlayback
  compact?: boolean
}>()

const errorBadgeText = computed(() => {
  switch (props.playback.playbackErrorCategory.value) {
    case 'autoplay_blocked':
      return 'Autoplay blocked'
    case 'unsupported_format':
      return 'Unsupported format'
    case 'hls_manifest_error':
      return 'Manifest error'
    case 'hls_network_error':
      return 'Network error'
    case 'hls_media_error':
      return 'Media error'
    case 'native_media_error':
      return 'Browser media error'
    case 'stream_load_error':
      return 'Stream load error'
    case 'unknown_error':
      return 'Unknown error'
    default:
      return 'Playback error'
  }
})

const copyState = ref<'idle' | 'done' | 'failed'>('idle')

const diagnosticsReason = computed(() => props.playback.playbackError.value || props.playback.playbackErrorTechnical.value)

const diagnosticsLines = computed(() => {
  const lines = [
    `Channel: ${props.playback.selectedChannel.value?.name ?? 'Unknown'}`,
    `Group: ${props.playback.selectedChannel.value?.group_title ?? 'Ungrouped'}`,
    `Stream host: ${props.playback.streamHost.value}`,
    `Error category: ${props.playback.playbackErrorCategory.value ?? 'unknown_error'}`,
    `Reason: ${diagnosticsReason.value || 'Unknown playback error'}`,
    `Stream type: ${props.playback.streamTypeGuess.value}`,
    `native_hls_supported: ${props.playback.nativeHlsSupported.value}`,
    `hls_js_supported: ${props.playback.hlsJsSupported.value}`,
  ]

  if (props.playback.nativeVideoError.value) {
    lines.push(`Native video error code: ${props.playback.nativeVideoError.value.code}`)
    lines.push(`Native video error message: ${props.playback.nativeVideoError.value.message}`)
  }

  if (props.playback.hlsError.value?.type) {
    lines.push(`HLS error type: ${props.playback.hlsError.value.type}`)
  }

  if (props.playback.hlsError.value?.details) {
    lines.push(`HLS error details: ${props.playback.hlsError.value.details}`)
  }

  return lines.join('\n')
})

async function copyDiagnostics() {
  try {
    await navigator.clipboard.writeText(diagnosticsLines.value)
    copyState.value = 'done'
  } catch {
    copyState.value = 'failed'
  }

  window.setTimeout(() => {
    copyState.value = 'idle'
  }, 1600)
}
</script>

<template>
  <div
    class="player-shell glass-panel mx-auto w-full border border-white/12 bg-black/72 shadow-[0_24px_80px_rgba(0,0,0,0.42)] backdrop-blur-2xl transition-all duration-300"
    :class="
      playback.isFullscreen.value
        ? 'overflow-visible rounded-none border-transparent shadow-none'
        : [
            'overflow-hidden rounded-[2rem] sm:rounded-[2.5rem]',
            compact ? 'md:max-w-3xl xl:max-w-4xl' : 'max-w-5xl',
          ]
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
      class="player-video-frame relative bg-black transition-all duration-300"
      :class="
        playback.isFullscreen.value
          ? 'h-full min-h-screen w-full overflow-visible rounded-none'
          : compact
            ? 'aspect-video md:aspect-[16/6.5] xl:aspect-[16/6]'
            : 'aspect-video'
      "
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

          <div
            v-if="playback.playbackState.value === 'error'"
            class="flex w-fit max-w-full flex-wrap items-center gap-2 rounded-full border border-rose-400/22 bg-rose-500/10 px-3 py-2 text-xs text-rose-100/92 shadow-[0_12px_32px_rgba(0,0,0,0.24)] backdrop-blur-xl"
          >
            <span class="rounded-full border border-rose-300/24 bg-rose-400/12 px-2 py-0.5 uppercase tracking-[0.2em] text-[10px]">
              {{ errorBadgeText }}
            </span>
            <span class="text-rose-50/78">
              {{ playback.playbackErrorTechnical.value }}
            </span>
          </div>

          <details
            v-if="playback.playbackState.value === 'error'"
            class="diagnostics-panel max-w-md rounded-[1.25rem] border border-white/10 bg-black/42 p-3 text-xs text-white/78 shadow-[0_12px_36px_rgba(0,0,0,0.24)] backdrop-blur-xl"
          >
            <summary class="flex cursor-pointer list-none items-center justify-between gap-3">
              <div class="min-w-0">
                <p class="truncate font-medium text-white">Playback diagnostics</p>
                <p class="truncate text-[11px] text-white/48">{{ playback.streamHost.value }}</p>
              </div>
              <ChevronDown class="diagnostics-chevron h-4 w-4 shrink-0 text-white/56 transition-transform duration-200" />
            </summary>

            <div class="mt-3 space-y-3 border-t border-white/8 pt-3">
              <div class="grid grid-cols-[auto,1fr] gap-x-3 gap-y-2 leading-5">
                <span class="text-white/42">Category</span>
                <span class="break-words text-white/86">{{ playback.playbackErrorCategory.value ?? 'unknown_error' }}</span>

                <span class="text-white/42">Reason</span>
                <span class="break-words text-white/86">{{ diagnosticsReason }}</span>

                <span class="text-white/42">Channel</span>
                <span class="break-words text-white/86">{{ playback.selectedChannel.value?.name ?? 'Unknown' }}</span>

                <span class="text-white/42">Group</span>
                <span class="break-words text-white/86">{{ playback.selectedChannel.value?.group_title ?? 'Ungrouped' }}</span>

                <span class="text-white/42">Stream type</span>
                <span class="break-words text-white/86">{{ playback.streamTypeGuess.value }}</span>

                <span class="text-white/42">Native HLS</span>
                <span class="break-words text-white/86">{{ playback.nativeHlsSupported.value }}</span>

                <span class="text-white/42">hls.js</span>
                <span class="break-words text-white/86">{{ playback.hlsJsSupported.value }}</span>

                <template v-if="playback.nativeVideoError.value">
                  <span class="text-white/42">Video error</span>
                  <span class="break-words text-white/86">
                    {{ playback.nativeVideoError.value.code }}
                    <span class="text-white/54">· {{ playback.nativeVideoError.value.message }}</span>
                  </span>
                </template>

                <template v-if="playback.hlsError.value?.type">
                  <span class="text-white/42">HLS type</span>
                  <span class="break-words text-white/86">{{ playback.hlsError.value.type }}</span>
                </template>

                <template v-if="playback.hlsError.value?.details">
                  <span class="text-white/42">HLS details</span>
                  <span class="break-words text-white/86">{{ playback.hlsError.value.details }}</span>
                </template>
              </div>

              <button
                class="diagnostics-copy-button tv-focus-card inline-flex min-h-10 items-center gap-2 rounded-full border border-white/12 bg-white/8 px-3 py-2 text-xs text-white/86 transition"
                type="button"
                @click.stop="copyDiagnostics"
              >
                <Check v-if="copyState === 'done'" class="h-4 w-4" />
                <Copy v-else class="h-4 w-4" />
                <span>
                  {{
                    copyState === 'done'
                      ? 'Copied'
                      : copyState === 'failed'
                        ? 'Copy failed'
                        : 'Copy diagnostics'
                  }}
                </span>
              </button>
            </div>
          </details>

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

.diagnostics-panel[open] .diagnostics-chevron {
  transform: rotate(180deg);
}

.diagnostics-copy-button:hover,
.diagnostics-copy-button:focus-visible {
  background: rgb(255 255 255 / 0.12);
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
