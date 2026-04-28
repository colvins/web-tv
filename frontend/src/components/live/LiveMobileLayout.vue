<script setup lang="ts">
import { computed } from 'vue'
import { Search } from 'lucide-vue-next'
import { NInput, NSelect } from 'naive-ui'

import LiveChannelCard from '@/components/live/LiveChannelCard.vue'
import LivePlayer from '@/components/live/LivePlayer.vue'
import type { LivePlayback } from '@/composables/useLivePlayback'
import type { LiveChannel, LiveChannelGroup } from '@/api/sourceConfigs'

const props = defineProps<{
  groups: LiveChannelGroup[]
  channels: LiveChannel[]
  selectedGroupId: string | null
  query: string
  loading: boolean
  playback: LivePlayback
}>()

const emit = defineEmits<{
  'update:query': [value: string]
  selectGroup: [groupId: string | null]
  selectChannel: [channel: LiveChannel]
}>()

const queryModel = computed({
  get: () => props.query,
  set: (value: string) => emit('update:query', value),
})

const ALL_GROUP_VALUE = '__all__'

const selectedGroupValue = computed(() => props.selectedGroupId ?? ALL_GROUP_VALUE)

const groupOptions = computed(() => [
  { label: 'All Groups', value: ALL_GROUP_VALUE },
  ...props.groups.map((group) => ({
    label: `${group.name} (${group.channel_count})`,
    value: group.id,
  })),
])
</script>

<template>
  <section class="grid gap-5 pb-24 sm:gap-6 sm:pb-28">
    <div class="live-mobile-sticky-player relative sticky top-2 z-30 -mx-2 px-2 pt-1 pb-2">
      <LivePlayer :playback="playback" />
    </div>

    <div class="grid gap-4">
      <div class="glass-panel rounded-[1.5rem] p-3 sm:rounded-[2rem] sm:p-4">
        <div class="flex w-full flex-col gap-3 sm:flex-row">
          <NInput v-model:value="queryModel" round clearable placeholder="Search channels" class="w-full sm:min-w-72">
            <template #prefix><Search class="h-4 w-4 text-white/42" /></template>
          </NInput>
          <NSelect
            :value="selectedGroupValue"
            :options="groupOptions"
            placeholder="Channel group"
            @update:value="(value) => emit('selectGroup', value === ALL_GROUP_VALUE ? null : String(value))"
          />
        </div>
      </div>
    </div>

    <div class="live-mobile-channel-content grid gap-4 pb-6">
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
          @select="$emit('selectChannel', $event)"
        />
      </div>
    </div>
  </section>
</template>

<style scoped>
.chip-scroller::-webkit-scrollbar {
  display: none;
}

.live-mobile-sticky-player {
  isolation: isolate;
}

.live-mobile-channel-content {
  --live-mobile-flow-gap: 1.25rem;
  margin-top: var(--live-mobile-flow-gap);
  scroll-margin-top: var(--live-mobile-flow-gap);
}

.live-mobile-sticky-player::before {
  content: '';
  position: absolute;
  inset: 0;
  z-index: -1;
  border-radius: 2rem;
  background: linear-gradient(180deg, rgb(5 5 7 / 0.95), rgb(5 5 7 / 0.72) 76%, rgb(5 5 7 / 0));
  pointer-events: none;
}

.live-mobile-sticky-player::after {
  content: '';
  position: absolute;
  left: 0.5rem;
  right: 0.5rem;
  bottom: -0.5rem;
  height: 1rem;
  z-index: -1;
  background: linear-gradient(180deg, rgb(5 5 7 / 0.18), rgb(5 5 7 / 0));
  pointer-events: none;
}
</style>
