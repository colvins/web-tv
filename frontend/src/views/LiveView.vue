<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Search, SlidersHorizontal } from 'lucide-vue-next'
import { NButton, NInput, useMessage } from 'naive-ui'

import LiveChannelCard from '@/components/live/LiveChannelCard.vue'
import LivePlayer from '@/components/live/LivePlayer.vue'
import { useLivePlayback } from '@/composables/useLivePlayback'
import {
  listLiveChannels,
  listLiveGroups,
  updateLiveChannel,
  type LiveChannel,
  type LiveChannelGroup,
} from '@/api/sourceConfigs'
import { ApiError } from '@/api/client'

const message = useMessage()
const groups = ref<LiveChannelGroup[]>([])
const channels = ref<LiveChannel[]>([])
const selectedGroupId = ref<string | null>(null)
const query = ref('')
const loading = ref(false)
const togglingIds = ref<Set<string>>(new Set())
const groupScroller = ref<HTMLElement | null>(null)
const groupPointerDown = ref(false)
const groupDragging = ref(false)
const suppressNextGroupClick = ref(false)
const playback = useLivePlayback()

let searchTimer: number | undefined
let suppressGroupClickTimer: number | undefined
let groupDragStartX = 0
let groupDragStartY = 0
let groupDragStartScrollLeft = 0
const groupDragThreshold = 6

const selectedGroupName = computed(
  () => groups.value.find((group) => group.id === selectedGroupId.value)?.name ?? 'All Channels',
)

async function selectChannel(channel: LiveChannel) {
  await playback.loadChannel(channel)
}

function clearSuppressGroupClickTimer() {
  window.clearTimeout(suppressGroupClickTimer)
  suppressGroupClickTimer = undefined
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
  if (suppressNextGroupClick.value) {
    suppressNextGroupClick.value = false
    clearSuppressGroupClickTimer()
    return
  }
  selectedGroupId.value = groupId
}

function startGroupDrag(event: PointerEvent) {
  if (event.pointerType === 'touch' || event.button !== 0) return
  const scroller = groupScroller.value
  if (!scroller) return
  groupPointerDown.value = true
  groupDragging.value = false
  suppressNextGroupClick.value = false
  clearSuppressGroupClickTimer()
  groupDragStartX = event.clientX
  groupDragStartY = event.clientY
  groupDragStartScrollLeft = scroller.scrollLeft
}

function moveGroupDrag(event: PointerEvent) {
  if (event.pointerType === 'touch' || !groupPointerDown.value) return
  const scroller = groupScroller.value
  if (!scroller) return
  const deltaX = event.clientX - groupDragStartX
  const deltaY = event.clientY - groupDragStartY

  if (!groupDragging.value) {
    if (Math.abs(deltaX) < groupDragThreshold || Math.abs(deltaX) <= Math.abs(deltaY)) return
    groupDragging.value = true
    scroller.setPointerCapture(event.pointerId)
  }

  scroller.scrollLeft = groupDragStartScrollLeft - deltaX
}

function resetGroupDrag(event: PointerEvent) {
  const wasDragging = groupDragging.value
  groupPointerDown.value = false
  groupDragging.value = false

  if (groupScroller.value?.hasPointerCapture(event.pointerId)) {
    groupScroller.value.releasePointerCapture(event.pointerId)
  }

  if (wasDragging) {
    suppressNextGroupClick.value = true
    clearSuppressGroupClickTimer()
    suppressGroupClickTimer = window.setTimeout(() => {
      suppressNextGroupClick.value = false
    }, 250)
  }
}

watch(query, () => {
  window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(loadLiveData, 250)
})

watch(selectedGroupId, loadLiveData)

onMounted(loadLiveData)

onBeforeUnmount(() => {
  window.clearTimeout(searchTimer)
  clearSuppressGroupClickTimer()
})
</script>

<template>
  <section class="grid gap-5 pb-24 sm:gap-6 sm:pb-28">
    <div class="glass-panel rounded-[2rem] p-5 sm:rounded-[2.5rem] sm:p-8">
      <div>
        <div>
          <p class="text-sm uppercase tracking-[0.28em] text-white/42">Live TV</p>
          <h2 class="mt-3 text-3xl font-semibold text-white sm:text-5xl xl:text-6xl">{{ selectedGroupName }}</h2>
          <p class="mt-3 max-w-3xl text-sm leading-6 text-white/58">
            Browse imported channels and play a selected stream directly in this page.
          </p>
        </div>
      </div>
    </div>

    <LivePlayer :playback="playback" />

    <div class="grid gap-4 pb-6 xl:content-start xl:pb-0">
      <div class="glass-panel rounded-[1.5rem] p-3 sm:rounded-[2rem] sm:p-4">
        <div class="flex w-full flex-col gap-3 sm:flex-row">
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

      <div
        ref="groupScroller"
        class="chip-scroller -mx-1 cursor-grab overflow-x-auto overscroll-x-contain px-1 pb-1 active:cursor-grabbing [scrollbar-width:none]"
        @pointerdown="startGroupDrag"
        @pointermove="moveGroupDrag"
        @pointerup="resetGroupDrag"
        @pointercancel="resetGroupDrag"
        @pointerleave="resetGroupDrag"
        @lostpointercapture="resetGroupDrag"
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

      <div v-if="loading && channels.length === 0" class="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6">
        <div v-for="index in 12" :key="index" class="glass-panel aspect-square animate-pulse rounded-[1.5rem]"></div>
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

      <div v-else class="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6">
        <LiveChannelCard
          v-for="channel in channels"
          :key="channel.id"
          :channel="channel"
          :selected="playback.selectedChannelId.value === channel.id"
          :toggling="togglingIds.has(channel.id)"
          @select="selectChannel"
          @toggle="toggleChannel"
        />
      </div>
    </div>
  </section>
</template>

<style scoped>
.chip-scroller::-webkit-scrollbar {
  display: none;
}
</style>
