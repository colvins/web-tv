<script setup lang="ts">
import { Teleport, computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import {
  getVodCategories,
  getCurrentVodSite,
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
import VodSourceSelector from '@/components/vod/VodSourceSelector.vue'
import { vodPageHeaderTitle } from '@/composables/useVodPageHeader'
import {
  buildVodCatalogQuery,
  getVodCatalogRouteKey,
  parseVodCatalogRouteState,
  type VodCatalogRouteState,
} from '@/utils/vodRouteState'

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
    siteKey: overrides.siteKey ?? pageResponse.value?.site.site_key ?? categoriesResponse.value?.site.site_key ?? null,
    categoryId: overrides.categoryId ?? selectedCategoryId.value,
    query: overrides.query ?? submittedQuery.value,
    page: overrides.page ?? pageResponse.value?.page ?? 1,
  }
}

async function fetchSourceCatalog(sourceId: string, routeState: VodCatalogRouteState) {
  const categories = await getVodCategories(sourceId, routeState.siteKey)
  const normalizedRouteState = normalizeRouteStateCategory(routeState, categories)
  const page = normalizedRouteState.query
    ? await searchVod({
        source_config_id: sourceId,
        site_key: normalizedRouteState.siteKey,
        q: normalizedRouteState.query,
        page: normalizedRouteState.page,
      })
    : await getVodList({
        source_config_id: sourceId,
        site_key: normalizedRouteState.siteKey,
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
    const [sourceList, currentVodSite] = await Promise.all([listSourceConfigs(), getCurrentVodSite()])
    sources.value = sourceList

    const routeState = parseVodCatalogRouteState(route.query)
    const enabledIds = new Set(sourceList.filter((source) => source.enabled && source.vod_site_count > 0).map((source) => source.id))
    const candidateIds = [
      routeState.sourceId && enabledIds.has(routeState.sourceId) ? routeState.sourceId : null,
      currentVodSite?.source_config_id && enabledIds.has(currentVodSite.source_config_id) ? currentVodSite.source_config_id : null,
      ...enabledSources.value.map((source) => source.id),
    ].filter((value, index, values): value is string => Boolean(value) && values.indexOf(value) === index)

    for (const sourceId of candidateIds) {
      try {
        const initialRouteState =
          !routeState.sourceId && currentVodSite?.source_config_id === sourceId
            ? { ...routeState, sourceId, siteKey: currentVodSite.site_key }
            : { ...routeState, sourceId }
        const catalog = await fetchSourceCatalog(sourceId, initialRouteState)
        applyCatalogState(sourceId, catalog)
        if (
          routeState.sourceId !== sourceId ||
          getVodCatalogRouteKey(initialRouteState) !== getVodCatalogRouteKey({ ...catalog.routeState, sourceId })
        ) {
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
        siteKey: buildCatalogRouteState().siteKey,
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
      siteKey: buildCatalogRouteState().siteKey,
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
      siteKey: buildCatalogRouteState().siteKey,
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
      siteKey: buildCatalogRouteState().siteKey,
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
      siteKey: null,
      categoryId: null,
      query: '',
      page: 1,
    }),
  })
}

watch(
  headerSourceName,
  (value) => {
    vodPageHeaderTitle.value = value || 'VOD'
  },
  { immediate: true },
)

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
  vodPageHeaderTitle.value = 'VOD'
})

watch(
  () => route.fullPath,
  () => {
    syncLayoutMode()
  },
)
</script>

<template>
  <Teleport to="#vod-page-toolbar">
    <VodSourceSelector
      :compact="!isDesktopLayout"
      :source-options="sourceOptions"
      :selected-source-id="selectedSourceId"
      :search-query="searchQuery"
      :loading="loading"
      :source-loading="sourceLoading"
      :search-loading="searchLoading"
      :has-search-filter="Boolean(submittedQuery || selectedCategoryId)"
      @refresh="bootstrap"
      @update:selected-source-id="onSourceChange"
      @update:search-query="(value) => (searchQuery = value)"
      @search="runSearch(1)"
      @reset="selectCategory(null)"
    />
  </Teleport>

  <VodDesktopLayout
    v-if="isDesktopLayout"
    :page-label="pageLabel"
    :load-error="loadError"
    :loading="loading"
    :no-usable-source="noUsableSource"
    :selected-source-id="selectedSourceId"
    :selected-category-id="selectedCategoryId"
    :source-loading="sourceLoading"
    :search-loading="searchLoading"
    :categories="categoriesResponse?.categories ?? []"
    :items="pageResponse?.items ?? []"
    :can-go-prev="canGoPrev"
    :can-go-next="canGoNext"
    :is-search-mode="isSearchMode"
    :submitted-query="submittedQuery"
    :pagecount="pageResponse?.pagecount ?? 0"
    @select-category="selectCategory"
    @select-item="openDetail"
    @change-page="changePage"
  />

  <VodMobileLayout
    v-else
    :page-label="pageLabel"
    :load-error="loadError"
    :loading="loading"
    :no-usable-source="noUsableSource"
    :selected-source-id="selectedSourceId"
    :selected-category-id="selectedCategoryId"
    :source-loading="sourceLoading"
    :search-loading="searchLoading"
    :categories="categoriesResponse?.categories ?? []"
    :items="pageResponse?.items ?? []"
    :can-go-prev="canGoPrev"
    :can-go-next="canGoNext"
    :is-search-mode="isSearchMode"
    :submitted-query="submittedQuery"
    :pagecount="pageResponse?.pagecount ?? 0"
    @select-category="selectCategory"
    @select-item="openDetail"
    @change-page="changePage"
  />
</template>
