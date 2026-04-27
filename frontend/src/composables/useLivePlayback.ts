import Hls from 'hls.js'
import mpegts from 'mpegts.js'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { diagnoseLiveChannel, type LiveChannel, type LiveChannelDiagnosis } from '@/api/sourceConfigs'
import { ApiError } from '@/api/client'

export type PlaybackState = 'idle' | 'loading' | 'ready' | 'error'
export type ChannelPlaybackStatus = 'unknown' | 'playing' | 'failed'
export type PlaybackErrorCategory =
  | 'autoplay_blocked'
  | 'unsupported_format'
  | 'hls_manifest_error'
  | 'hls_network_error'
  | 'hls_media_error'
  | 'native_media_error'
  | 'stream_load_error'
  | 'unknown_error'

type FullscreenCapableVideo = HTMLVideoElement & {
  webkitEnterFullscreen?: () => void
  webkitDisplayingFullscreen?: boolean
}

type PlaybackErrorInfo = {
  category: PlaybackErrorCategory
  message: string
  technicalReason: string
  detail?: string
}

type NativeVideoErrorInfo = {
  code: string
  message: string
}

type HlsErrorInfo = {
  type: string
  details: string
}

export type StreamTypeGuess = 'hls_m3u8' | 'direct_ts' | 'unknown_stream'

