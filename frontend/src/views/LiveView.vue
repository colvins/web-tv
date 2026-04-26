<script setup lang="ts">
import Hls from 'hls.js'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  LoaderCircle,
  Maximize,
  Pause,
  Play,
  Search,
  SlidersHorizontal,
  Tv,
  Volume2,
  VolumeX,
} from 'lucide-vue-next'
import { NButton, NInput, NSwitch, useMessage } from 'naive-ui'

import {
  listLiveChannels,
  listLiveGroups,
  updateLiveChannel,
  type LiveChannel,
  type LiveChannelGroup,
} from '@/api/sourceConfigs'
import { ApiError } from '@/api/client'

type PlaybackState = 'idle' | 'loading' | 'ready' | 'error'
type FullscreenCapableVideo = HTMLVideoElement & {
  webkitEnterFullscreen?: () => void
  webkitDisplayingFullscreen?: boolean
}

const message = useMessage()
const groups = ref<LiveChannelGroup[]>([])
const channels = ref<LiveChannel[]>([])
const selectedGroupId = ref<string | null>(null)
const query = ref('')
const loading = ref(false)
const togglingIds = ref<Set<string>>(new Set())
const selectedChannel = ref<LiveChannel | null>(null)
const playbackState = ref<PlaybackState>('idle')
const playbackError = ref('')
const isPlaying = ref(false)
const isMuted = ref(false)
const isFullscreen = ref(false)
const playerStatusText = ref('Select a channel to start playback.')
const videoEl = ref<HTMLVideoElement | null>(null)
const controlsVisible = ref(true)
const playerHovering = ref(false)
const playerFocused = ref(false)

let hls: Hls | null = null
let searchTimer: number | undefined
let controlsHideTimer: number | undefined

const selectedGroupName = computed(
  () => groups.value.find((group) => group.id === selectedGroupId.value)?.name ?? 'All Channels',
)

const selectedChannelId = computed(() => selectedChannel.value?.id ?? null)
const shouldPinControlsVisible = computed(() =>
  playbackState.value === 'idle' ||
  playbackState.value === 'loading' ||
  playbackState.value === 'error' ||
  !selectedChannel.value,
)

function isHlsStream(url: string) {
  return url.toLowerCase().includes('.m3u8')
}

function clearControlsHideTimer() {
  window.clearTimeout(controlsHideTimer)
  controlsHideTimer = undefined
}

function syncControlsVisibility() {
  if (shouldPinControlsVisible.value || playerHovering.value || playerFocused.value || !isPlaying.value) {
    controlsVisible.value = true
    clearControlsHideTimer()
    return
  }

  clearControlsHideTimer()
  controlsHideTimer = window.setTimeout(() => {
    if (!playerHovering.value && !playerFocused.value && isPlaying.value && playbackState.value === 'ready') {
      controlsVisible.value = false
    }
  }, 2800)
}

function revealControls() {
  controlsVisible.value = true
  syncControlsVisibility()
}

function destroyPlayer() {
  clearControlsHideTimer()
  hls?.destroy()
  hls = null

  const video = videoEl.value
  if (!video) return
  video.pause()
  video.removeAttribute('src')
  video.load()
}

function setPlaybackError(description: string) {
  playbackState.value = 'error'
  playbackError.value = description
  playerStatusText.value = description
  isPlaying.value = false
  revealControls()
}

async function attemptPlay() {
  const video = videoEl.value
  if (!video) return

  revealControls()

  try {
    await video.play()
  } catch {
    playbackState.value = 'ready'
    playerStatusText.value = 'Ready to play.'
    isPlaying.value = false
    revealControls()
  }
}

