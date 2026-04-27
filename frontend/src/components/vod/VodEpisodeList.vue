<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import type { VodPlaySourceSummary } from '@/api/sourceConfigs'

const props = withDefaults(defineProps<{
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

const activeSourceName = ref<string | null>(null)

const visibleSources = computed(() => {
  if (props.playSources.length <= 1) return props.playSources
  const sourceName = activeSourceName.value ?? props.selectedSourceName ?? props.playSources[0]?.source_name ?? null
  return props.playSources.filter((group) => group.source_name === sourceName)
})

watch(
  () => [props.playSources, props.selectedSourceName] as const,
  ([playSources, selectedSourceName]) => {
    const fallbackName = selectedSourceName ?? playSources[0]?.source_name ?? null
    if (!fallbackName) {
      activeSourceName.value = null
      return
    }
    const stillExists = playSources.some((group) => group.source_name === activeSourceName.value)
    if (!stillExists || selectedSourceName) {
      activeSourceName.value = fallbackName
    }
  },
  { immediate: true },
)
</script>

<template>
  <div class="grid gap-3">
    <div v-if="playSources.length > 1" class="flex flex-wrap gap-2">
      <button
        v-for="group in playSources"
        :key="`tab-${group.source_name}`"
        type="button"
        class="rounded-full border px-3 py-1.5 text-xs transition"
        :class="
          activeSourceName === group.source_name
            ? 'border-white/32 bg-white text-black'
            : 'border-white/12 bg-black/18 text-white/82 hover:border-white/22 hover:bg-white/10'
        "
        @click="activeSourceName = group.source_name"
      >
        {{ group.source_name }}
      </button>
    </div>
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
