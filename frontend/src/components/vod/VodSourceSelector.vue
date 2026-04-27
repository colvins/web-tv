<script setup lang="ts">
import { RefreshCw, Search, Settings } from 'lucide-vue-next'
import { NButton, NInput, NSelect } from 'naive-ui'
import { RouterLink } from 'vue-router'

withDefaults(defineProps<{
  sourceOptions: Array<{ label: string; value: string }>
  selectedSourceId: string | null
  searchQuery: string
  loading: boolean
  sourceLoading: boolean
  searchLoading: boolean
  hasSearchFilter: boolean
  compact?: boolean
}>(), {
  compact: false,
})

const emit = defineEmits<{
  refresh: []
  'update:selectedSourceId': [value: string | null]
  'update:searchQuery': [value: string]
  search: []
  reset: []
}>()
</script>

<template>
  <article class="glass-panel" :class="compact ? 'rounded-[1.5rem] p-4' : 'rounded-[2.25rem] p-6 sm:p-8'">
    <div class="grid gap-4">
      <div class="rounded-[1.5rem] border border-white/10 bg-black/18" :class="compact ? 'p-4' : 'p-5'">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <p class="text-sm uppercase tracking-[0.18em] text-white/42">Source</p>
          <div class="flex items-center gap-2">
            <RouterLink
              to="/settings/sources"
              class="tv-focus-card inline-flex min-h-11 items-center rounded-full border border-white/10 bg-white/6 px-4 text-sm text-white/82 transition hover:bg-white/10"
            >
              <Settings class="mr-2 h-4 w-4" aria-hidden="true" />
              Source Settings
            </RouterLink>
            <NButton quaternary circle :loading="loading || sourceLoading" @click="emit('refresh')">
              <template #icon><RefreshCw class="h-4 w-4" /></template>
            </NButton>
          </div>
        </div>
        <NSelect
          class="mt-4"
          :value="selectedSourceId"
          :options="sourceOptions"
          placeholder="Select a source"
          :loading="loading || sourceLoading"
          @update:value="(value) => emit('update:selectedSourceId', value)"
        />
      </div>

      <div class="rounded-[1.5rem] border border-white/10 bg-black/18" :class="compact ? 'p-4' : 'p-5'">
        <div class="flex flex-col gap-4" :class="compact ? '' : 'lg:flex-row'">
          <NInput
            :value="searchQuery"
            placeholder="Search titles"
            clearable
            @update:value="(value) => emit('update:searchQuery', value)"
            @keyup.enter="emit('search')"
          />
          <div class="flex gap-3">
            <NButton round type="primary" :loading="searchLoading" @click="emit('search')">
              <template #icon><Search class="h-4 w-4" /></template>
              Search
            </NButton>
            <NButton round secondary :disabled="!hasSearchFilter" @click="emit('reset')">
              Reset
            </NButton>
          </div>
        </div>
      </div>
    </div>
  </article>
</template>
