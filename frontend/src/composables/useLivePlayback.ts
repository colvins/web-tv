import Hls from 'hls.js'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import type { LiveChannel } from '@/api/sourceConfigs'

export type PlaybackState = 'idle' | 'loading' | 'ready' | 'error'

type FullscreenCapableVideo = HTMLVideoElement & {
  webkitEnterFullscreen?: () => void
  webkitDisplayingFullscreen?: boolean
}

export function useLivePlayback() {
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
  let controlsHideTimer: number | undefined

  const selectedChannelId = computed(() => selectedChannel.value?.id ?? null)
  const shouldPinControlsVisible = computed(() =>
    playbackState.value === 'idle' ||
    playbackState.value === 'loading' ||
    playbackState.value === 'error' ||
    !selectedChannel.value,
  )

  function setVideoElement(element: unknown) {
    videoEl.value = element instanceof HTMLVideoElement ? element : null
  }

  function updateSelectedChannel(channel: LiveChannel) {
    if (selectedChannel.value?.id === channel.id) {
      selectedChannel.value = { ...selectedChannel.value, ...channel }
    }
  }

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

  async function loadChannel(channel: LiveChannel) {
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

    const isLikelyIos =
      /iPad|iPhone|iPod/.test(navigator.userAgent) ||
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

  watch([shouldPinControlsVisible, isPlaying, isFullscreen], syncControlsVisibility)

  onMounted(() => {
    document.addEventListener('fullscreenchange', syncFullscreenState)
    document.addEventListener('webkitfullscreenchange', syncFullscreenState as EventListener)
  })

  onBeforeUnmount(() => {
    document.removeEventListener('fullscreenchange', syncFullscreenState)
    document.removeEventListener('webkitfullscreenchange', syncFullscreenState as EventListener)
    clearControlsHideTimer()
    destroyPlayer()
  })

  return {
    selectedChannel,
    selectedChannelId,
    playbackState,
    playbackError,
    isPlaying,
    isMuted,
    isFullscreen,
    playerStatusText,
    controlsVisible,
    setVideoElement,
    updateSelectedChannel,
    loadChannel,
    destroyPlayer,
    togglePlayback,
    toggleMute,
    toggleFullscreen,
    handlePlaying,
    handlePause,
    handleWaiting,
    handleCanPlay,
    handleVideoError,
    handleVolumeChange,
    handlePlayerPointerEnter,
    handlePlayerPointerLeave,
    handlePlayerInteraction,
    handlePlayerFocusIn,
    handlePlayerFocusOut,
  }
}

export type LivePlayback = ReturnType<typeof useLivePlayback>
