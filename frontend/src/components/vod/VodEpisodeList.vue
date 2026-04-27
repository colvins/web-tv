<script setup lang="ts">
import type { VodPlaySourceSummary } from '@/api/sourceConfigs'

withDefaults(defineProps<{
  playSources: VodPlaySourceSummary[]
  episodeLoadingKey: string | null
  selectedSourceName: string | null
  selectedEpisodeIndex: number | null
  compact?: boolean
}>(), {
  compact: false,
})

const emit = defineEmits<{
  playEpisode: [sourceName: string, episodeIndex: number]
}>()
</script>

<template>
  <div class="grid gap-3">
    <article
      v-for="group in playSources"
      :key="group.source_name"
      class="rounded-[1.5rem] border transition-colors"
      :class="[
        compact ? 'p-3' : 'p-4',
        selectedSourceName === group.source_name
          ? 'border-white/24 bg-white/10'
          : 'border-white/10 bg-white/6',
      ]"
    >
      <div class="flex flex-wrap items-center justify-between gap-3">
        <h4 class="font-semibold text-white" :class="compact ? 'text-xs' : 'text-sm'">{{ group.source_name }}</h4>
        <span class="rounded-full border border-white/10 bg-black/18 px-3 py-1 text-xs text-white/60">
          {{ group.episode_count }} 集
        </span>
      </div>
      <div
        class="mt-4"
        :class="compact ? 'grid grid-cols-3 gap-2 sm:grid-cols-4' : 'flex flex-wrap gap-2'"
      >
        <button
          v-for="(episodeName, episodeIndex) in group.episode_names"
          :key="`${group.source_name}-${episodeIndex}-${episodeName}`"
          type="button"
          class="rounded-full border transition disabled:cursor-wait disabled:opacity-70"
          :class="[
            compact ? 'min-h-9 px-3 py-1.5 text-xs' : 'min-h-11 px-4 py-2 text-sm',
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
