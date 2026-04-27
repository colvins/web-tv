<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

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
import VodDesktopLayout from '@/components/vod/VodDesktopLayout.vue'
import VodMobileLayout from '@/components/vod/VodMobileLayout.vue'
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
const isDesktopLayout = ref(true)

let mediaQuery: MediaQueryList | undefined

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

function syncLayoutMode() {
  isDesktopLayout.value = mediaQuery?.matches ?? window.innerWidth >= 768
}

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
onMounted(() => {
  mediaQuery = window.matchMedia('(min-width: 768px)')
  syncLayoutMode()
  mediaQuery.addEventListener('change', syncLayoutMode)
})

onBeforeUnmount(() => {
  mediaQuery?.removeEventListener('change', syncLayoutMode)
})

watch(
  () => route.fullPath,
  () => {
    syncLayoutMode()
  },
)
</script>

<template>
  <VodDesktopLayout
    v-if="isDesktopLayout"
    :header-site-name="headerSiteName"
    :header-source-name="headerSourceName"
    :page-label="pageLabel"
    :selected-site-key="pageResponse?.site.site_key ?? categoriesResponse?.site.site_key ?? null"
    :total-results="pageResponse?.total ?? 0"
    :load-error="loadError"
    :loading="loading"
    :no-usable-source="noUsableSource"
    :selected-source-id="selectedSourceId"
    :selected-category-id="selectedCategoryId"
    :source-options="sourceOptions"
    :search-query="searchQuery"
    :source-loading="sourceLoading"
    :search-loading="searchLoading"
    :has-search-filter="Boolean(submittedQuery || selectedCategoryId)"
    :categories="categoriesResponse?.categories ?? []"
    :items="pageResponse?.items ?? []"
    :can-go-prev="canGoPrev"
    :can-go-next="canGoNext"
    :is-search-mode="isSearchMode"
    :submitted-query="submittedQuery"
    :pagecount="pageResponse?.pagecount ?? 0"
    @refresh="bootstrap"
    @update:selected-source-id="onSourceChange"
    @update:search-query="(value) => (searchQuery = value)"
    @search="runSearch(1)"
    @reset="selectCategory(null)"
    @select-category="selectCategory"
    @select-item="openDetail"
    @change-page="changePage"
  />

  <VodMobileLayout
    v-else
    :header-site-name="headerSiteName"
    :header-source-name="headerSourceName"
    :page-label="pageLabel"
    :selected-site-key="pageResponse?.site.site_key ?? categoriesResponse?.site.site_key ?? null"
    :total-results="pageResponse?.total ?? 0"
    :load-error="loadError"
    :loading="loading"
    :no-usable-source="noUsableSource"
    :selected-source-id="selectedSourceId"
    :selected-category-id="selectedCategoryId"
    :source-options="sourceOptions"
    :search-query="searchQuery"
    :source-loading="sourceLoading"
    :search-loading="searchLoading"
    :has-search-filter="Boolean(submittedQuery || selectedCategoryId)"
    :categories="categoriesResponse?.categories ?? []"
    :items="pageResponse?.items ?? []"
    :can-go-prev="canGoPrev"
    :can-go-next="canGoNext"
    :is-search-mode="isSearchMode"
    :submitted-query="submittedQuery"
    :pagecount="pageResponse?.pagecount ?? 0"
    @refresh="bootstrap"
    @update:selected-source-id="onSourceChange"
    @update:search-query="(value) => (searchQuery = value)"
    @search="runSearch(1)"
    @reset="selectCategory(null)"
    @select-category="selectCategory"
    @select-item="openDetail"
    @change-page="changePage"
  />
</template>
