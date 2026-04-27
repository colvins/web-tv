<script setup lang="ts">
import { computed } from 'vue'
import { Tv } from 'lucide-vue-next'
import { NSwitch } from 'naive-ui'

import type { LiveChannel } from '@/api/sourceConfigs'
import type { ChannelPlaybackStatus } from '@/composables/useLivePlayback'

const props = defineProps<{
  channel: LiveChannel
  selected: boolean
  toggling: boolean
  playbackStatus: ChannelPlaybackStatus
}>()

defineEmits<{
  select: [channel: LiveChannel]
  toggle: [channel: LiveChannel, enabled: boolean]
}>()

const playbackBadgeLabel = computed(() => {
  switch (props.playbackStatus) {
    case 'playing':
      return 'Playable'
    case 'failed':
      return 'Failed'
    default:
      return ''
  }
})
</script>

<template>
  <article
    tabindex="0"
    class="tv-focus-card glass-panel group flex aspect-square min-h-0 cursor-pointer flex-col overflow-hidden rounded-[1.35rem] border transition sm:rounded-[1.6rem]"
    :class="
      selected
        ? 'border-aurora/50 bg-aurora/12 shadow-[0_0_0_1px_rgba(120,220,255,0.12)]'
        : 'border-white/10 bg-white/[0.03] hover:border-white/20'
    "
    @click="$emit('select', channel)"
    @keydown.enter.prevent="$emit('select', channel)"
    @keydown.space.prevent="$emit('select', channel)"
  >
    <div class="flex h-full flex-col p-3 sm:p-4">
      <div class="flex min-h-0 flex-1 items-center justify-center rounded-[1.15rem] bg-white/7 p-3">
        <img
          v-if="channel.tvg_logo"
          :src="channel.tvg_logo"
          :alt="channel.name"
          class="max-h-16 max-w-[86%] object-contain sm:max-h-20"
          loading="lazy"
        />
        <Tv v-else class="h-9 w-9 text-white/62 sm:h-10 sm:w-10" />
      </div>
      <div class="mt-3 min-w-0">
        <div class="flex items-start justify-between gap-2">
          <div class="min-w-0">
            <div v-if="playbackStatus !== 'unknown'" class="mb-2">
              <span
                class="inline-flex items-center rounded-full border px-2 py-1 text-[10px] uppercase tracking-[0.2em]"
                :class="
                  playbackStatus === 'playing'
                    ? 'border-emerald-300/24 bg-emerald-400/12 text-emerald-100'
                    : 'border-rose-300/24 bg-rose-400/12 text-rose-100'
                "
              >
                {{ playbackBadgeLabel }}
              </span>
            </div>
            <h3 class="line-clamp-2 text-sm font-semibold leading-5 text-white sm:text-base">
              {{ channel.name }}
            </h3>
            <p class="mt-1 truncate text-xs text-white/46">{{ channel.group_title ?? 'Ungrouped' }}</p>
          </div>
          <NSwitch
            :value="channel.enabled"
            :loading="toggling"
            @click.stop
            @update:value="(value) => $emit('toggle', channel, value)"
          />
        </div>
        <p class="mt-2 truncate font-mono text-[10px] leading-4 text-white/22 opacity-0 transition group-hover:opacity-100">
          {{ channel.stream_url }}
        </p>
      </div>
    </div>
  </article>
</template>
