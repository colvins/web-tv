<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RefreshCw, Settings } from 'lucide-vue-next'
import { NButton } from 'naive-ui'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import {
  getVodCategories,
  getVodList,
  listSourceConfigs,
  searchVod,
  type SourceConfig,
  type VodBrowseCategoriesResponse,
  type VodBrowseItem,
  type VodBrowsePageResponse,
} from '@/api/sourceConfigs'
import { ApiError } from '@/api/client'
import VodCatalogGrid from '@/components/vod/VodCatalogGrid.vue'
import VodCategoryChips from '@/components/vod/VodCategoryChips.vue'
import VodSourceSelector from '@/components/vod/VodSourceSelector.vue'
import {
  buildVodCatalogQuery,
  getVodCatalogRouteKey,
  parseVodCatalogRouteState,
  type VodCatalogRouteState,
} from '@/utils/vodRouteState'

const VOD_SOURCE_STORAGE_KEY = 'webtv.vod.selectedSourceConfigId'

const route = useRoute()
const router = useRouter()
const sources = ref<SourceConfig[]>([])
const selectedSourceId = ref<string | null>(null)
const categoriesResponse = ref<VodBrowseCategoriesResponse | null>(null)
const pageResponse = ref<VodBrowsePageResponse | null>(null)
const loading = ref(false)
const sourceLoading = ref(false)
const searchLoading = ref(false)
const noUsableSource = ref(false)
const loadError = ref<string | null>(null)
const selectedCategoryId = ref<string | null>(null)
const searchQuery = ref('')
const submittedQuery = ref('')
const bootstrapped = ref(false)
const lastLoadedRouteKey = ref<string | null>(null)

const sourceOptions = computed(() =>
  sources.value
    .filter((source) => source.enabled && source.vod_site_count > 0)
    .map((source) => ({
      label: `${source.name} · ${source.vod_site_count} VOD source${source.vod_site_count > 1 ? 's' : ''}`,
      value: source.id,
    })),
)

const selectedSource = computed(
  () => sources.value.find((source) => source.id === selectedSourceId.value) ?? null,
)

const headerSiteName = computed(() => pageResponse.value?.site.site_name ?? categoriesResponse.value?.site.site_name ?? 'VOD Library')
const headerSourceName = computed(() => pageResponse.value?.site.source_name ?? categoriesResponse.value?.site.source_name ?? selectedSource.value?.name ?? 'VOD Source')
const pageLabel = computed(() => `${pageResponse.value?.page ?? 1} / ${pageResponse.value?.pagecount ?? 1}`)
const isSearchMode = computed(() => submittedQuery.value.trim().length > 0)
const canGoPrev = computed(() => (pageResponse.value?.page ?? 1) > 1)
const canGoNext = computed(() => (pageResponse.value?.page ?? 1) < (pageResponse.value?.pagecount ?? 1))
const enabledSources = computed(() => sources.value.filter((source) => source.enabled && source.vod_site_count > 0))

function normalizeRouteStateCategory(
  routeState: VodCatalogRouteState,
  categories: VodBrowseCategoriesResponse,
): VodCatalogRouteState {
  const selectedCategoryId = routeState.categoryId
  if (!selectedCategoryId) {
    return routeState
  }

  const normalizedCategories = categories.categories.map((category) => ({
    id: category.type_id === null || category.type_id === undefined ? null : String(category.type_id),
    parentId:
      category.parent_type_id === null || category.parent_type_id === undefined || String(category.parent_type_id) === '0'
        ? null
        : String(category.parent_type_id),
  }))
  const childParentIds = new Set(
    normalizedCategories
      .map((category) => category.parentId)
      .filter((parentId): parentId is string => Boolean(parentId)),
  )

  if (!childParentIds.has(selectedCategoryId)) {
    return routeState
  }

  return {
    ...routeState,
    categoryId: null,
    page: 1,
  }
}

function restoreSavedSourceId() {
  return window.localStorage.getItem(VOD_SOURCE_STORAGE_KEY)
}

function persistSelectedSourceId(sourceId: string | null) {
  if (sourceId) {
    window.localStorage.setItem(VOD_SOURCE_STORAGE_KEY, sourceId)
    return
  }
  window.localStorage.removeItem(VOD_SOURCE_STORAGE_KEY)
}

function resetVodState() {
  categoriesResponse.value = null
  pageResponse.value = null
  selectedCategoryId.value = null
  submittedQuery.value = ''
  searchQuery.value = ''
  lastLoadedRouteKey.value = null
}

