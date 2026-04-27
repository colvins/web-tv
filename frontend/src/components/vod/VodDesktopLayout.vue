<script setup lang="ts">
import { NButton } from 'naive-ui'

import type { VodBrowseCategory, VodBrowseItem } from '@/api/sourceConfigs'
import VodCatalogGrid from '@/components/vod/VodCatalogGrid.vue'
import VodCategoryChips from '@/components/vod/VodCategoryChips.vue'

defineProps<{
  currentSourceName: string
  pageLabel: string
  loadError: string | null
  loading: boolean
  noUsableSource: boolean
  selectedSourceId: string | null
  selectedCategoryId: string | null
  sourceLoading: boolean
  searchLoading: boolean
  categories: VodBrowseCategory[]
  items: VodBrowseItem[]
  canGoPrev: boolean
  canGoNext: boolean
  isSearchMode: boolean
  submittedQuery: string
  pagecount: number
}>()

const emit = defineEmits<{
  selectCategory: [categoryId: string | null]
  selectItem: [item: VodBrowseItem]
  changePage: [direction: -1 | 1]
}>()
</script>

<template>
  <section class="grid gap-6">
    <div v-if="loadError" class="glass-panel rounded-[2rem] border border-red-300/18 bg-red-400/10 p-5 text-red-100">
      {{ loadError }}
    </div>

    <div
      v-if="!loading && noUsableSource"
      class="glass-panel flex min-h-[24rem] items-end rounded-[2.5rem] p-7 sm:p-10"
    >
      <div class="max-w-3xl">
        <p class="text-sm uppercase tracking-[0.28em] text-white/42">No VOD source</p>
        <h2 class="mt-3 text-4xl font-semibold text-white sm:text-6xl">No VOD source is ready yet</h2>
        <p class="mt-5 text-base leading-7 text-white/58">Add or enable a source with catalog data in Source Settings.</p>
      </div>
    </div>

    <template v-else>
      <article class="glass-panel rounded-[2.25rem] p-6 sm:p-8">
        <div class="grid gap-2">
          <p class="text-sm uppercase tracking-[0.28em] text-white/38">Current source</p>
          <h2 class="text-2xl font-semibold text-white sm:text-3xl">{{ currentSourceName }}</h2>
        </div>
        <VodCategoryChips
          :categories="categories"
          :selected-category-id="selectedCategoryId"
          @select="(categoryId) => emit('selectCategory', categoryId)"
        />
      </article>

      <VodCatalogGrid
        :items="items"
        :loading="sourceLoading || searchLoading"
        @select-item="(item) => emit('selectItem', item)"
      />
    </template>

    <div
      v-if="!loading && !noUsableSource && !selectedSourceId"
      class="glass-panel flex min-h-[18rem] items-end rounded-[2.5rem] p-7 sm:p-10"
    >
      <div class="max-w-3xl">
        <p class="text-sm uppercase tracking-[0.28em] text-white/42">No source selected</p>
        <h2 class="mt-3 text-3xl font-semibold text-white sm:text-5xl">Choose a VOD source to begin browsing</h2>
        <p class="mt-5 text-base leading-7 text-white/58">Enable a source with catalog data to open its catalog.</p>
      </div>
    </div>

    <div
      v-if="!loading && !sourceLoading && !searchLoading && !noUsableSource && selectedSourceId && !items.length"
      class="glass-panel flex min-h-[18rem] items-end rounded-[2.5rem] p-7 sm:p-10"
    >
      <div class="max-w-3xl">
        <p class="text-sm uppercase tracking-[0.28em] text-white/42">No titles</p>
        <h2 class="mt-3 text-3xl font-semibold text-white sm:text-5xl">
          {{ isSearchMode ? 'No results matched the current search' : 'No titles were returned for this view' }}
        </h2>
      </div>
    </div>

    <article v-if="pagecount > 0" class="glass-panel rounded-[2rem] p-5">
      <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <p class="text-sm text-white/52">
          {{ isSearchMode ? `Search: ${submittedQuery}` : `Category: ${selectedCategoryId ?? 'All'}` }}
        </p>
        <div class="flex items-center gap-3">
          <NButton round secondary :disabled="!canGoPrev" @click="emit('changePage', -1)">Previous</NButton>
          <span class="min-w-24 text-center text-sm text-white/64">{{ pageLabel }}</span>
          <NButton round secondary :disabled="!canGoNext" @click="emit('changePage', 1)">Next</NButton>
        </div>
      </div>
    </article>
  </section>
</template>
