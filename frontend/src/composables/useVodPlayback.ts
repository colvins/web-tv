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
  webkitRequestFullscreen?: () => Promise<void> | void
  webkitDisplayingFullscreen?: boolean
}

export function useVodPlayback() {
  const currentEpisode = ref<VodEpisodePlay | null>(null)
  const playbackState = ref<VodPlaybackState>('idle')
  const errorMessage = ref('')
  const isPlaying = ref(false)
  const isMuted = ref(false)
  const isFullscreen = ref(false)
  const playerStatusText = ref('请选择剧集开始播放。')
  const videoEl = ref<HTMLVideoElement | null>(null)

  let hls: Hls | null = null

  const streamHost = computed(() => currentEpisode.value?.stream_host ?? '未知来源')
  const streamTypeGuess = computed(() => currentEpisode.value?.stream_type_guess ?? '未知格式')
  const nativeHlsSupported = computed(() => !!videoEl.value?.canPlayType('application/vnd.apple.mpegurl'))
  const hlsJsSupported = computed(() => Hls.isSupported())

  function prefersNativeHlsPlayback() {
    const userAgent = navigator.userAgent
    const vendor = navigator.vendor
    const isAppleWebKit = /AppleWebKit/i.test(userAgent)
    const isSafariBrand = /Safari/i.test(userAgent) && !/(Chrome|Chromium|CriOS|Edg|OPR|FxiOS|Android)/i.test(userAgent)
    const isAppleVendor = /Apple/i.test(vendor)
    return isSafariBrand || (isAppleVendor && isAppleWebKit && !Hls.isSupported())
  }

  function setVideoElement(element: unknown) {
    videoEl.value = element instanceof HTMLVideoElement ? element : null
  }

  function destroyPlayer() {
    hls?.destroy()
    hls = null
    const video = videoEl.value
    if (video) {
      video.pause()
      video.removeAttribute('src')
      video.load()
    }
    currentEpisode.value = null
    playbackState.value = 'idle'
    errorMessage.value = ''
    playerStatusText.value = '请选择剧集开始播放。'
    isPlaying.value = false
  }

  async function attemptPlay() {
    const video = videoEl.value
    if (!video) return
    try {
      await video.play()
    } catch (error) {
      playbackState.value = 'ready'
      playerStatusText.value = '可以开始播放。'
      isPlaying.value = false
      if (error instanceof DOMException && error.name === 'NotAllowedError') {
        errorMessage.value = '自动播放被阻止，请点击播放继续。'
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
    playerStatusText.value = '正在加载播放...'
    video.muted = isMuted.value

    if (episode.is_hls_like) {
      if (prefersNativeHlsPlayback() && video.canPlayType('application/vnd.apple.mpegurl')) {
        video.src = episode.stream_url
        video.load()
        await attemptPlay()
        return
      }

      if (Hls.isSupported()) {
        const nextHls = new Hls()
        hls = nextHls
        nextHls.on(Hls.Events.MEDIA_ATTACHED, () => {
          nextHls.loadSource(episode.stream_url)
        })
        nextHls.on(Hls.Events.MANIFEST_PARSED, () => {
          void attemptPlay()
        })
        nextHls.on(Hls.Events.ERROR, (_event, data) => {
          if (data.fatal) {
            nextHls.destroy()
            if (hls === nextHls) {
              hls = null
            }
            playbackState.value = 'error'
            playerStatusText.value = '播放失败。'
            errorMessage.value = '无法加载当前 HLS 播放地址。'
            isPlaying.value = false
          }
        })
        nextHls.attachMedia(video)
        return
      }

      playbackState.value = 'error'
      playerStatusText.value = '播放失败。'
      errorMessage.value = '当前浏览器不支持 HLS 播放。'
      return
    }

    video.src = episode.stream_url
    video.load()
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

    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen()
        return
      }

      if (typeof video.webkitEnterFullscreen === 'function') {
        video.webkitEnterFullscreen()
        return
      }

      if (typeof container.requestFullscreen === 'function') {
        await container.requestFullscreen()
        return
      }

      if (typeof video.requestFullscreen === 'function') {
        await video.requestFullscreen()
        return
      }

      if (typeof video.webkitRequestFullscreen === 'function') {
        await video.webkitRequestFullscreen()
      }
    } catch (error) {
      console.warn('Unable to enter VOD fullscreen mode', error)
    }
  }

  function handlePlaying() {
    playbackState.value = 'ready'
    playerStatusText.value = '正在播放。'
    isPlaying.value = true
    errorMessage.value = ''
  }

  function handlePause() {
    isPlaying.value = false
    if (playbackState.value !== 'error') {
      playerStatusText.value = '已暂停。'
    }
  }

  function handleWaiting() {
    if (!currentEpisode.value) return
    playbackState.value = 'loading'
    playerStatusText.value = '正在缓冲...'
  }

  function handleCanPlay() {
    if (playbackState.value === 'error') return
    playbackState.value = 'ready'
    if (!isPlaying.value) {
      playerStatusText.value = '可以开始播放。'
    }
  }

  function handleVideoError() {
    const mediaError = videoEl.value?.error
    console.error('VOD native video error', {
      code: mediaError?.code ?? null,
      message: mediaError?.message ?? null,
      streamHost: currentEpisode.value?.stream_host ?? null,
      streamTypeGuess: currentEpisode.value?.stream_type_guess ?? null,
    })
    playbackState.value = 'error'
    playerStatusText.value = '播放失败。'
    errorMessage.value = '浏览器媒体播放出错。'
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

export type VodPlayback = ReturnType<typeof useVodPlayback>