function buildCatalogRouteState(overrides: Partial<VodCatalogRouteState> = {}): VodCatalogRouteState {
  return {
    sourceId: overrides.sourceId ?? selectedSourceId.value,
    categoryId: overrides.categoryId ?? selectedCategoryId.value,
    query: overrides.query ?? submittedQuery.value,
    page: overrides.page ?? pageResponse.value?.page ?? 1,
  }
}

async function fetchSourceCatalog(sourceId: string, routeState: VodCatalogRouteState) {
  const categories = await getVodCategories(sourceId)
  const normalizedRouteState = normalizeRouteStateCategory(routeState, categories)
  const page = normalizedRouteState.query
    ? await searchVod({
        source_config_id: sourceId,
        q: normalizedRouteState.query,
        page: normalizedRouteState.page,
      })
    : await getVodList({
        source_config_id: sourceId,
        type_id: normalizedRouteState.categoryId,
        page: normalizedRouteState.page,
      })
  return { categories, page, routeState: normalizedRouteState }
}

function applyCatalogState(
  sourceId: string,
  catalog: { categories: VodBrowseCategoriesResponse; page: VodBrowsePageResponse; routeState: VodCatalogRouteState },
) {
  selectedSourceId.value = sourceId
  persistSelectedSourceId(sourceId)
  categoriesResponse.value = catalog.categories
  pageResponse.value = catalog.page
  selectedCategoryId.value = catalog.routeState.categoryId
  searchQuery.value = catalog.routeState.query
  submittedQuery.value = catalog.routeState.query
  noUsableSource.value = false
  lastLoadedRouteKey.value = getVodCatalogRouteKey({ ...catalog.routeState, sourceId })
}

async function bootstrap() {
  loading.value = true
  loadError.value = null
  try {
    const sourceList = await listSourceConfigs()
    sources.value = sourceList

    const routeState = parseVodCatalogRouteState(route.query)
    const enabledIds = new Set(sourceList.filter((source) => source.enabled && source.vod_site_count > 0).map((source) => source.id))
    const currentSelection = selectedSourceId.value
    const savedSelection = restoreSavedSourceId()
    const candidateIds = [
      routeState.sourceId && enabledIds.has(routeState.sourceId) ? routeState.sourceId : null,
      currentSelection && enabledIds.has(currentSelection) ? currentSelection : null,
      savedSelection && enabledIds.has(savedSelection) ? savedSelection : null,
      ...enabledSources.value.map((source) => source.id),
    ].filter((value, index, values): value is string => Boolean(value) && values.indexOf(value) === index)

    for (const sourceId of candidateIds) {
      try {
        const catalog = await fetchSourceCatalog(sourceId, routeState)
        applyCatalogState(sourceId, catalog)
        if (routeState.sourceId !== sourceId || getVodCatalogRouteKey({ ...routeState, sourceId }) !== getVodCatalogRouteKey({ ...catalog.routeState, sourceId })) {
          await router.replace({
            name: 'vod',
            query: buildVodCatalogQuery({ ...catalog.routeState, sourceId }),
          })
        }
        return
      } catch {
        continue
      }
    }

    selectedSourceId.value = null
    persistSelectedSourceId(null)
    resetVodState()
    noUsableSource.value = true
  } catch (error) {
    loadError.value = error instanceof ApiError ? error.message : 'Unable to load VOD sources'
  } finally {
    loading.value = false
    bootstrapped.value = true
  }
}

async function syncCatalogFromRoute() {
  const routeState = parseVodCatalogRouteState(route.query)

  if (!routeState.sourceId) {
    selectedSourceId.value = null
    persistSelectedSourceId(null)
    resetVodState()
    noUsableSource.value = false
    return
  }

  const routeKey = getVodCatalogRouteKey(routeState)
  if (lastLoadedRouteKey.value === routeKey && pageResponse.value) {
    return
  }

  sourceLoading.value = true
  loadError.value = null
  noUsableSource.value = false
  try {
    const catalog = await fetchSourceCatalog(routeState.sourceId, routeState)
    applyCatalogState(routeState.sourceId, catalog)
    if (getVodCatalogRouteKey(routeState) !== getVodCatalogRouteKey(catalog.routeState)) {
      await router.replace({
        name: 'vod',
        query: buildVodCatalogQuery(catalog.routeState),
      })
    }
  } catch (error) {
    loadError.value = error instanceof ApiError ? error.message : 'Unable to load VOD titles'
  } finally {
    sourceLoading.value = false
  }
}