export function useLivePlayback() {
  const selectedChannel = ref<LiveChannel | null>(null)
  const playbackState = ref<PlaybackState>('idle')
  const playbackError = ref('')
  const playbackErrorCategory = ref<PlaybackErrorCategory | null>(null)
  const playbackErrorTechnical = ref('')
  const nativeVideoError = ref<NativeVideoErrorInfo | null>(null)
  const hlsError = ref<HlsErrorInfo | null>(null)
  const isPlaying = ref(false)
  const isMuted = ref(false)
  const isFullscreen = ref(false)
  const playerStatusText = ref('Select a channel to start playback.')
  const channelDiagnosis = ref<LiveChannelDiagnosis | null>(null)
  const channelDiagnosisLoading = ref(false)
  const channelDiagnosisError = ref('')
  const videoEl = ref<HTMLVideoElement | null>(null)
  const controlsVisible = ref(true)
  const playerHovering = ref(false)
  const playerFocused = ref(false)

  let hls: Hls | null = null
  let mpegtsPlayer: mpegts.Player | null = null
  let controlsHideTimer: number | undefined
  let hlsMediaRecoveryAttempted = false
  let browserProfileRetryAttempted = false
  let mpegtsFallbackAttempted = false
  let usingMpegtsFallback = false
  let usingBrowserProfileFallback = false
  let lastLoggedErrorSignature = ''
  const browserPlaybackUrlCache = new Map<string, string | null>()

  const selectedChannelId = computed(() => selectedChannel.value?.id ?? null)
  const shouldPinControlsVisible = computed(() =>
    playbackState.value === 'idle' ||
    playbackState.value === 'loading' ||
    playbackState.value === 'error' ||
    !selectedChannel.value,
  )
  const streamHost = computed(() => getStreamHost(selectedChannel.value?.stream_url))
  const streamTypeGuess = computed<StreamTypeGuess>(() => guessStreamType(selectedChannel.value?.stream_url ?? ''))
  const nativeHlsSupported = computed(() => {
    const video = videoEl.value
    return !!video?.canPlayType('application/vnd.apple.mpegurl')
  })
  const hlsJsSupported = computed(() => Hls.isSupported())

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
    const keepVisibleForFocus = playerFocused.value && !isFullscreen.value
    if (shouldPinControlsVisible.value || keepVisibleForHover || keepVisibleForFocus || !isPlaying.value) {
      controlsVisible.value = true
      clearControlsHideTimer()
      return
    }

    clearControlsHideTimer()
    controlsHideTimer = window.setTimeout(() => {
      const canHideForPointerState = !playerHovering.value || isFullscreen.value
      const canHideForFocusState = !playerFocused.value || isFullscreen.value
      if (canHideForPointerState && canHideForFocusState && isPlaying.value && playbackState.value === 'ready') {
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
    mpegtsPlayer?.unload()
    mpegtsPlayer?.detachMediaElement()
    mpegtsPlayer?.destroy()
    mpegtsPlayer = null
    hlsMediaRecoveryAttempted = false
    browserProfileRetryAttempted = false
    mpegtsFallbackAttempted = false
    usingMpegtsFallback = false
    usingBrowserProfileFallback = false
    channelDiagnosis.value = null
    channelDiagnosisLoading.value = false
    channelDiagnosisError.value = ''

    const video = videoEl.value
    if (!video) return
    video.pause()
    video.removeAttribute('src')
    video.load()
  }

  function getStreamHost(streamUrl: string | null | undefined) {
    if (!streamUrl) return 'unknown-host'

    try {
      return new URL(streamUrl).host || 'unknown-host'
    } catch {
      return 'unknown-host'
    }
  }

  function guessStreamType(streamUrl: string) {
    const normalizedUrl = streamUrl.toLowerCase()
    if (normalizedUrl.includes('.m3u8')) return 'hls_m3u8'
    if (
      normalizedUrl.includes('.ts') ||
      normalizedUrl.includes('mpegts') ||
      normalizedUrl.includes('transportstream') ||
      normalizedUrl.includes('video/mp2t')
    ) {
      return 'direct_ts'
    }
    return 'unknown_stream'
  }

  function isDirectTsStream(url: string) {
    return guessStreamType(url) === 'direct_ts'
  }

  function logPlaybackFailure(error: PlaybackErrorInfo) {
    const signature = JSON.stringify({
      channel: selectedChannel.value?.name ?? 'unknown-channel',
      host: getStreamHost(selectedChannel.value?.stream_url),
      category: error.category,
      technicalReason: error.technicalReason,
      detail: error.detail ?? '',
      nativeVideoError: nativeVideoError.value,
      hlsError: hlsError.value,
    })

    if (signature === lastLoggedErrorSignature) return

    lastLoggedErrorSignature = signature
    console.warn('[live-playback]', JSON.parse(signature))
  }

  function setPlaybackError(error: PlaybackErrorInfo) {
    playbackState.value = 'error'
    playbackError.value = error.message
    playbackErrorCategory.value = error.category
    playbackErrorTechnical.value = error.technicalReason
    playerStatusText.value = error.message
    isPlaying.value = false
    logPlaybackFailure(error)
    revealControls()
  }

  function clearPlaybackError() {
    playbackError.value = ''
    playbackErrorCategory.value = null
    playbackErrorTechnical.value = ''
    nativeVideoError.value = null
    hlsError.value = null
    lastLoggedErrorSignature = ''
  }

  function buildPlaybackError(category: PlaybackErrorCategory, detail?: string): PlaybackErrorInfo {
    switch (category) {
      case 'autoplay_blocked':
        return {
          category,
          message: 'Playback failed: autoplay was blocked. Tap play to start the channel.',
          technicalReason: 'Autoplay blocked by browser policy.',
          detail,
        }
      case 'unsupported_format':
        return {
          category,
          message: 'Playback failed: browser does not support this stream format.',
          technicalReason: 'Stream format is not supported in this browser.',
          detail,
        }
      case 'hls_manifest_error':
        return {
          category,
          message: 'Playback failed: HLS manifest could not be loaded.',
          technicalReason: 'HLS manifest load error.',
          detail,
        }
      case 'hls_network_error':
        return {
          category,
          message: 'Playback failed: network error while loading the stream.',
          technicalReason: 'HLS network error.',
          detail,
        }
      case 'hls_media_error':
        return {
          category,
          message: 'Playback failed: media decode error.',
          technicalReason: 'HLS media error.',
          detail,
        }
      case 'native_media_error':
        return {
          category,
          message: 'Playback failed: browser media playback error.',
          technicalReason: 'Native media element error.',
          detail,
        }
      case 'stream_load_error':
        return {
          category,
          message: 'Playback failed: could not load this channel stream.',
          technicalReason: 'Stream load failed.',
          detail,
        }
      case 'unknown_error':
      default:
        return {
          category: 'unknown_error',
          message: 'Playback failed: unknown playback error.',
          technicalReason: 'Unknown playback error.',
          detail,
        }
    }
  }

  function classifyHlsError(data: {
    details?: string
    fatal?: boolean
    error?: unknown
    networkDetails?: unknown
    response?: { code?: number; text?: string }
  }): PlaybackErrorInfo {
    const detailParts = [data.details, data.response?.code ? `HTTP ${data.response.code}` : undefined]
      .filter(Boolean)
      .join(' | ')

    switch (data.details) {
      case Hls.ErrorDetails.MANIFEST_LOAD_ERROR:
      case Hls.ErrorDetails.MANIFEST_LOAD_TIMEOUT:
      case Hls.ErrorDetails.MANIFEST_PARSING_ERROR:
      case Hls.ErrorDetails.MANIFEST_INCOMPATIBLE_CODECS_ERROR:
        return buildPlaybackError('hls_manifest_error', detailParts)
      case Hls.ErrorDetails.LEVEL_LOAD_ERROR:
      case Hls.ErrorDetails.LEVEL_LOAD_TIMEOUT:
      case Hls.ErrorDetails.AUDIO_TRACK_LOAD_ERROR:
      case Hls.ErrorDetails.AUDIO_TRACK_LOAD_TIMEOUT:
      case Hls.ErrorDetails.FRAG_LOAD_ERROR:
      case Hls.ErrorDetails.FRAG_LOAD_TIMEOUT:
      case Hls.ErrorDetails.KEY_LOAD_ERROR:
      case Hls.ErrorDetails.KEY_LOAD_TIMEOUT:
        return buildPlaybackError('hls_network_error', detailParts)
      case Hls.ErrorDetails.BUFFER_APPEND_ERROR:
      case Hls.ErrorDetails.BUFFER_APPENDING_ERROR:
      case Hls.ErrorDetails.FRAG_DECRYPT_ERROR:
      case Hls.ErrorDetails.FRAG_PARSING_ERROR:
      case Hls.ErrorDetails.BUFFER_STALLED_ERROR:
      case Hls.ErrorDetails.BUFFER_SEEK_OVER_HOLE:
        return buildPlaybackError('hls_media_error', detailParts)
      default:
        if (data.networkDetails) {
          return buildPlaybackError('hls_network_error', detailParts || 'Network request failed')
        }
        return buildPlaybackError(data.fatal ? 'stream_load_error' : 'unknown_error', detailParts)
    }
  }

  function classifyNativeVideoError(error: MediaError | null): PlaybackErrorInfo {
    switch (error?.code) {
      case MediaError.MEDIA_ERR_ABORTED:
        return buildPlaybackError('stream_load_error', 'MEDIA_ERR_ABORTED')
      case MediaError.MEDIA_ERR_NETWORK:
        return buildPlaybackError('stream_load_error', 'MEDIA_ERR_NETWORK')
      case MediaError.MEDIA_ERR_DECODE:
        return buildPlaybackError('native_media_error', 'MEDIA_ERR_DECODE')
      case MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED:
        return buildPlaybackError('unsupported_format', 'MEDIA_ERR_SRC_NOT_SUPPORTED')
      default:
        return buildPlaybackError('unknown_error', error?.message || 'Unknown media element error')
    }
  }

  function getNativeVideoErrorCodeLabel(error: MediaError | null) {
    switch (error?.code) {
      case MediaError.MEDIA_ERR_ABORTED:
        return 'MEDIA_ERR_ABORTED'
      case MediaError.MEDIA_ERR_NETWORK:
        return 'MEDIA_ERR_NETWORK'
      case MediaError.MEDIA_ERR_DECODE:
        return 'MEDIA_ERR_DECODE'
      case MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED:
        return 'MEDIA_ERR_SRC_NOT_SUPPORTED'
      default:
        return 'UNKNOWN_MEDIA_ERR'
    }
  }

  async function attemptPlay() {
    const video = videoEl.value
    if (!video) return

    revealControls()

    try {
      await video.play()
    } catch (error) {
      if (error instanceof DOMException && error.name === 'NotAllowedError') {
        setPlaybackError(buildPlaybackError('autoplay_blocked', error.name))
        return
      }

      playbackState.value = 'ready'
      playerStatusText.value = 'Ready to play.'
      clearPlaybackError()
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
    clearPlaybackError()
    playerStatusText.value = 'Loading stream...'
    controlsVisible.value = true
    video.muted = isMuted.value

    const streamUrl = channel.stream_url

    if (isDirectTsStream(streamUrl)) {
      const cachedBrowserPlaybackUrl = browserPlaybackUrlCache.get(channel.id)
      if (cachedBrowserPlaybackUrl) {
        usingBrowserProfileFallback = true
        video.src = cachedBrowserPlaybackUrl
        await attemptPlay()
        return
      }

      if (!browserPlaybackUrlCache.has(channel.id)) {
        try {
          const diagnosis = await diagnoseLiveChannel(channel.id)
          channelDiagnosis.value = diagnosis
          browserPlaybackUrlCache.set(channel.id, diagnosis.browser_playback_url)

          if (diagnosis.browser_playback_url) {
            usingBrowserProfileFallback = true
            playerStatusText.value = 'Loading browser-friendly stream...'
            video.src = diagnosis.browser_playback_url
            await attemptPlay()
            return
          }

          if (mpegts.isSupported()) {
            mpegtsFallbackAttempted = true
            await startMpegtsFallback(streamUrl)
            return
          }
        } catch {
          browserPlaybackUrlCache.set(channel.id, null)
        }
      } else if (mpegts.isSupported()) {
        mpegtsFallbackAttempted = true
        await startMpegtsFallback(streamUrl)
        return
      }
    }

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
          hlsError.value = {
            type: data.type ?? 'unknown',
            details: [data.details, data.response?.code ? `HTTP ${data.response.code}` : undefined]
              .filter(Boolean)
              .join(' | '),
          }

          if (data.details === Hls.ErrorDetails.BUFFER_STALLED_ERROR && !data.fatal) {
            playbackState.value = 'loading'
            playerStatusText.value = 'Buffering stream...'
            revealControls()
            return
          }

          if (data.details === Hls.ErrorDetails.BUFFER_APPENDING_ERROR && data.fatal && !hlsMediaRecoveryAttempted) {
            hlsMediaRecoveryAttempted = true
            playerStatusText.value = 'Recovering stream...'
            playbackState.value = 'loading'
            revealControls()
            hls?.recoverMediaError()
            return
          }

          if (data.fatal && data.type === Hls.ErrorTypes.MEDIA_ERROR && !hlsMediaRecoveryAttempted) {
            hlsMediaRecoveryAttempted = true
            playerStatusText.value = 'Recovering stream...'
            playbackState.value = 'loading'
            revealControls()
            hls?.recoverMediaError()
            return
          }

          if (data.fatal) {
            setPlaybackError(classifyHlsError(data))
          }
        })
        return
      }

      setPlaybackError(buildPlaybackError('unsupported_format', 'HLS playback not supported'))
      return
    }

    video.src = streamUrl
    await attemptPlay()
  }

  async function startMpegtsFallback(streamUrl: string) {
    const video = videoEl.value
    if (!video || !mpegts.isSupported()) {
      setPlaybackError(buildPlaybackError('unsupported_format', 'MPEG-TS fallback is not supported in this browser'))
      return
    }

    hls?.destroy()
    hls = null
    mpegtsPlayer?.unload()
    mpegtsPlayer?.detachMediaElement()
    mpegtsPlayer?.destroy()
    mpegtsPlayer = null

    usingMpegtsFallback = true
    playbackState.value = 'loading'
    playerStatusText.value = 'Retrying stream with TS fallback...'
    revealControls()

    mpegtsPlayer = mpegts.createPlayer(
      {
        type: 'mpegts',
        isLive: true,
        url: streamUrl,
      },
      {
        enableWorker: true,
        lazyLoad: false,
        liveBufferLatencyChasing: true,
        liveSync: true,
      },
    )

    mpegtsPlayer.on(mpegts.Events.ERROR, (errorType: string, errorDetail: string, errorInfo: unknown) => {
      const detail = [errorType, errorDetail, errorInfo ? JSON.stringify(errorInfo) : ''].filter(Boolean).join(' | ')
      setPlaybackError(buildPlaybackError('stream_load_error', detail))
    })
    mpegtsPlayer.attachMediaElement(video)
    mpegtsPlayer.load()
    await attemptPlay()
  }

  async function startBrowserProfileFallback() {
    if (!selectedChannel.value) return false

    channelDiagnosisError.value = ''

    try {
      const diagnosis = await diagnoseLiveChannel(selectedChannel.value.id)
      channelDiagnosis.value = diagnosis

      if (!diagnosis.browser_playback_url) return false

      const video = videoEl.value
      if (!video) return false

      usingBrowserProfileFallback = true
      playbackState.value = 'loading'
      playerStatusText.value = 'Retrying stream with browser profile...'
      revealControls()

      hls?.destroy()
      hls = null
      mpegtsPlayer?.unload()
      mpegtsPlayer?.detachMediaElement()
      mpegtsPlayer?.destroy()
      mpegtsPlayer = null

      video.src = diagnosis.browser_playback_url
      await attemptPlay()
      return true
    } catch (error) {
      channelDiagnosisError.value = error instanceof ApiError ? error.message : 'Unable to resolve browser playback profile.'
      return false
    }
  }

  async function runChannelDiagnosis() {
    if (!selectedChannel.value) return

    channelDiagnosisLoading.value = true
    channelDiagnosisError.value = ''

    try {
      channelDiagnosis.value = await diagnoseLiveChannel(selectedChannel.value.id)
    } catch (error) {
      channelDiagnosis.value = null
      channelDiagnosisError.value = error instanceof ApiError ? error.message : 'Unable to diagnose this channel.'
    } finally {
      channelDiagnosisLoading.value = false
      revealControls()
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
    clearPlaybackError()
    if (!isPlaying.value) {
      playerStatusText.value = 'Ready to play.'
    }
    syncControlsVisibility()
  }

  function handleVideoError() {
    const mediaError = videoEl.value?.error ?? null
    nativeVideoError.value = {
      code: getNativeVideoErrorCodeLabel(mediaError),
      message: mediaError?.message || 'Media element reported an error.',
    }

    const streamUrl = selectedChannel.value?.stream_url ?? ''
    const shouldTryMpegtsFallback =
      !usingBrowserProfileFallback &&
      !usingMpegtsFallback &&
      !mpegtsFallbackAttempted &&
      isDirectTsStream(streamUrl) &&
      mpegts.isSupported() &&
      mediaError?.code !== MediaError.MEDIA_ERR_ABORTED

    const shouldTryBrowserProfileFallback =
      !usingBrowserProfileFallback &&
      !browserProfileRetryAttempted &&
      isDirectTsStream(streamUrl) &&
      mediaError?.code !== MediaError.MEDIA_ERR_ABORTED

    if (shouldTryBrowserProfileFallback) {
      browserProfileRetryAttempted = true
      void startBrowserProfileFallback().then((resolved) => {
        if (!resolved && shouldTryMpegtsFallback) {
          mpegtsFallbackAttempted = true
          void startMpegtsFallback(streamUrl)
        }
      })
      return
    }

    if (shouldTryMpegtsFallback) {
      mpegtsFallbackAttempted = true
      void startMpegtsFallback(streamUrl)
      return
    }

    setPlaybackError(classifyNativeVideoError(mediaError))
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
    playbackErrorCategory,
    playbackErrorTechnical,
    nativeVideoError,
    hlsError,
    streamHost,
    streamTypeGuess,
    nativeHlsSupported,
    hlsJsSupported,
    isPlaying,
    isMuted,
    isFullscreen,
    playerStatusText,
    channelDiagnosis,
    channelDiagnosisLoading,
    channelDiagnosisError,
    controlsVisible,
    setVideoElement,
    updateSelectedChannel,
    loadChannel,
    runChannelDiagnosis,
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
