<script setup lang="ts">
import { NButton } from 'naive-ui'

import type { VodPlaySourceSummary } from '@/api/sourceConfigs'

defineProps<{
  playSources: VodPlaySourceSummary[]
  episodeLoadingKey: string | null
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
      class="rounded-[1.25rem] border border-white/10 bg-white/6 p-4"
    >
      <div class="flex flex-wrap items-center justify-between gap-3">
        <h4 class="text-sm font-semibold text-white">{{ group.source_name }}</h4>
        <div class="flex flex-wrap gap-2 text-xs text-white/60">
          <span class="rounded-full border border-white/10 bg-black/18 px-3 py-1">{{ group.episode_count }} episodes</span>
          <span class="rounded-full border border-white/10 bg-black/18 px-3 py-1">{{ group.has_play_urls ? 'URLs stored' : 'No URLs' }}</span>
        </div>
      </div>
      <div class="mt-3 flex flex-wrap gap-2">
        <span
          v-for="episode in group.sample_episode_names"
          :key="episode"
          class="rounded-full border border-white/10 bg-black/18 px-3 py-1 text-xs text-white/64"
        >
          {{ episode }}
        </span>
      </div>
      <div class="mt-4 flex flex-wrap gap-2">
        <NButton
          v-for="(episodeName, episodeIndex) in group.episode_names"
          :key="`${group.source_name}-${episodeIndex}-${episodeName}`"
          round
          secondary
          size="small"
          :loading="episodeLoadingKey === `${group.source_name}:${episodeIndex}`"
          @click="emit('playEpisode', group.source_name, episodeIndex)"
        >
          {{ episodeName }}
        </NButton>
      </div>
    </article>
    <p v-if="playSources.length === 0" class="text-sm text-white/54">
      No play source groups were returned by the collector.
    </p>
  </div>
</template>
