<script setup lang="ts">
import { RefreshCw, Settings } from 'lucide-vue-next'
import { NButton } from 'naive-ui'
import { RouterLink } from 'vue-router'

import type { VodBrowseCategory, VodBrowseItem } from '@/api/sourceConfigs'
import VodCatalogGrid from '@/components/vod/VodCatalogGrid.vue'
import VodCategoryChips from '@/components/vod/VodCategoryChips.vue'
import VodSourceSelector from '@/components/vod/VodSourceSelector.vue'

defineProps<{
  headerSiteName: string
  headerSourceName: string
  pageLabel: string
  selectedSiteKey: string | null
  totalResults: number
  loadError: string | null
  loading: boolean
  noUsableSource: boolean
  selectedSourceId: string | null
  selectedCategoryId: string | null
  sourceOptions: Array<{ label: string; value: string }>
  searchQuery: string
  sourceLoading: boolean
  searchLoading: boolean
  hasSearchFilter: boolean
  categories: VodBrowseCategory[]
  items: VodBrowseItem[]
  canGoPrev: boolean
  canGoNext: boolean
  isSearchMode: boolean
  submittedQuery: string
  pagecount: number
}>()

const emit = defineEmits<{
  refresh: []
  'update:selectedSourceId': [value: string | null]
  'update:searchQuery': [value: string]
  search: []
  reset: []
  selectCategory: [categoryId: string | null]
  selectItem: [item: VodBrowseItem]
  changePage: [direction: -1 | 1]
}>()
</script>

<template>
  <section class="grid gap-6">
    <div
      class="glass-panel overflow-hidden rounded-[2.5rem] bg-[radial-gradient(circle_at_top_left,rgba(90,161,255,0.2),transparent_40%),linear-gradient(135deg,rgba(255,255,255,0.06),rgba(255,255,255,0.02))] p-7 sm:p-10"
    >
      <div class="flex flex-col gap-8 xl:flex-row xl:items-end xl:justify-between">
        <div class="max-w-4xl">
          <p class="text-sm uppercase tracking-[0.28em] text-white/44">VOD Browser</p>
          <h2 class="mt-4 text-4xl font-semibold text-white sm:text-6xl">{{ headerSiteName }}</h2>
          <p class="mt-5 max-w-3xl text-base leading-7 text-white/60">Browse titles, jump into details, and start an episode quickly.</p>
        </div>
        <div class="flex flex-wrap gap-3">
          <RouterLink
            to="/settings/sources"
            class="tv-focus-card glass-panel inline-flex min-h-12 items-center rounded-3xl px-5 text-sm font-medium"
          >
            <Settings class="mr-2 h-4 w-4" aria-hidden="true" />
            Source Settings
          </RouterLink>
          <NButton round secondary :loading="loading" @click="emit('refresh')">
            <template #icon><RefreshCw class="h-4 w-4" /></template>
            Refresh
          </NButton>
        </div>
      </div>

      <div class="mt-10 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-5">
          <p class="text-sm text-white/42">Source package</p>
          <p class="mt-2 text-lg font-semibold text-white">{{ headerSourceName }}</p>
        </div>
        <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-5">
          <p class="text-sm text-white/42">Current site</p>
          <p class="mt-2 text-lg font-semibold text-white">{{ selectedSiteKey ?? 'Not selected' }}</p>
        </div>
        <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-5">
          <p class="text-sm text-white/42">Results</p>
          <p class="mt-2 text-lg font-semibold text-white">{{ totalResults }}</p>
        </div>
        <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-5">
          <p class="text-sm text-white/42">Page</p>
          <p class="mt-2 text-lg font-semibold text-white">{{ pageLabel }}</p>
        </div>
      </div>
    </div>

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
      <VodSourceSelector
        :source-options="sourceOptions"
        :selected-source-id="selectedSourceId"
        :search-query="searchQuery"
        :loading="loading"
        :source-loading="sourceLoading"
        :search-loading="searchLoading"
        :has-search-filter="hasSearchFilter"
        @update:selected-source-id="(value) => emit('update:selectedSourceId', value)"
        @update:search-query="(value) => emit('update:searchQuery', value)"
        @search="emit('search')"
        @reset="emit('reset')"
      />

      <article class="glass-panel rounded-[2.25rem] p-6 sm:p-8">
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
        <p class="mt-5 text-base leading-7 text-white/58">Pick a source from the selector to open its catalog.</p>
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
