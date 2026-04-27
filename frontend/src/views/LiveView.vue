<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RefreshCw } from 'lucide-vue-next'
import { NButton, NSelect, useMessage } from 'naive-ui'

import LiveDesktopLayout from '@/components/live/LiveDesktopLayout.vue'
import LiveMobileLayout from '@/components/live/LiveMobileLayout.vue'
import { useLivePlayback, type ChannelPlaybackStatus } from '@/composables/useLivePlayback'
import {
  listLiveChannels,
  listLiveGroups,
  listSourceConfigs,
  updateLiveChannel,
  type LiveChannel,
  type LiveChannelGroup,
  type SourceConfig,
} from '@/api/sourceConfigs'
import { ApiError } from '@/api/client'

const LIVE_SOURCE_STORAGE_KEY = 'webtv.live.selectedSourceConfigId'

const message = useMessage()
const sources = ref<SourceConfig[]>([])
const groups = ref<LiveChannelGroup[]>([])
const channels = ref<LiveChannel[]>([])
const selectedSourceId = ref<string | null>(null)
const selectedGroupId = ref<string | null>(null)
const query = ref('')
const loading = ref(false)
const sourceLoading = ref(false)
const loadError = ref<string | null>(null)
const togglingIds = ref<Set<string>>(new Set())
const isDesktopLayout = ref(true)
const channelPlaybackStatuses = ref<Record<string, ChannelPlaybackStatus>>({})
const playback = useLivePlayback()

let searchTimer: number | undefined
let mediaQuery: MediaQueryList | undefined

const enabledSources = computed(() => sources.value.filter((source) => source.enabled))
const compatibleSources = computed(() => enabledSources.value.filter((source) => source.live_channel_count > 0))
const selectedSource = computed(
  () => sources.value.find((source) => source.id === selectedSourceId.value) ?? null,
)
const selectedSourceHasLiveData = computed(() => (selectedSource.value?.live_channel_count ?? 0) > 0)
const sourceOptions = computed(() =>
  compatibleSources.value.map((source) => {
    const format = source.latest_detected_format ?? source.source_type.toUpperCase()
    const liveCount = source.live_channel_count
    const status = source.latest_import_status ? source.latest_import_status.toUpperCase() : 'NEW'
    return {
      label: `${source.name} · ${format} · Live ${liveCount} · ${status}`,
      value: source.id,
    }
  }),
)
const emptyStateTitle = computed(() => {
  if (enabledSources.value.length === 0) return 'No source packages are enabled'
  if (!selectedSourceId.value) return 'No live-capable source is available yet'
  if (!selectedSource.value) return 'Selected live source is no longer available'
  if (!selectedSourceHasLiveData.value) return 'No extracted live channels for this source'
  return 'No channels matched the current view'
})
const emptyStateDescription = computed(() => {
  if (enabledSources.value.length === 0) {
    return 'Enable or import a source package in Settings before opening Live TV.'
  }
  if (!selectedSourceId.value) {
    return 'Import and extract a live M3U source in Settings, then select it here.'
  }
  if (!selectedSource.value) {
    return 'Pick another imported source package from the selector.'
  }
  if (!selectedSourceHasLiveData.value) {
    return 'This source package has no extracted live channel data yet. Import and extract live channels from Settings/Sources first.'
  }
  return 'Adjust the group or search filter, or choose another live source package.'
})

function syncLayoutMode() {
  isDesktopLayout.value = mediaQuery?.matches ?? window.innerWidth >= 768
}

function restoreSavedSourceId() {
  return window.localStorage.getItem(LIVE_SOURCE_STORAGE_KEY)
}

function persistSelectedSourceId(sourceId: string | null) {
  if (sourceId) {
    window.localStorage.setItem(LIVE_SOURCE_STORAGE_KEY, sourceId)
    return
  }
  window.localStorage.removeItem(LIVE_SOURCE_STORAGE_KEY)
}

