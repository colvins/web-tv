<script setup lang="ts">
import { computed } from 'vue'

import type { VodPlaySourceSummary } from '@/api/sourceConfigs'

const props = withDefaults(defineProps<{
  playSources: VodPlaySourceSummary[]
  sourceName?: string | null
  episodeLoadingKey: string | null
  selectedSourceName: string | null
  selectedEpisodeIndex: number | null
  compact?: boolean
}>(), {
  sourceName: null,
  compact: false,
})

const emit = defineEmits<{
  playEpisode: [sourceName: string, episodeIndex: number]
}>()

const visibleSources = computed(() => {
  const preferredName = props.sourceName ?? props.selectedSourceName ?? props.playSources[0]?.source_name ?? null
  if (!preferredName) return props.playSources.slice(0, 1)
  const matched = props.playSources.filter((group) => group.source_name === preferredName)
  return matched.length ? matched : props.playSources.slice(0, 1)
})
</script>

<template>
  <div class="grid gap-3">
    <article
      v-for="group in visibleSources"
      :key="group.source_name"
      class="rounded-[1.25rem] border transition-colors"
      :class="[
        compact ? 'p-0' : 'p-0',
        selectedSourceName === group.source_name
          ? 'border-white/24 bg-white/10'
          : 'border-white/10 bg-white/6',
      ]"
    >
      <div
        :class="compact ? 'grid grid-cols-3 gap-2 p-2 sm:grid-cols-4' : 'grid grid-cols-4 gap-2 p-3 xl:grid-cols-5'"
      >
        <button
          v-for="(episodeName, episodeIndex) in group.episode_names"
          :key="`${group.source_name}-${episodeIndex}-${episodeName}`"
          type="button"
          class="rounded-full border transition disabled:cursor-wait disabled:opacity-70"
          :class="[
            compact ? 'min-h-9 px-3 py-1.5 text-xs' : 'min-h-10 px-3 py-1.5 text-sm',
            selectedSourceName === group.source_name && selectedEpisodeIndex === episodeIndex
              ? 'border-white/32 bg-white text-black'
              : 'border-white/12 bg-black/18 text-white/82 hover:border-white/22 hover:bg-white/10',
          ]"
          :disabled="episodeLoadingKey === `${group.source_name}:${episodeIndex}`"
          @click="emit('playEpisode', group.source_name, episodeIndex)"
        >
          <span class="block truncate">
            {{ episodeLoadingKey === `${group.source_name}:${episodeIndex}` ? `加载 ${episodeName}` : episodeName }}
          </span>
        </button>
      </div>
    </article>
    <p v-if="playSources.length === 0" class="text-sm text-white/54">
      当前源没有返回可播放分组。
    </p>
  </div>
</template>
