<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useMessage } from 'naive-ui'

import LiveDesktopLayout from '@/components/live/LiveDesktopLayout.vue'
import LiveMobileLayout from '@/components/live/LiveMobileLayout.vue'
import { useLivePlayback, type ChannelPlaybackStatus } from '@/composables/useLivePlayback'
import {
  listLiveChannels,
  listLiveGroups,
  updateLiveChannel,
  type LiveChannel,
  type LiveChannelGroup,
} from '@/api/sourceConfigs'
import { ApiError } from '@/api/client'

type PlaybackStatusFilter = 'all' | 'playing' | 'failed' | 'unknown'

const message = useMessage()
const groups = ref<LiveChannelGroup[]>([])
const channels = ref<LiveChannel[]>([])
const selectedGroupId = ref<string | null>(null)
const query = ref('')
const playbackStatusFilter = ref<PlaybackStatusFilter>('all')
const loading = ref(false)
const togglingIds = ref<Set<string>>(new Set())
const isDesktopLayout = ref(true)
const channelPlaybackStatuses = ref<Record<string, ChannelPlaybackStatus>>({})
const playback = useLivePlayback()

let searchTimer: number | undefined
let mediaQuery: MediaQueryList | undefined

const selectedGroupName = computed(
  () => groups.value.find((group) => group.id === selectedGroupId.value)?.name ?? 'All Channels',
)
const filteredChannels = computed(() =>
  channels.value.filter((channel) => {
    if (playbackStatusFilter.value === 'all') return true
    return (channelPlaybackStatuses.value[channel.id] ?? 'unknown') === playbackStatusFilter.value
  }),
)

function syncLayoutMode() {
  isDesktopLayout.value = mediaQuery?.matches ?? window.innerWidth >= 768
}

async function selectChannel(channel: LiveChannel) {
  await playback.loadChannel(channel)
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

    const selected = playback.selectedChannel.value
    const latestSelected = selected ? channelResult.find((channel) => channel.id === selected.id) : null
    if (latestSelected) {
      playback.updateSelectedChannel(latestSelected)
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

function selectPlaybackStatusFilter(filter: PlaybackStatusFilter) {
  playbackStatusFilter.value = filter
}

function markChannelPlaybackStatus(channelId: string | null, status: Exclude<ChannelPlaybackStatus, 'unknown'>) {
  if (!channelId) return

  channelPlaybackStatuses.value = {
    ...channelPlaybackStatuses.value,
    [channelId]: status,
  }
}

watch(query, () => {
  window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(loadLiveData, 250)
})

watch(selectedGroupId, loadLiveData)

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
  void loadLiveData()
})

onBeforeUnmount(() => {
  window.clearTimeout(searchTimer)
  mediaQuery?.removeEventListener('change', syncLayoutMode)
})
</script>

<template>
  <LiveDesktopLayout
    v-if="isDesktopLayout"
    v-model:query="query"
    :groups="groups"
    :channels="filteredChannels"
    :selected-group-id="selectedGroupId"
    :selected-group-name="selectedGroupName"
    :selected-playback-status-filter="playbackStatusFilter"
    :loading="loading"
    :toggling-ids="togglingIds"
    :playback="playback"
    :channel-playback-statuses="channelPlaybackStatuses"
    @refresh="loadLiveData"
    @select-group="selectGroup"
    @select-playback-status-filter="selectPlaybackStatusFilter"
    @select-channel="selectChannel"
    @toggle-channel="toggleChannel"
  />
  <LiveMobileLayout
    v-else
    v-model:query="query"
    :groups="groups"
    :channels="filteredChannels"
    :selected-group-id="selectedGroupId"
    :selected-group-name="selectedGroupName"
    :selected-playback-status-filter="playbackStatusFilter"
    :loading="loading"
    :toggling-ids="togglingIds"
    :playback="playback"
    :channel-playback-statuses="channelPlaybackStatuses"
    @refresh="loadLiveData"
    @select-group="selectGroup"
    @select-playback-status-filter="selectPlaybackStatusFilter"
    @select-channel="selectChannel"
    @toggle-channel="toggleChannel"
  />
</template>