async function loadSelectedChannel(channel: LiveChannel) {
  const video = videoEl.value
  if (!video) return

  destroyPlayer()
  selectedChannel.value = { ...channel }
  playbackState.value = 'loading'
  playbackError.value = ''
  playerStatusText.value = 'Loading stream...'
  controlsVisible.value = true
  video.muted = isMuted.value

  const streamUrl = channel.stream_url

  if (isHlsStream(streamUrl)) {
    if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = streamUrl
      await attemptPlay()
      return
    }

    if (Hls.isSupported()) {
      hls = new Hls()
      hls.attachMedia(video)
      hls.on(Hls.Events.MEDIA_ATTACHED, () => {
        hls?.loadSource(streamUrl)
      })
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        void attemptPlay()
      })
      hls.on(Hls.Events.ERROR, (_event, data) => {
        if (data.fatal) {
          setPlaybackError('Unable to play this HLS stream.')
        }
      })
      return
    }

    setPlaybackError('HLS playback is not supported in this browser.')
    return
  }

  video.src = streamUrl
  await attemptPlay()
}

async function selectChannel(channel: LiveChannel) {
  await loadSelectedChannel(channel)
}

async function loadLiveData() {
  loading.value = true
  try {
    const [groupResult, channelResult] = await Promise.all([
      listLiveGroups(),
      listLiveChannels({ group_id: selectedGroupId.value ?? undefined, q: query.value || undefined }),
    ])
    groups.value = groupResult
    channels.value = channelResult

    if (selectedChannel.value) {
      const latestSelected = channelResult.find((channel) => channel.id === selectedChannel.value?.id)
      if (latestSelected) {
        selectedChannel.value = { ...latestSelected }
      }
    }
  } catch (error) {
    message.error(error instanceof ApiError ? error.message : 'Unable to load live channels')
  } finally {
    loading.value = false
  }
}

async function toggleChannel(channel: LiveChannel, enabled: boolean) {
  const previous = channel.enabled
  channel.enabled = enabled
  togglingIds.value = new Set(togglingIds.value).add(channel.id)
  try {
    const updated = await updateLiveChannel(channel.id, enabled)
    channels.value = channels.value.map((item) => (item.id === updated.id ? updated : item))
    if (selectedChannel.value?.id === updated.id) {
      selectedChannel.value = { ...selectedChannel.value, ...updated }
    }
  } catch (error) {
    channel.enabled = previous
    message.error(error instanceof ApiError ? error.message : 'Unable to update channel')
  } finally {
    const next = new Set(togglingIds.value)
    next.delete(channel.id)
    togglingIds.value = next
  }
}

async function togglePlayback() {
  const video = videoEl.value
  if (!video || !selectedChannel.value) return

  revealControls()

  if (video.paused) {
    await attemptPlay()
    return
  }

  video.pause()
}

function toggleMute() {
  const video = videoEl.value
  if (!video) return

  revealControls()
  video.muted = !video.muted
  isMuted.value = video.muted
}

async function toggleFullscreen() {
  const video = videoEl.value as FullscreenCapableVideo | null
  const container = video?.closest('[data-player-shell]') as HTMLElement | null
  if (!video || !container) return

  revealControls()

  if (document.fullscreenElement) {
    await document.exitFullscreen()
    return
  }

  try {
    if (typeof container.requestFullscreen === 'function') {
      await container.requestFullscreen()
      return
    }
  } catch {
    // Fall through to the iOS video fullscreen API.
  }

  if (typeof video.webkitEnterFullscreen === 'function') {
    video.webkitEnterFullscreen()
  }
}

function handlePlaying() {
  playbackState.value = 'ready'
  playerStatusText.value = 'Now playing.'
  isPlaying.value = true
  syncControlsVisibility()
}

function handlePause() {
  isPlaying.value = false
  if (playbackState.value !== 'error') {
    playerStatusText.value = 'Playback paused.'
  }
  revealControls()
}

function handleWaiting() {
  if (!selectedChannel.value) return
  playbackState.value = 'loading'
  playerStatusText.value = 'Buffering stream...'
  revealControls()
}

function handleCanPlay() {
  if (playbackState.value === 'error') return
  playbackState.value = 'ready'
  if (!isPlaying.value) {
    playerStatusText.value = 'Ready to play.'
  }
  syncControlsVisibility()
}

function handleVideoError() {
  setPlaybackError('Unable to load this channel stream.')
}

function handleVolumeChange() {
  isMuted.value = !!videoEl.value?.muted
}

