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
const groupScroller = ref<HTMLElement | null>(null)
const controlsVisible = ref(true)
const playerHovering = ref(false)
const playerFocused = ref(false)
const groupDragging = ref(false)
const groupDragMoved = ref(false)

let hls: Hls | null = null
let searchTimer: number | undefined
let controlsHideTimer: number | undefined
let groupDragStartX = 0
let groupDragStartScrollLeft = 0

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
  const keepVisibleForHover = playerHovering.value && !isFullscreen.value
  if (shouldPinControlsVisible.value || keepVisibleForHover || playerFocused.value || !isPlaying.value) {
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

  const isLikelyIos = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)

  if (isLikelyIos && typeof video.webkitEnterFullscreen === 'function') {
    video.webkitEnterFullscreen()
    return
  }

  try {
    if (typeof container.requestFullscreen === 'function') {
      await container.requestFullscreen()
      return
    }
  } catch {
    // Fall through to video fullscreen when a browser blocks container fullscreen.
  }

  if (typeof video.requestFullscreen === 'function') {
    await video.requestFullscreen()
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

function selectGroup(groupId: string | null) {
  if (groupDragMoved.value) return
  selectedGroupId.value = groupId
}

function startGroupDrag(event: PointerEvent) {
  if (event.pointerType === 'touch') return
  const scroller = groupScroller.value
  if (!scroller) return
  groupDragging.value = true
  groupDragMoved.value = false
  groupDragStartX = event.clientX
  groupDragStartScrollLeft = scroller.scrollLeft
  scroller.setPointerCapture(event.pointerId)
}

function moveGroupDrag(event: PointerEvent) {
  if (!groupDragging.value || event.pointerType === 'touch') return
  const scroller = groupScroller.value
  if (!scroller) return
  const deltaX = event.clientX - groupDragStartX
  if (Math.abs(deltaX) > 4) {
    groupDragMoved.value = true
  }
  scroller.scrollLeft = groupDragStartScrollLeft - deltaX
}

function endGroupDrag(event: PointerEvent) {
  if (!groupDragging.value) return
  groupDragging.value = false
  if (groupScroller.value?.hasPointerCapture(event.pointerId)) {
    groupScroller.value.releasePointerCapture(event.pointerId)
  }
  window.setTimeout(() => {
    groupDragMoved.value = false
  }, 0)
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
watch([shouldPinControlsVisible, isPlaying, isFullscreen], syncControlsVisibility)

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

    <div class="grid gap-5 xl:grid-cols-[minmax(24rem,0.9fr)_minmax(0,1.1fr)] xl:items-start">
      <div
        class="player-shell glass-panel border border-white/10 bg-black/40 transition md:sticky md:top-6 xl:top-8"
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

            <div class="space-y-3">
              <p class="max-w-2xl text-sm leading-6 text-white/72 drop-shadow">
                {{ playbackState === 'error' ? playbackError : playerStatusText }}
              </p>

              <div class="flex w-fit max-w-full items-center gap-3 rounded-full">
                <button
                  class="tv-focus-card flex h-12 w-12 items-center justify-center rounded-full border border-white/20 bg-black/58 text-white shadow-[0_12px_32px_rgba(0,0,0,0.38)] backdrop-blur-xl transition disabled:cursor-not-allowed disabled:opacity-40 sm:h-14 sm:w-14"
                  :disabled="!selectedChannel || playbackState === 'loading'"
                  @click.stop="togglePlayback"
                >
                  <Pause v-if="isPlaying" class="h-5 w-5 sm:h-6 sm:w-6" />
                  <Play v-else class="ml-0.5 h-5 w-5 sm:h-6 sm:w-6" />
                </button>
                <button
                  class="tv-focus-card flex h-12 w-12 items-center justify-center rounded-full border border-white/20 bg-black/58 text-white shadow-[0_12px_32px_rgba(0,0,0,0.38)] backdrop-blur-xl transition disabled:cursor-not-allowed disabled:opacity-40 sm:h-14 sm:w-14"
                  :disabled="!selectedChannel"
                  @click.stop="toggleMute"
                >
                  <VolumeX v-if="isMuted" class="h-5 w-5 sm:h-6 sm:w-6" />
                  <Volume2 v-else class="h-5 w-5 sm:h-6 sm:w-6" />
                </button>
                <button
                  class="tv-focus-card flex h-12 w-12 items-center justify-center rounded-full border border-white/20 bg-black/58 text-white shadow-[0_12px_32px_rgba(0,0,0,0.38)] backdrop-blur-xl transition disabled:cursor-not-allowed disabled:opacity-40 sm:h-14 sm:w-14"
                  :disabled="!selectedChannel"
                  @click.stop="toggleFullscreen"
                >
                  <Maximize class="h-5 w-5 sm:h-6 sm:w-6" />
                </button>
                <div
                  class="hidden min-h-12 items-center rounded-full border border-white/14 bg-black/46 px-4 text-sm text-white/72 shadow-[0_12px_32px_rgba(0,0,0,0.32)] backdrop-blur-xl sm:flex"
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
        <div
          ref="groupScroller"
          class="chip-scroller -mx-1 cursor-grab overflow-x-auto overscroll-x-contain px-1 pb-1 active:cursor-grabbing [scrollbar-width:none]"
          @pointerdown="startGroupDrag"
          @pointermove="moveGroupDrag"
          @pointerup="endGroupDrag"
          @pointercancel="endGroupDrag"
          @pointerleave="endGroupDrag"
        >
          <div class="flex min-w-max flex-nowrap gap-3">
            <button
              class="tv-focus-card shrink-0 rounded-full border px-5 py-3 text-sm transition sm:px-6 sm:py-3.5"
              :class="
                selectedGroupId === null
                  ? 'border-aurora/40 bg-aurora/18 text-white'
                  : 'border-white/10 bg-white/6 text-white/62'
              "
              @click="selectGroup(null)"
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
              @click="selectGroup(group.id)"
            >
              {{ group.name }}
              <span class="ml-2 text-white/42">{{ group.channel_count }}</span>
            </button>
          </div>
        </div>

        <div v-if="loading && channels.length === 0" class="grid grid-cols-2 gap-3 md:grid-cols-3 2xl:grid-cols-4">
          <div v-for="index in 8" :key="index" class="glass-panel aspect-square animate-pulse rounded-[1.5rem]"></div>
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

        <div v-else class="grid grid-cols-2 gap-3 md:grid-cols-3 2xl:grid-cols-4">
          <article
            v-for="channel in channels"
            :key="channel.id"
            tabindex="0"
            class="tv-focus-card glass-panel group flex aspect-square min-h-0 cursor-pointer flex-col overflow-hidden rounded-[1.35rem] border transition sm:rounded-[1.6rem]"
            :class="
              selectedChannelId === channel.id
                ? 'border-aurora/50 bg-aurora/12 shadow-[0_0_0_1px_rgba(120,220,255,0.12)]'
                : 'border-white/10 bg-white/[0.03] hover:border-white/20'
            "
            @click="selectChannel(channel)"
            @keydown.enter.prevent="selectChannel(channel)"
            @keydown.space.prevent="selectChannel(channel)"
          >
            <div class="flex h-full flex-col p-3 sm:p-4">
              <div class="flex min-h-0 flex-1 items-center justify-center rounded-[1.15rem] bg-white/7 p-3">
                <img
                  v-if="channel.tvg_logo"
                  :src="channel.tvg_logo"
                  :alt="channel.name"
                  class="max-h-16 max-w-[86%] object-contain sm:max-h-20"
                  loading="lazy"
                />
                <Tv v-else class="h-9 w-9 text-white/62 sm:h-10 sm:w-10" />
              </div>
              <div class="mt-3 min-w-0">
                <div class="flex items-start justify-between gap-2">
                  <div class="min-w-0">
                    <h3 class="line-clamp-2 text-sm font-semibold leading-5 text-white sm:text-base">
                      {{ channel.name }}
                    </h3>
                    <p class="mt-1 truncate text-xs text-white/46">{{ channel.group_title ?? 'Ungrouped' }}</p>
                  </div>
                  <NSwitch
                    :value="channel.enabled"
                    :loading="togglingIds.has(channel.id)"
                    @click.stop
                    @update:value="(value) => toggleChannel(channel, value)"
                  />
                </div>
                <p class="mt-2 truncate font-mono text-[10px] leading-4 text-white/22 opacity-0 transition group-hover:opacity-100">
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

<style scoped>
.chip-scroller::-webkit-scrollbar {
  display: none;
}

.player-shell:fullscreen {
  border: 0;
  border-radius: 0;
  box-shadow: none;
  overflow: visible;
}

.player-shell:fullscreen video {
  border-radius: 0;
}

.player-shell:-webkit-full-screen {
  border: 0;
  border-radius: 0;
  box-shadow: none;
  overflow: visible;
}

.player-shell:-webkit-full-screen video {
  border-radius: 0;
}
</style>
