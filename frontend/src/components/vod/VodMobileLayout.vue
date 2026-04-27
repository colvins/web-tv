<script setup lang="ts">
import { NButton } from 'naive-ui'

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
  <section class="grid gap-4 pb-[calc(7rem+env(safe-area-inset-bottom))]">
    <div class="grid gap-4">
      <div class="min-w-0">
        <p class="text-xs uppercase tracking-[0.24em] text-white/42">WEB-TV</p>
        <h1 class="mt-2 truncate text-2xl font-semibold text-white">{{ headerSourceName }}</h1>
      </div>

      <VodSourceSelector
        compact
        :source-options="sourceOptions"
        :selected-source-id="selectedSourceId"
        :search-query="searchQuery"
        :loading="loading"
        :source-loading="sourceLoading"
        :search-loading="searchLoading"
        :has-search-filter="hasSearchFilter"
        @refresh="emit('refresh')"
        @update:selected-source-id="(value) => emit('update:selectedSourceId', value)"
        @update:search-query="(value) => emit('update:searchQuery', value)"
        @search="emit('search')"
        @reset="emit('reset')"
      />
    </div>

    <div v-if="loadError" class="glass-panel rounded-[1.5rem] border border-red-300/18 bg-red-400/10 p-4 text-red-100">
      {{ loadError }}
    </div>

    <div
      v-if="!loading && noUsableSource"
      class="glass-panel flex min-h-[16rem] items-end rounded-[1.75rem] p-5"
    >
      <div>
        <p class="text-xs uppercase tracking-[0.24em] text-white/42">没有可用源</p>
        <h2 class="mt-3 text-2xl font-semibold text-white">当前没有可浏览的 VOD 源</h2>
      </div>
    </div>

    <template v-else>
      <article class="glass-panel rounded-[1.5rem] p-4">
        <VodCategoryChips
          compact
          :categories="categories"
          :selected-category-id="selectedCategoryId"
          @select="(categoryId) => emit('selectCategory', categoryId)"
        />
      </article>

      <div
        v-if="!loading && !sourceLoading && !searchLoading && !selectedSourceId"
        class="glass-panel flex min-h-[12rem] items-end rounded-[1.75rem] p-5"
      >
        <div>
          <p class="text-xs uppercase tracking-[0.24em] text-white/42">未选择源</p>
          <h2 class="mt-3 text-2xl font-semibold text-white">先选择一个 VOD 源</h2>
        </div>
      </div>

      <div
        v-else-if="!loading && !sourceLoading && !searchLoading && selectedSourceId && !items.length"
        class="glass-panel flex min-h-[12rem] items-end rounded-[1.75rem] p-5"
      >
        <div>
          <p class="text-xs uppercase tracking-[0.24em] text-white/42">没有内容</p>
          <h2 class="mt-3 text-2xl font-semibold text-white">
            {{ isSearchMode ? '没有找到匹配内容' : '当前视图没有返回影片' }}
          </h2>
        </div>
      </div>

      <VodCatalogGrid
        :items="items"
        :loading="sourceLoading || searchLoading"
        mobile
        @select-item="(item) => emit('selectItem', item)"
      />
    </template>

    <article v-if="pagecount > 0" class="glass-panel rounded-[1.5rem] p-4">
      <div class="grid gap-3">
        <p class="text-xs text-white/52">
          {{ isSearchMode ? `搜索：${submittedQuery}` : `分类：${selectedCategoryId ?? '全部'}` }}
        </p>
        <div class="flex items-center gap-3">
          <NButton round secondary class="flex-1" :disabled="!canGoPrev" @click="emit('changePage', -1)">上一页</NButton>
          <span class="min-w-16 text-center text-xs text-white/64">{{ pageLabel }}</span>
          <NButton round secondary class="flex-1" :disabled="!canGoNext" @click="emit('changePage', 1)">下一页</NButton>
        </div>
      </div>
    </article>
  </section>
</template>