function syncFullscreenState() {
  const video = videoEl.value as FullscreenCapableVideo | null
  const webkitFullscreenElement = (document as Document & { webkitFullscreenElement?: Element | null })
    .webkitFullscreenElement
  isFullscreen.value = !!document.fullscreenElement || !!webkitFullscreenElement || !!video?.webkitDisplayingFullscreen
  revealControls()
}

function handlePlayerPointerEnter() {
  playerHovering.value = true
  revealControls()
}

function handlePlayerPointerLeave() {
  playerHovering.value = false
  syncControlsVisibility()
}

function handlePlayerInteraction() {
  revealControls()
}

function handlePlayerFocusIn() {
  playerFocused.value = true
  revealControls()
}

function handlePlayerFocusOut(event: FocusEvent) {
  const currentTarget = event.currentTarget as HTMLElement | null
  const relatedTarget = event.relatedTarget as Node | null
  if (currentTarget?.contains(relatedTarget)) return
  playerFocused.value = false
  syncControlsVisibility()
}

watch(query, () => {
  window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(loadLiveData, 250)
})

watch(selectedGroupId, loadLiveData)
watch([shouldPinControlsVisible, isPlaying], syncControlsVisibility)

onMounted(() => {
  document.addEventListener('fullscreenchange', syncFullscreenState)
  document.addEventListener('webkitfullscreenchange', syncFullscreenState as EventListener)
  void loadLiveData()
})

onBeforeUnmount(() => {
  document.removeEventListener('fullscreenchange', syncFullscreenState)
  document.removeEventListener('webkitfullscreenchange', syncFullscreenState as EventListener)
  window.clearTimeout(searchTimer)
  clearControlsHideTimer()
  destroyPlayer()
})
</script>