async function runSearch(page = 1) {
  if (!selectedSourceId.value) return
  const query = searchQuery.value.trim()
  if (!query) {
    await router.replace({
      name: 'vod',
      query: buildVodCatalogQuery({
        sourceId: selectedSourceId.value,
        categoryId: selectedCategoryId.value,
        query: '',
        page: 1,
      }),
    })
    return
  }

  searchLoading.value = true
  await router.replace({
    name: 'vod',
    query: buildVodCatalogQuery({
      sourceId: selectedSourceId.value,
      categoryId: null,
      query,
      page,
    }),
  })
  searchLoading.value = false
}

async function selectCategory(categoryId: string | null) {
  if (!selectedSourceId.value) return
  await router.replace({
    name: 'vod',
    query: buildVodCatalogQuery({
      sourceId: selectedSourceId.value,
      categoryId,
      query: '',
      page: 1,
    }),
  })
}

async function openDetail(item: VodBrowseItem) {
  if (!selectedSourceId.value || item.vod_id === null || item.vod_id === undefined) return
  await router.push({
    name: 'vod-detail',
    params: {
      sourceConfigId: selectedSourceId.value,
      vodId: String(item.vod_id),
    },
    query: buildVodCatalogQuery(buildCatalogRouteState()),
  })
}

async function changePage(direction: -1 | 1) {
  if (!pageResponse.value || !selectedSourceId.value) return
  const nextPage = pageResponse.value.page + direction
  await router.replace({
    name: 'vod',
    query: buildVodCatalogQuery({
      sourceId: selectedSourceId.value,
      categoryId: isSearchMode.value ? null : selectedCategoryId.value,
      query: submittedQuery.value,
      page: nextPage,
    }),
  })
}

function onSourceChange(value: string | null) {
  if (!value) {
    void router.replace({ name: 'vod', query: {} })
    return
  }
  void router.replace({
    name: 'vod',
    query: buildVodCatalogQuery({
      sourceId: value,
      categoryId: null,
      query: '',
      page: 1,
    }),
  })
}

watch(
  () => route.query,
  () => {
    if (!bootstrapped.value) return
    void syncCatalogFromRoute()
  },
)

onMounted(bootstrap)
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
          <NButton round secondary :loading="loading" @click="bootstrap">
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
          <p class="mt-2 text-lg font-semibold text-white">{{ pageResponse?.site.site_key ?? categoriesResponse?.site.site_key ?? 'Not selected' }}</p>
        </div>
        <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-5">
          <p class="text-sm text-white/42">Results</p>
          <p class="mt-2 text-lg font-semibold text-white">{{ pageResponse?.total ?? 0 }}</p>
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
        :has-search-filter="Boolean(submittedQuery || selectedCategoryId)"
        @update:selected-source-id="onSourceChange"
        @update:search-query="(value) => (searchQuery = value)"
        @search="runSearch(1)"
        @reset="selectCategory(null)"
      />

      <article class="glass-panel rounded-[2.25rem] p-6 sm:p-8">
        <VodCategoryChips
          :categories="categoriesResponse?.categories ?? []"
          :selected-category-id="selectedCategoryId"
          @select="selectCategory"
        />
      </article>

      <VodCatalogGrid
        :items="pageResponse?.items ?? []"
        :loading="sourceLoading || searchLoading"
        @select-item="openDetail"
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
      v-if="!loading && !sourceLoading && !searchLoading && !noUsableSource && selectedSourceId && !pageResponse?.items.length"
      class="glass-panel flex min-h-[18rem] items-end rounded-[2.5rem] p-7 sm:p-10"
    >
      <div class="max-w-3xl">
        <p class="text-sm uppercase tracking-[0.28em] text-white/42">No titles</p>
        <h2 class="mt-3 text-3xl font-semibold text-white sm:text-5xl">
          {{ isSearchMode ? 'No results matched the current search' : 'No titles were returned for this view' }}
        </h2>
      </div>
    </div>

    <article v-if="pageResponse && pageResponse.pagecount > 0" class="glass-panel rounded-[2rem] p-5">
      <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <p class="text-sm text-white/52">
          {{ isSearchMode ? `Search: ${submittedQuery}` : `Category: ${selectedCategoryId ?? 'All'}` }}
        </p>
        <div class="flex items-center gap-3">
          <NButton round secondary :disabled="!canGoPrev" @click="changePage(-1)">Previous</NButton>
          <span class="min-w-24 text-center text-sm text-white/64">{{ pageLabel }}</span>
          <NButton round secondary :disabled="!canGoNext" @click="changePage(1)">Next</NButton>
        </div>
      </div>
    </article>
  </section>
</template>
