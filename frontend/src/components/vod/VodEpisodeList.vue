<script setup lang="ts">
import type { VodPlaySourceSummary } from '@/api/sourceConfigs'

defineProps<{
  playSources: VodPlaySourceSummary[]
  episodeLoadingKey: string | null
  selectedSourceName: string | null
  selectedEpisodeIndex: number | null
}>()

const emit = defineEmits<{
  playEpisode: [sourceName: string, episodeIndex: number]
}>()
</script>

<template>
  <div class="mt-4 grid gap-3">
    <article
      v-for="group in playSources"
      :key="group.source_name"
      class="rounded-[1.5rem] border p-4 transition-colors"
      :class="
        selectedSourceName === group.source_name
          ? 'border-white/24 bg-white/10'
          : 'border-white/10 bg-white/6'
      "
    >
      <div class="flex flex-wrap items-center justify-between gap-3">
        <h4 class="text-sm font-semibold text-white">{{ group.source_name }}</h4>
        <span class="rounded-full border border-white/10 bg-black/18 px-3 py-1 text-xs text-white/60">
          {{ group.episode_count }} episodes
        </span>
      </div>
      <div class="mt-4 flex flex-wrap gap-2">
        <button
          v-for="(episodeName, episodeIndex) in group.episode_names"
          :key="`${group.source_name}-${episodeIndex}-${episodeName}`"
          type="button"
          class="min-h-11 rounded-full border px-4 py-2 text-sm transition disabled:cursor-wait disabled:opacity-70"
          :class="
            selectedSourceName === group.source_name && selectedEpisodeIndex === episodeIndex
              ? 'border-white/32 bg-white text-black'
              : 'border-white/12 bg-black/18 text-white/82 hover:border-white/22 hover:bg-white/10'
          "
          :disabled="episodeLoadingKey === `${group.source_name}:${episodeIndex}`"
          @click="emit('playEpisode', group.source_name, episodeIndex)"
        >
          {{ episodeLoadingKey === `${group.source_name}:${episodeIndex}` ? `Loading ${episodeName}` : episodeName }}
        </button>
      </div>
    </article>
    <p v-if="playSources.length === 0" class="text-sm text-white/54">
      No play source groups were returned by the collector.
    </p>
  </div>
</template>
