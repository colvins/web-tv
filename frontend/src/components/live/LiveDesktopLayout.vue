<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Search, SlidersHorizontal } from 'lucide-vue-next'
import { NButton, NInput } from 'naive-ui'

import LiveChannelCard from '@/components/live/LiveChannelCard.vue'
import LivePlayer from '@/components/live/LivePlayer.vue'
import type { LivePlayback } from '@/composables/useLivePlayback'
import type { LiveChannel, LiveChannelGroup } from '@/api/sourceConfigs'

const props = defineProps<{
  groups: LiveChannelGroup[]
  channels: LiveChannel[]
  selectedGroupId: string | null
  selectedGroupName: string
  query: string
  loading: boolean
  togglingIds: Set<string>
  playback: LivePlayback
}>()

const emit = defineEmits<{
  'update:query': [value: string]
  refresh: []
  selectGroup: [groupId: string | null]
  selectChannel: [channel: LiveChannel]
  toggleChannel: [channel: LiveChannel, enabled: boolean]
}>()

const queryModel = computed({
  get: () => props.query,
  set: (value: string) => emit('update:query', value),
})

const groupScroller = ref<HTMLElement | null>(null)
const stickyLiveArea = ref<HTMLElement | null>(null)
const groupPointerDown = ref(false)
const groupDragging = ref(false)
const suppressNextGroupClick = ref(false)
const stickyCompact = ref(false)

let suppressGroupClickTimer: number | undefined
let groupDragStartX = 0
let groupDragStartY = 0
let groupDragStartScrollLeft = 0
const groupDragThreshold = 6

function updateStickyCompact() {
  const top = stickyLiveArea.value?.getBoundingClientRect().top ?? 0
  stickyCompact.value = window.scrollY > 120 && top <= 24
}

function clearSuppressGroupClickTimer() {
  window.clearTimeout(suppressGroupClickTimer)
  suppressGroupClickTimer = undefined
}

function selectGroup(groupId: string | null) {
  if (suppressNextGroupClick.value) {
    suppressNextGroupClick.value = false
    clearSuppressGroupClickTimer()
    return
  }
  emit('selectGroup', groupId)
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

onMounted(() => {
  updateStickyCompact()
  window.addEventListener('scroll', updateStickyCompact, { passive: true })
  window.addEventListener('resize', updateStickyCompact)
})

onBeforeUnmount(() => {
  clearSuppressGroupClickTimer()
  window.removeEventListener('scroll', updateStickyCompact)
  window.removeEventListener('resize', updateStickyCompact)
})
</script>

<template>
  <section class="grid gap-6 pb-28">
    <div class="glass-panel rounded-[2.5rem] p-8">
      <p class="text-sm uppercase tracking-[0.28em] text-white/42">Live TV</p>
      <h2 class="mt-3 text-5xl font-semibold text-white xl:text-6xl">{{ selectedGroupName }}</h2>
      <p class="mt-3 max-w-3xl text-sm leading-6 text-white/58">
        Browse imported channels and play a selected stream directly in this page.
      </p>
    </div>

    <div
      ref="stickyLiveArea"
      class="live-sticky-area relative grid gap-4 rounded-[2rem] transition-all duration-300 md:sticky md:top-3 md:z-40 md:-mx-3 md:px-3 md:py-3 lg:top-5 xl:top-6"
      :class="stickyCompact ? 'md:gap-3' : ''"
    >
      <LivePlayer :playback="playback" :compact="stickyCompact" />

      <div
        class="grid gap-3 rounded-[2rem] border border-white/10 bg-black/56 p-4 shadow-[0_18px_64px_rgba(0,0,0,0.28)] backdrop-blur-2xl"
      >
        <div class="flex w-full gap-3">
          <NInput v-model:value="queryModel" round clearable placeholder="Search channels" class="w-full xl:w-80">
            <template #prefix><Search class="h-4 w-4 text-white/42" /></template>
          </NInput>
          <NButton round secondary :loading="loading" class="min-h-12" @click="$emit('refresh')">
            <template #icon><SlidersHorizontal class="h-4 w-4" /></template>
            Refresh
          </NButton>
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
              class="tv-focus-card shrink-0 rounded-full border px-6 py-3.5 text-sm transition"
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
              class="tv-focus-card shrink-0 rounded-full border px-6 py-3.5 text-sm transition"
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
      </div>
    </div>

    <div class="live-channel-content grid gap-4 pb-6 xl:content-start xl:pb-0">
      <div v-if="loading && channels.length === 0" class="grid grid-cols-4 gap-3 xl:grid-cols-5 2xl:grid-cols-6">
        <div v-for="index in 12" :key="index" class="glass-panel aspect-square animate-pulse rounded-[1.5rem]"></div>
      </div>

      <div
        v-else-if="channels.length === 0"
        class="glass-panel flex min-h-72 items-end rounded-[2.5rem] p-10"
      >
        <div>
          <p class="text-sm uppercase tracking-[0.28em] text-white/42">No Channels</p>
          <h2 class="mt-3 max-w-2xl text-5xl font-semibold">Import and extract a live M3U source first.</h2>
        </div>
      </div>

      <div v-else class="grid grid-cols-4 gap-3 xl:grid-cols-5 2xl:grid-cols-6">
        <LiveChannelCard
          v-for="channel in channels"
          :key="channel.id"
          :channel="channel"
          :selected="playback.selectedChannelId.value === channel.id"
          :toggling="togglingIds.has(channel.id)"
          @select="$emit('selectChannel', $event)"
          @toggle="(channel, enabled) => $emit('toggleChannel', channel, enabled)"
        />
      </div>
    </div>
  </section>
</template>

<style scoped>
.chip-scroller::-webkit-scrollbar {
  display: none;
}

.live-sticky-area {
  --live-sticky-safe-offset: clamp(2.5rem, 4vw, 4.5rem);
  isolation: isolate;
}

.live-channel-content {
  margin-top: var(--live-sticky-safe-offset);
  scroll-margin-top: var(--live-sticky-safe-offset);
}

.live-sticky-area::before {
  content: '';
  position: absolute;
  inset: 0;
  z-index: -1;
  border-radius: 2rem;
  background: linear-gradient(180deg, rgb(5 5 7 / 0.86), rgb(5 5 7 / 0.52) 74%, rgb(5 5 7 / 0));
  backdrop-filter: blur(22px);
  -webkit-backdrop-filter: blur(22px);
  pointer-events: none;
}

.live-sticky-area::after {
  content: '';
  position: absolute;
  left: 0.75rem;
  right: 0.75rem;
  bottom: -2rem;
  height: 2.5rem;
  z-index: -1;
  background: linear-gradient(180deg, rgb(5 5 7 / 0.42), rgb(5 5 7 / 0));
  filter: blur(10px);
  pointer-events: none;
}
</style>
