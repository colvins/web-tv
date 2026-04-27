<script setup lang="ts">
import { Tv } from 'lucide-vue-next'

import type { LiveChannel } from '@/api/sourceConfigs'

const props = defineProps<{
  channel: LiveChannel
  selected: boolean
}>()

defineEmits<{
  select: [channel: LiveChannel]
}>()
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
        <h3 class="line-clamp-2 text-center text-sm font-semibold leading-5 text-white sm:text-base">
          {{ channel.name }}
        </h3>
      </div>
    </div>
  </article>
</template>
