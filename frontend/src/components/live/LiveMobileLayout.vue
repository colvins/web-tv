<script setup lang="ts">
import { computed } from 'vue'
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
</script>

<template>
  <section class="grid gap-5 pb-24 sm:gap-6 sm:pb-28">
    <div class="glass-panel rounded-[2rem] p-5 sm:rounded-[2.5rem] sm:p-8">
      <p class="text-sm uppercase tracking-[0.28em] text-white/42">Live TV</p>
      <h2 class="mt-3 text-3xl font-semibold text-white sm:text-5xl">{{ selectedGroupName }}</h2>
      <p class="mt-3 max-w-3xl text-sm leading-6 text-white/58">
        Browse imported channels and play a selected stream directly in this page.
      </p>
    </div>

    <LivePlayer :playback="playback" />

    <div class="grid gap-4 pb-6">
      <div class="glass-panel rounded-[1.5rem] p-3 sm:rounded-[2rem] sm:p-4">
        <div class="flex w-full flex-col gap-3 sm:flex-row">
          <NInput v-model:value="queryModel" round clearable placeholder="Search channels" class="w-full sm:min-w-72">
            <template #prefix><Search class="h-4 w-4 text-white/42" /></template>
          </NInput>
          <NButton round secondary :loading="loading" class="min-h-12" @click="$emit('refresh')">
            <template #icon><SlidersHorizontal class="h-4 w-4" /></template>
            Refresh
          </NButton>
        </div>
      </div>

      <div class="chip-scroller -mx-1 overflow-x-auto overscroll-x-contain px-1 pb-1 [scrollbar-width:none]">
        <div class="flex min-w-max flex-nowrap gap-3">
          <button
            class="tv-focus-card shrink-0 rounded-full border px-5 py-3 text-sm transition sm:px-6 sm:py-3.5"
            :class="
              selectedGroupId === null
                ? 'border-aurora/40 bg-aurora/18 text-white'
                : 'border-white/10 bg-white/6 text-white/62'
            "
            @click="$emit('selectGroup', null)"
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
            @click="$emit('selectGroup', group.id)"
          >
            {{ group.name }}
            <span class="ml-2 text-white/42">{{ group.channel_count }}</span>
          </button>
        </div>
      </div>

      <div v-if="loading && channels.length === 0" class="grid grid-cols-2 gap-3">
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

      <div v-else class="grid grid-cols-2 gap-3">
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
</style>