function resetSourceBoundState() {
  groups.value = []
  channels.value = []
  selectedGroupId.value = null
  channelPlaybackStatuses.value = {}
  playback.clearSelectedChannel()
}

async function selectChannel(channel: LiveChannel) {
  await playback.loadChannel(channel)
}

async function loadLiveData(sourceId = selectedSourceId.value) {
  if (!sourceId || !selectedSourceHasLiveData.value) {
    groups.value = []
    channels.value = []
    return
  }

  loading.value = true
  loadError.value = null
  try {
    const [groupResult, channelResult] = await Promise.all([
      listLiveGroups(sourceId),
      listLiveChannels({
        source_config_id: sourceId,
        group_id: selectedGroupId.value ?? undefined,
        q: query.value || undefined,
      }),
    ])
    groups.value = groupResult
    channels.value = channelResult

    const selected = playback.selectedChannel.value
    const latestSelected = selected ? channelResult.find((channel) => channel.id === selected.id) : null
    if (latestSelected) {
      playback.updateSelectedChannel(latestSelected)
    } else if (selected) {
      playback.clearSelectedChannel()
    }
  } catch (error) {
    groups.value = []
    channels.value = []
    loadError.value = error instanceof ApiError ? error.message : 'Unable to load live channels'
    message.error(loadError.value)
  } finally {
    loading.value = false
  }
}

async function bootstrap() {
  sourceLoading.value = true
  loadError.value = null
  try {
    const sourceList = await listSourceConfigs()
    sources.value = sourceList

    const enabledIds = new Set(compatibleSources.value.map((source) => source.id))
    const currentSelection = selectedSourceId.value
    const savedSelection = restoreSavedSourceId()
    const preferredSourceId =
      (currentSelection && enabledIds.has(currentSelection) ? currentSelection : null) ??
      (savedSelection && enabledIds.has(savedSelection) ? savedSelection : null) ??
      compatibleSources.value[0]?.id ??
      null

    if (!preferredSourceId) {
      selectedSourceId.value = null
      persistSelectedSourceId(null)
      resetSourceBoundState()
      return
    }

    selectedSourceId.value = preferredSourceId
    persistSelectedSourceId(preferredSourceId)
    resetSourceBoundState()
    if (sourceList.find((source) => source.id === preferredSourceId)?.live_channel_count) {
      await loadLiveData(preferredSourceId)
    }
  } catch (error) {
    loadError.value = error instanceof ApiError ? error.message : 'Unable to load source packages'
    message.error(loadError.value)
  } finally {
    sourceLoading.value = false
  }
}

async function toggleChannel(channel: LiveChannel, enabled: boolean) {
  const previous = channel.enabled
  channel.enabled = enabled
  togglingIds.value = new Set(togglingIds.value).add(channel.id)
  try {
    const updated = await updateLiveChannel(channel.id, enabled)
    channels.value = channels.value.map((item) => (item.id === updated.id ? updated : item))
    playback.updateSelectedChannel(updated)
  } catch (error) {
    channel.enabled = previous
    message.error(error instanceof ApiError ? error.message : 'Unable to update channel')
  } finally {
    const next = new Set(togglingIds.value)
    next.delete(channel.id)
    togglingIds.value = next
  }
}

function selectGroup(groupId: string | null) {
  selectedGroupId.value = groupId
}

function markChannelPlaybackStatus(channelId: string | null, status: Exclude<ChannelPlaybackStatus, 'unknown'>) {
  if (!channelId) return

  channelPlaybackStatuses.value = {
    ...channelPlaybackStatuses.value,
    [channelId]: status,
  }
}

function onSourceChange(value: string | null) {
  selectedSourceId.value = value
  persistSelectedSourceId(value)
  loadError.value = null
  resetSourceBoundState()
  if (value && sources.value.find((source) => source.id === value)?.live_channel_count) {
    void loadLiveData(value)
  }
}

