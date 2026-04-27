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
  <div class="grid gap-3" :class="compact ? '' : 'xl:grid-cols-[15rem_minmax(0,1fr)_auto]'">
    <div class="min-w-0">
      <NSelect
        :value="selectedSourceId"
        :options="sourceOptions"
        placeholder="Select a source"
        :loading="loading || sourceLoading"
        @update:value="(value) => emit('update:selectedSourceId', value)"
      />
    </div>

    <div class="flex min-w-0 flex-col gap-3" :class="compact ? '' : 'sm:flex-row'">
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

    <div class="flex items-center gap-2" :class="compact ? 'justify-end' : 'justify-start xl:justify-end'">
      <RouterLink
        to="/settings/sources"
        class="tv-focus-card inline-flex min-h-11 items-center rounded-full border border-white/10 bg-white/6 px-4 text-sm text-white/82 transition hover:bg-white/10"
      >
        <Settings class="mr-2 h-4 w-4" aria-hidden="true" />
        <span :class="compact ? 'hidden sm:inline' : ''">Source Settings</span>
        <span v-if="compact" class="sm:hidden">Settings</span>
      </RouterLink>
      <NButton quaternary circle :loading="loading || sourceLoading" @click="emit('refresh')">
        <template #icon><RefreshCw class="h-4 w-4" /></template>
      </NButton>
    </div>
  </div>
</template>

<style scoped>
:deep(.n-base-selection) {
  min-height: 44px;
}

:deep(.n-input) {
  --n-height: 44px;
}

:deep(.n-input__input-el),
:deep(.n-base-selection-label) {
  font-size: 0.95rem;
}
</style>
