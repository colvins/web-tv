<script setup lang="ts">
import { RefreshCw, Search } from 'lucide-vue-next'
import { NButton, NInput, NSelect } from 'naive-ui'

withDefaults(defineProps<{
  sourceOptions: Array<{ label: string; value: string }>
  selectedSourceId: string | null
  searchQuery: string
  loading: boolean
  sourceLoading: boolean
  searchLoading: boolean
  compact?: boolean
}>(), {
  compact: false,
})

const emit = defineEmits<{
  refresh: []
  'update:selectedSourceId': [value: string | null]
  'update:searchQuery': [value: string]
  search: []
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
      </div>
    </div>

    <div class="flex items-center gap-2" :class="compact ? 'justify-end' : 'justify-start xl:justify-end'">
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
