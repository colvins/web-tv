<script setup lang="ts">
import { Search } from 'lucide-vue-next'
import { NButton, NInput, NSelect } from 'naive-ui'

defineProps<{
  sourceOptions: Array<{ label: string; value: string }>
  selectedSourceId: string | null
  searchQuery: string
  loading: boolean
  sourceLoading: boolean
  searchLoading: boolean
  hasSearchFilter: boolean
}>()

const emit = defineEmits<{
  'update:selectedSourceId': [value: string | null]
  'update:searchQuery': [value: string]
  search: []
  reset: []
}>()
</script>

<template>
  <article class="glass-panel rounded-[2.25rem] p-6 sm:p-8">
    <div class="grid gap-4 xl:grid-cols-[minmax(0,20rem)_minmax(0,1fr)]">
      <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-5">
        <p class="text-sm uppercase tracking-[0.18em] text-white/42">Source</p>
        <NSelect
          class="mt-4"
          :value="selectedSourceId"
          :options="sourceOptions"
          placeholder="Select a source"
          :loading="loading || sourceLoading"
          @update:value="(value) => emit('update:selectedSourceId', value)"
        />
      </div>

      <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-5">
        <div class="flex flex-col gap-4 lg:flex-row">
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
        <p class="mt-4 text-sm text-white/48">Choose a source, browse categories, or search by title.</p>
      </div>
    </div>
  </article>
</template>
