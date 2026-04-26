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

const message = useMessage()
const groups = ref<LiveChannelGroup[]>([])
const channels = ref<LiveChannel[]>([])
const selectedGroupId = ref<string | null>(null)
const query = ref('')
const loading = ref(false)
const togglingIds = ref<Set<string>>(new Set())
const selectedChannelId = ref<string | null>(null)
const playbackState = ref<PlaybackState>('idle')
const playbackError = ref('')
const isPlaying = ref(false)
const isMuted = ref(false)
const isFullscreen = ref(false)
const playerStatusText = ref('Select a channel to start playback.')
const videoEl = ref<HTMLVideoElement | null>(null)

let hls: Hls | null = null
let searchTimer: number | undefined

const selectedGroupName = computed(
  () => groups.value.find((group) => group.id === selectedGroupId.value)?.name ?? 'All Channels',
)

const selectedChannel = computed(() => {
  if (!selectedChannelId.value) return null
  return channels.value.find((channel) => channel.id === selectedChannelId.value) ?? null
})

function isHlsStream(url: string) {
  return url.toLowerCase().includes('.m3u8')
}

function destroyPlayer() {
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
}

async function attemptPlay() {
  const video = videoEl.value
  if (!video) return

  try {
    await video.play()
  } catch {
    playbackState.value = 'ready'
    playerStatusText.value = 'Ready to play.'
    isPlaying.value = false
  }
}