watch(query, () => {
  window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(() => {
    if (selectedSourceId.value && selectedSourceHasLiveData.value) {
      void loadLiveData()
    }
  }, 250)
})

watch(selectedGroupId, () => {
  if (selectedSourceId.value && selectedSourceHasLiveData.value) {
    void loadLiveData()
  }
})

watch(
  [playback.selectedChannelId, playback.playbackState],
  ([channelId, playbackState]) => {
    if (playbackState === 'ready') {
      markChannelPlaybackStatus(channelId, 'playing')
      return
    }

    if (playbackState === 'error') {
      markChannelPlaybackStatus(channelId, 'failed')
    }
  },
  { immediate: true },
)

onMounted(() => {
  mediaQuery = window.matchMedia('(min-width: 768px)')
  syncLayoutMode()
  mediaQuery.addEventListener('change', syncLayoutMode)
  void bootstrap()
})

onBeforeUnmount(() => {
  window.clearTimeout(searchTimer)
  mediaQuery?.removeEventListener('change', syncLayoutMode)
})
</script>

<template>
  <section class="grid gap-6">
    <div class="glass-panel rounded-[2rem] p-5 sm:rounded-[2.5rem] sm:p-7">
      <div class="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p class="text-sm uppercase tracking-[0.28em] text-white/42">Live Source</p>
          <h2 class="mt-3 text-3xl font-semibold text-white sm:text-5xl">
            {{ selectedSource?.name ?? 'Choose a live source' }}
          </h2>
          <p class="mt-3 max-w-3xl text-sm leading-6 text-white/58">Select a live source to browse its channel list.</p>
        </div>
        <div class="flex flex-col gap-3 sm:min-w-[22rem]">
          <NSelect
            :value="selectedSourceId"
            :options="sourceOptions"
            placeholder="Select a live source"
            :loading="sourceLoading"
            @update:value="onSourceChange"
          />
          <NButton round secondary :loading="sourceLoading || loading" @click="bootstrap">
            <template #icon><RefreshCw class="h-4 w-4" /></template>
            Refresh sources
          </NButton>
        </div>
      </div>
    </div>

    <div v-if="loadError" class="glass-panel rounded-[2rem] border border-red-300/18 bg-red-400/10 p-5 text-red-100">
      {{ loadError }}
    </div>

    <div
      v-if="!selectedSourceId || !selectedSource || !selectedSourceHasLiveData"
      class="glass-panel flex min-h-[20rem] items-end rounded-[2.5rem] p-7 sm:p-10"
    >
      <div class="max-w-3xl">
        <p class="text-sm uppercase tracking-[0.28em] text-white/42">Live source</p>
        <h2 class="mt-3 text-3xl font-semibold text-white sm:text-5xl">{{ emptyStateTitle }}</h2>
        <p class="mt-5 text-base leading-7 text-white/58">{{ emptyStateDescription }}</p>
      </div>
    </div>

    <template v-else>
      <LiveDesktopLayout
        v-if="isDesktopLayout"
        v-model:query="query"
        :groups="groups"
        :channels="channels"
        :selected-group-id="selectedGroupId"
        :loading="loading"
        :toggling-ids="togglingIds"
        :playback="playback"
        :channel-playback-statuses="channelPlaybackStatuses"
        @refresh="loadLiveData"
        @select-group="selectGroup"
        @select-channel="selectChannel"
        @toggle-channel="toggleChannel"
      />
      <LiveMobileLayout
        v-else
        v-model:query="query"
        :groups="groups"
        :channels="channels"
        :selected-group-id="selectedGroupId"
        :loading="loading"
        :toggling-ids="togglingIds"
        :playback="playback"
        :channel-playback-statuses="channelPlaybackStatuses"
        @refresh="loadLiveData"
        @select-group="selectGroup"
        @select-channel="selectChannel"
        @toggle-channel="toggleChannel"
      />
    </template>
  </section>
</template>