<template>
  <section class="grid gap-5 pb-24 sm:gap-6 sm:pb-28">
    <div class="glass-panel rounded-[2rem] p-5 sm:rounded-[2.5rem] sm:p-8">
      <div class="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p class="text-sm uppercase tracking-[0.28em] text-white/42">Live TV</p>
          <h2 class="mt-3 text-3xl font-semibold text-white sm:text-5xl xl:text-6xl">{{ selectedGroupName }}</h2>
          <p class="mt-3 max-w-3xl text-sm leading-6 text-white/58">
            Browse imported channels and play a selected stream directly in this page.
          </p>
        </div>
        <div class="flex w-full flex-col gap-3 sm:flex-row xl:w-auto">
          <NInput
            v-model:value="query"
            round
            clearable
            placeholder="Search channels"
            class="w-full sm:min-w-72 xl:w-80"
          >
            <template #prefix><Search class="h-4 w-4 text-white/42" /></template>
          </NInput>
          <NButton round secondary :loading="loading" class="min-h-12" @click="loadLiveData">
            <template #icon><SlidersHorizontal class="h-4 w-4" /></template>
            Refresh
          </NButton>
        </div>
      </div>
    </div>

    <div class="grid gap-5 xl:grid-cols-[minmax(0,1.1fr)_minmax(22rem,0.9fr)] xl:items-start">
      <div
        class="glass-panel border border-white/10 bg-black/40 transition"
        :class="isFullscreen ? 'overflow-visible rounded-none border-transparent shadow-none' : 'overflow-hidden rounded-[2rem] sm:rounded-[2.5rem]'"
        data-player-shell
        @mouseenter="handlePlayerPointerEnter"
        @mouseleave="handlePlayerPointerLeave"
        @mousemove="handlePlayerInteraction"
        @click="handlePlayerInteraction"
        @touchstart.passive="handlePlayerInteraction"
        @focusin="handlePlayerFocusIn"
        @focusout="handlePlayerFocusOut"
      >
        <div class="relative bg-black" :class="isFullscreen ? 'h-full min-h-screen w-full' : 'aspect-video'">
          <video
            ref="videoEl"
            class="h-full w-full bg-black object-contain"
            :class="isFullscreen ? 'rounded-none' : ''"
            playsinline
            controlslist="nodownload noplaybackrate"
            preload="none"
            @canplay="handleCanPlay"
            @error="handleVideoError"
            @pause="handlePause"
            @playing="handlePlaying"
            @volumechange="handleVolumeChange"
            @waiting="handleWaiting"
          ></video>

          <div
            class="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/78 via-black/15 to-black/45 transition-opacity duration-300"
            :class="controlsVisible ? 'opacity-100' : 'opacity-0'"
          ></div>

          <div
            class="absolute inset-0 flex flex-col justify-between p-4 transition-opacity duration-300 sm:p-6"
            :class="controlsVisible ? 'pointer-events-auto opacity-100' : 'pointer-events-none opacity-0'"
          >
            <div class="flex items-start justify-between gap-3 sm:gap-4">
              <div class="min-w-0">
                <p class="text-[11px] uppercase tracking-[0.28em] text-white/42 sm:text-xs">Now Playing</p>
                <div v-if="selectedChannel" class="mt-3 flex items-center gap-3">
                  <img
                    v-if="selectedChannel.tvg_logo"
                    :src="selectedChannel.tvg_logo"
                    :alt="selectedChannel.name"
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
                      {{ selectedChannel.name }}
                    </h3>
                    <p class="truncate text-sm text-white/56">
                      {{ selectedChannel.group_title ?? 'Ungrouped' }}
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
                  playbackState === 'error'
                    ? 'border-rose-400/40 bg-rose-500/15 text-rose-100'
                    : playbackState === 'loading'
                      ? 'border-amber-300/35 bg-amber-400/10 text-amber-100'
                      : playbackState === 'ready'
                        ? 'border-emerald-300/30 bg-emerald-400/10 text-emerald-100'
                        : 'border-white/12 bg-white/8 text-white/56'
                "
              >
                {{
                  playbackState === 'idle'
                    ? 'Idle'
                    : playbackState === 'loading'
                      ? 'Loading'
                      : playbackState === 'ready'
                        ? isPlaying
                          ? 'Playing'
                          : 'Ready'
                        : 'Error'
                }}
              </div>
            </div>

            <div class="space-y-3 sm:space-y-4">
              <p class="max-w-2xl text-sm leading-6 text-white/72">
                {{ playbackState === 'error' ? playbackError : playerStatusText }}
              </p>

              <div class="flex flex-wrap items-center gap-3">
                <button
                  class="tv-focus-card flex h-12 w-12 items-center justify-center rounded-full border border-white/14 bg-white/12 text-white transition disabled:cursor-not-allowed disabled:opacity-40 sm:h-14 sm:w-14"
                  :disabled="!selectedChannel || playbackState === 'loading'"
                  @click.stop="togglePlayback"
                >
                  <Pause v-if="isPlaying" class="h-5 w-5 sm:h-6 sm:w-6" />
                  <Play v-else class="ml-0.5 h-5 w-5 sm:h-6 sm:w-6" />
                </button>
                <button
                  class="tv-focus-card flex h-12 w-12 items-center justify-center rounded-full border border-white/14 bg-white/12 text-white transition disabled:cursor-not-allowed disabled:opacity-40 sm:h-14 sm:w-14"
                  :disabled="!selectedChannel"
                  @click.stop="toggleMute"
                >
                  <VolumeX v-if="isMuted" class="h-5 w-5 sm:h-6 sm:w-6" />
                  <Volume2 v-else class="h-5 w-5 sm:h-6 sm:w-6" />
                </button>
                <button
                  class="tv-focus-card flex h-12 w-12 items-center justify-center rounded-full border border-white/14 bg-white/12 text-white transition disabled:cursor-not-allowed disabled:opacity-40 sm:h-14 sm:w-14"
                  :disabled="!selectedChannel"
                  @click.stop="toggleFullscreen"
                >
                  <Maximize class="h-5 w-5 sm:h-6 sm:w-6" />
                </button>
                <div
                  class="flex min-h-12 min-w-[11.5rem] flex-1 items-center rounded-full border border-white/12 bg-black/18 px-4 text-sm text-white/60 sm:min-h-14 sm:min-w-[13rem] sm:flex-none"
                >
                  <LoaderCircle
                    v-if="playbackState === 'loading'"
                    class="mr-2 h-4 w-4 animate-spin text-amber-100"
                  />
                  <span>
                    {{
                      playbackState === 'idle'
                        ? 'Select a channel'
                        : playbackState === 'loading'
                          ? 'Loading stream'
                          : playbackState === 'error'
                            ? 'Playback error'
                            : isFullscreen
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

      <div class="grid gap-4 pb-6 xl:content-start xl:pb-0">
        <div class="-mx-1 overflow-x-auto px-1 pb-1 [scrollbar-width:none]">
          <div class="flex min-w-max gap-3 xl:flex-wrap">
            <button
              class="tv-focus-card shrink-0 rounded-full border px-5 py-3 text-sm transition sm:px-6 sm:py-3.5"
              :class="
                selectedGroupId === null
                  ? 'border-aurora/40 bg-aurora/18 text-white'
                  : 'border-white/10 bg-white/6 text-white/62'
              "
              @click="selectedGroupId = null"
            >
              All
            </button>
            <button
              v-for="group in groups"
              :key="group.id"
              class="tv-focus-card shrink-0 rounded-full border px-5 py-3 text-sm transition sm:px-6 sm:py-3.5"
              :class="
                selectedGroupId === group.id
                  ? 'border-aurora/40 bg-aurora/18 text-white'
                  : 'border-white/10 bg-white/6 text-white/62'
              "
              @click="selectedGroupId = group.id"
            >
              {{ group.name }}
              <span class="ml-2 text-white/42">{{ group.channel_count }}</span>
            </button>
          </div>
        </div>

        <div v-if="loading && channels.length === 0" class="grid gap-4">
          <div v-for="index in 6" :key="index" class="glass-panel h-40 animate-pulse rounded-[2rem]"></div>
        </div>

        <div
          v-else-if="channels.length === 0"
          class="glass-panel flex min-h-72 items-end rounded-[2rem] p-6 sm:rounded-[2.5rem] sm:p-10"
        >
          <div>
            <p class="text-sm uppercase tracking-[0.28em] text-white/42">No Channels</p>
            <h2 class="mt-3 max-w-2xl text-2xl font-semibold sm:text-5xl">
              Import and extract a live M3U source first.
            </h2>
          </div>
        </div>

        <div v-else class="grid gap-4">
          <article
            v-for="channel in channels"
            :key="channel.id"
            tabindex="0"
            class="tv-focus-card glass-panel flex min-h-44 cursor-pointer flex-col overflow-hidden rounded-[1.75rem] border transition sm:rounded-[2rem]"
            :class="
              selectedChannelId === channel.id
                ? 'border-aurora/40 bg-white/10'
                : 'border-white/10 bg-transparent hover:border-white/20'
            "
            @click="selectChannel(channel)"
            @keydown.enter.prevent="selectChannel(channel)"
            @keydown.space.prevent="selectChannel(channel)"
          >
            <div class="flex items-center gap-4 p-5 sm:p-6">
              <div class="flex h-16 w-16 shrink-0 items-center justify-center rounded-[1.35rem] bg-white/8">
                <img
                  v-if="channel.tvg_logo"
                  :src="channel.tvg_logo"
                  :alt="channel.name"
                  class="max-h-12 max-w-[80%] object-contain"
                  loading="lazy"
                />
                <Tv v-else class="h-7 w-7 text-white/62" />
              </div>
              <div class="min-w-0 flex-1">
                <div class="flex items-start justify-between gap-4">
                  <div class="min-w-0">
                    <h3 class="line-clamp-2 text-lg font-semibold text-white">{{ channel.name }}</h3>
                    <p class="mt-1 truncate text-sm text-white/46">{{ channel.group_title ?? 'Ungrouped' }}</p>
                  </div>
                  <NSwitch
                    :value="channel.enabled"
                    :loading="togglingIds.has(channel.id)"
                    @click.stop
                    @update:value="(value) => toggleChannel(channel, value)"
                  />
                </div>
                <p class="mt-4 line-clamp-2 break-all font-mono text-xs leading-5 text-white/40">
                  {{ channel.stream_url }}
                </p>
              </div>
            </div>
          </article>
        </div>
      </div>
    </div>
  </section>
</template>