async function loadSelectedChannel(channel: LiveChannel) {
  const video = videoEl.value
  if (!video) return

  destroyPlayer()
  selectedChannelId.value = channel.id
  playbackState.value = 'loading'
  playbackError.value = ''
  playerStatusText.value = 'Loading stream...'
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

    if (selectedChannelId.value && !channelResult.some((channel) => channel.id === selectedChannelId.value)) {
      selectedChannelId.value = null
      playbackState.value = 'idle'
      playbackError.value = ''
      playerStatusText.value = 'Select a channel to start playback.'
      destroyPlayer()
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

  if (video.paused) {
    await attemptPlay()
    return
  }

  video.pause()
}

function toggleMute() {
  const video = videoEl.value
  if (!video) return

  video.muted = !video.muted
  isMuted.value = video.muted
}

async function toggleFullscreen() {
  const container = videoEl.value?.closest('[data-player-shell]') as HTMLElement | null
  if (!container) return

  if (document.fullscreenElement) {
    await document.exitFullscreen()
    return
  }

  await container.requestFullscreen()
}

function handlePlaying() {
  playbackState.value = 'ready'
  playerStatusText.value = 'Now playing.'
  isPlaying.value = true
}

function handlePause() {
  isPlaying.value = false
  if (playbackState.value !== 'error') {
    playerStatusText.value = 'Playback paused.'
  }
}

function handleWaiting() {
  if (!selectedChannel.value) return
  playbackState.value = 'loading'
  playerStatusText.value = 'Buffering stream...'
}

function handleCanPlay() {
  if (playbackState.value === 'error') return
  playbackState.value = 'ready'
  if (!isPlaying.value) {
    playerStatusText.value = 'Ready to play.'
  }
}

function handleVideoError() {
  setPlaybackError('Unable to load this channel stream.')
}

function handleVolumeChange() {
  isMuted.value = !!videoEl.value?.muted
}

function syncFullscreenState() {
  isFullscreen.value = !!document.fullscreenElement
}

watch(query, () => {
  window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(loadLiveData, 250)
})

watch(selectedGroupId, loadLiveData)

onMounted(() => {
  document.addEventListener('fullscreenchange', syncFullscreenState)
  void loadLiveData()
})

onBeforeUnmount(() => {
  document.removeEventListener('fullscreenchange', syncFullscreenState)
  window.clearTimeout(searchTimer)
  destroyPlayer()
})
</script>

<template>
  <section class="grid gap-6">
    <div class="glass-panel rounded-[2.5rem] p-6 sm:p-8">
      <div class="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p class="text-sm uppercase tracking-[0.28em] text-white/42">Live TV</p>
          <h2 class="mt-3 text-4xl font-semibold text-white sm:text-6xl">{{ selectedGroupName }}</h2>
          <p class="mt-4 max-w-3xl text-sm leading-6 text-white/58">
            Browse imported channels and play a selected stream directly in this page.
          </p>
        </div>
        <div class="flex w-full flex-col gap-3 sm:flex-row xl:w-auto">
          <NInput v-model:value="query" round clearable placeholder="Search channels" class="min-w-72">
            <template #prefix><Search class="h-4 w-4 text-white/42" /></template>
          </NInput>
          <NButton round secondary :loading="loading" @click="loadLiveData">
            <template #icon><SlidersHorizontal class="h-4 w-4" /></template>
            Refresh
          </NButton>
        </div>
      </div>
    </div>

    <div class="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(22rem,0.85fr)] xl:items-start">
      <div class="glass-panel overflow-hidden rounded-[2.5rem]" data-player-shell>
        <div class="relative aspect-video bg-black">
          <video
            ref="videoEl"
            class="h-full w-full"
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

          <div class="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/72 via-black/12 to-black/42"></div>

          <div class="absolute inset-0 flex flex-col justify-between p-4 sm:p-6">
            <div class="flex items-start justify-between gap-4">
              <div class="min-w-0">
                <p class="text-xs uppercase tracking-[0.28em] text-white/42">Now Playing</p>
                <div v-if="selectedChannel" class="mt-3 flex items-center gap-3">
                  <img
                    v-if="selectedChannel.tvg_logo"
                    :src="selectedChannel.tvg_logo"
                    :alt="selectedChannel.name"
                    class="h-12 w-12 rounded-2xl bg-white/8 object-contain p-2"
                  />
                  <div v-else class="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/10">
                    <Tv class="h-6 w-6 text-white/68" />
                  </div>
                  <div class="min-w-0">
                    <h3 class="truncate text-xl font-semibold text-white sm:text-2xl">
                      {{ selectedChannel.name }}
                    </h3>
                    <p class="truncate text-sm text-white/56">
                      {{ selectedChannel.group_title ?? 'Ungrouped' }}
                    </p>
                  </div>
                </div>
                <div v-else class="mt-3">
                  <h3 class="text-xl font-semibold text-white sm:text-2xl">No channel selected</h3>
                  <p class="mt-2 text-sm text-white/56">Choose a channel from the list to load a stream.</p>
                </div>
              </div>
              <div
                class="rounded-full border px-3 py-1 text-xs uppercase tracking-[0.24em]"
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

            <div class="space-y-4">
              <p class="max-w-2xl text-sm text-white/72">
                {{ playbackState === 'error' ? playbackError : playerStatusText }}
              </p>

              <div class="flex flex-wrap items-center gap-3">
                <button
                  class="tv-focus-card flex h-12 w-12 items-center justify-center rounded-full border border-white/14 bg-white/10 text-white transition disabled:cursor-not-allowed disabled:opacity-40"
                  :disabled="!selectedChannel || playbackState === 'loading'"
                  @click="togglePlayback"
                >
                  <Pause v-if="isPlaying" class="h-5 w-5" />
                  <Play v-else class="ml-0.5 h-5 w-5" />
                </button>
                <button
                  class="tv-focus-card flex h-12 w-12 items-center justify-center rounded-full border border-white/14 bg-white/10 text-white transition disabled:cursor-not-allowed disabled:opacity-40"
                  :disabled="!selectedChannel"
                  @click="toggleMute"
                >
                  <VolumeX v-if="isMuted" class="h-5 w-5" />
                  <Volume2 v-else class="h-5 w-5" />
                </button>
                <button
                  class="tv-focus-card flex h-12 w-12 items-center justify-center rounded-full border border-white/14 bg-white/10 text-white transition disabled:cursor-not-allowed disabled:opacity-40"
                  :disabled="!selectedChannel"
                  @click="toggleFullscreen"
                >
                  <Maximize class="h-5 w-5" />
                </button>
                <div
                  class="flex min-h-12 min-w-[13rem] items-center rounded-full border border-white/12 bg-black/18 px-4 text-sm text-white/60"
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

      <div class="grid gap-3 overflow-x-auto pb-2 xl:content-start">
        <div class="flex gap-3 overflow-x-auto pb-1 xl:flex-wrap">
          <button
            class="tv-focus-card shrink-0 rounded-full border px-5 py-3 text-sm transition"
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
            class="tv-focus-card shrink-0 rounded-full border px-5 py-3 text-sm transition"
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

        <div v-if="loading && channels.length === 0" class="grid gap-4 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
          <div v-for="index in 6" :key="index" class="glass-panel h-40 animate-pulse rounded-[2rem]"></div>
        </div>

        <div
          v-else-if="channels.length === 0"
          class="glass-panel flex min-h-72 items-end rounded-[2.5rem] p-7 sm:p-10"
        >
          <div>
            <p class="text-sm uppercase tracking-[0.28em] text-white/42">No Channels</p>
            <h2 class="mt-3 max-w-2xl text-3xl font-semibold sm:text-5xl">
              Import and extract a live M3U source first.
            </h2>
          </div>
        </div>

        <div v-else class="grid gap-4 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
          <article
            v-for="channel in channels"
            :key="channel.id"
            tabindex="0"
            class="tv-focus-card glass-panel flex min-h-44 cursor-pointer flex-col overflow-hidden rounded-[2rem] border transition"
            :class="
              selectedChannelId === channel.id
                ? 'border-aurora/40 bg-white/10'
                : 'border-white/10 bg-transparent hover:border-white/20'
            "
            @click="selectChannel(channel)"
            @keydown.enter.prevent="selectChannel(channel)"
            @keydown.space.prevent="selectChannel(channel)"
          >
            <div class="flex items-center gap-4 p-5">
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
                <p class="mt-4 line-clamp-2 break-all font-mono text-xs text-white/40">
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
