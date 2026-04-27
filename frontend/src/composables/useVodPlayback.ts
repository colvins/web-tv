import Hls from 'hls.js'
import { computed, onBeforeUnmount, ref } from 'vue'

export type VodPlaybackState = 'idle' | 'loading' | 'ready' | 'error'

export type VodEpisodePlay = {
  vod_id: number | string | null
  source_name: string
  episode_index: number
  episode_name: string
  stream_url: string
  stream_host: string | null
  stream_type_guess: string
  is_hls_like: boolean
  is_direct_file_like: boolean
}

type FullscreenCapableVideo = HTMLVideoElement & {
  webkitEnterFullscreen?: () => void
  webkitDisplayingFullscreen?: boolean
}

export function useVodPlayback() {
  const currentEpisode = ref<VodEpisodePlay | null>(null)
  const playbackState = ref<VodPlaybackState>('idle')
  const errorMessage = ref('')
  const isPlaying = ref(false)
  const isMuted = ref(false)
  const isFullscreen = ref(false)
  const playerStatusText = ref('Choose an episode to start playback.')
  const videoEl = ref<HTMLVideoElement | null>(null)

  let hls: Hls | null = null

  const streamHost = computed(() => currentEpisode.value?.stream_host ?? 'unknown-host')
  const streamTypeGuess = computed(() => currentEpisode.value?.stream_type_guess ?? 'unknown')
  const nativeHlsSupported = computed(() => !!videoEl.value?.canPlayType('application/vnd.apple.mpegurl'))
  const hlsJsSupported = computed(() => Hls.isSupported())

  function setVideoElement(element: unknown) {
    videoEl.value = element instanceof HTMLVideoElement ? element : null
  }

  function destroyPlayer() {
    hls?.destroy()
    hls = null
    const video = videoEl.value
    if (!video) return
    video.pause()
    video.removeAttribute('src')
    video.load()
    isPlaying.value = false
  }

  async function attemptPlay() {
    const video = videoEl.value
    if (!video) return
    try {
      await video.play()
    } catch (error) {
      playbackState.value = 'ready'
      playerStatusText.value = 'Ready to play.'
      isPlaying.value = false
      if (error instanceof DOMException && error.name === 'NotAllowedError') {
        errorMessage.value = 'Autoplay was blocked. Press play to start this episode.'
      }
    }
  }

  async function loadEpisode(episode: VodEpisodePlay) {
    const video = videoEl.value
    if (!video) return

    destroyPlayer()
    currentEpisode.value = episode
    playbackState.value = 'loading'
    errorMessage.value = ''
    playerStatusText.value = 'Loading episode...'
    video.muted = isMuted.value

    if (episode.is_hls_like) {
      if (video.canPlayType('application/vnd.apple.mpegurl')) {
        video.src = episode.stream_url
        await attemptPlay()
        return
      }

      if (Hls.isSupported()) {
        hls = new Hls()
        hls.attachMedia(video)
        hls.on(Hls.Events.MEDIA_ATTACHED, () => {
          hls?.loadSource(episode.stream_url)
        })
        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          void attemptPlay()
        })
        hls.on(Hls.Events.ERROR, (_event, data) => {
          if (data.fatal) {
            playbackState.value = 'error'
            playerStatusText.value = 'Episode playback failed.'
            errorMessage.value = 'Unable to load this HLS episode.'
            isPlaying.value = false
          }
        })
        return
      }
    }

    video.src = episode.stream_url
    await attemptPlay()
  }

  async function togglePlayback() {
    const video = videoEl.value
    if (!video) return
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
    const video = videoEl.value as FullscreenCapableVideo | null
    const container = video?.closest('[data-vod-player-shell]') as HTMLElement | null
    if (!video || !container) return

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

    if (typeof container.requestFullscreen === 'function') {
      await container.requestFullscreen()
      return
    }

    if (typeof video.requestFullscreen === 'function') {
      await video.requestFullscreen()
    }
  }

  function handlePlaying() {
    playbackState.value = 'ready'
    playerStatusText.value = 'Now playing.'
    isPlaying.value = true
    errorMessage.value = ''
  }

  function handlePause() {
    isPlaying.value = false
    if (playbackState.value !== 'error') {
      playerStatusText.value = 'Playback paused.'
    }
  }

  function handleWaiting() {
    if (!currentEpisode.value) return
    playbackState.value = 'loading'
    playerStatusText.value = 'Buffering episode...'
  }

  function handleCanPlay() {
    if (playbackState.value === 'error') return
    playbackState.value = 'ready'
    if (!isPlaying.value) {
      playerStatusText.value = 'Ready to play.'
    }
  }

  function handleVideoError() {
    playbackState.value = 'error'
    playerStatusText.value = 'Episode playback failed.'
    errorMessage.value = 'Browser media playback error.'
    isPlaying.value = false
  }

  function handleVolumeChange() {
    isMuted.value = !!videoEl.value?.muted
  }

  function syncFullscreenState() {
    const video = videoEl.value as FullscreenCapableVideo | null
    const webkitFullscreenElement = (document as Document & { webkitFullscreenElement?: Element | null }).webkitFullscreenElement
    isFullscreen.value = !!document.fullscreenElement || !!webkitFullscreenElement || !!video?.webkitDisplayingFullscreen
  }

  document.addEventListener('fullscreenchange', syncFullscreenState)
  document.addEventListener('webkitfullscreenchange', syncFullscreenState as EventListener)

  onBeforeUnmount(() => {
    destroyPlayer()
    document.removeEventListener('fullscreenchange', syncFullscreenState)
    document.removeEventListener('webkitfullscreenchange', syncFullscreenState as EventListener)
  })

  return {
    currentEpisode,
    playbackState,
    errorMessage,
    isPlaying,
    isMuted,
    isFullscreen,
    playerStatusText,
    streamHost,
    streamTypeGuess,
    nativeHlsSupported,
    hlsJsSupported,
    setVideoElement,
    loadEpisode,
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
  }
}
