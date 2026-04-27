<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RefreshCw, Settings } from 'lucide-vue-next'
import { NButton, useMessage } from 'naive-ui'
import { RouterLink } from 'vue-router'

import {
  getVodCategories,
  getVodDetail,
  getVodEpisodePlay,
  getVodList,
  listSourceConfigs,
  searchVod,
  type SourceConfig,
  type VodBrowseCategoriesResponse,
  type VodBrowseDetailResponse,
  type VodBrowseItem,
  type VodBrowsePageResponse,
  type VodEpisodePlayResponse,
} from '@/api/sourceConfigs'
import { ApiError } from '@/api/client'
import { useVodPlayback } from '@/composables/useVodPlayback'
import VodCatalogGrid from '@/components/vod/VodCatalogGrid.vue'
import VodCategoryChips from '@/components/vod/VodCategoryChips.vue'
import VodDetailPanel from '@/components/vod/VodDetailPanel.vue'
import VodSourceSelector from '@/components/vod/VodSourceSelector.vue'

const VOD_SOURCE_STORAGE_KEY = 'webtv.vod.selectedSourceConfigId'

const message = useMessage()
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
const detail = ref<VodBrowseDetailResponse | null>(null)
const detailLoading = ref(false)
const detailError = ref<string | null>(null)
const episodeLoadingKey = ref<string | null>(null)
const episodeError = ref<string | null>(null)
const playback = useVodPlayback()

const sourceOptions = computed(() =>
  sources.value
    .filter((source) => source.enabled)
    .map((source) => ({
      label: `${source.name} · ${source.latest_detected_format ?? source.source_type.toUpperCase()} · VOD ${source.vod_site_count} · ${source.latest_import_status?.toUpperCase() ?? 'NEW'}`,
      value: source.id,
    })),
)

const selectedSource = computed(
  () => sources.value.find((source) => source.id === selectedSourceId.value) ?? null,
)

const headerSiteName = computed(() => pageResponse.value?.site.site_name ?? categoriesResponse.value?.site.site_name ?? 'Generic collector')
const headerSourceName = computed(() => pageResponse.value?.site.source_name ?? categoriesResponse.value?.site.source_name ?? selectedSource.value?.name ?? 'VOD Source')
const pageLabel = computed(() => `${pageResponse.value?.page ?? 1} / ${pageResponse.value?.pagecount ?? 1}`)
const isSearchMode = computed(() => submittedQuery.value.trim().length > 0)
const canGoPrev = computed(() => (pageResponse.value?.page ?? 1) > 1)
const canGoNext = computed(() => (pageResponse.value?.page ?? 1) < (pageResponse.value?.pagecount ?? 1))
const detailTitle = computed(() => detail.value?.name ?? 'Title detail')
const enabledSources = computed(() => sources.value.filter((source) => source.enabled))

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
  detail.value = null
  detailError.value = null
  episodeError.value = null
  episodeLoadingKey.value = null
  selectedCategoryId.value = null
  submittedQuery.value = ''
  searchQuery.value = ''
  playback.destroyPlayer()
}

async function fetchSourceCatalog(sourceId: string) {
  const [categories, page] = await Promise.all([
    getVodCategories(sourceId),
    getVodList({
      source_config_id: sourceId,
      page: 1,
    }),
  ])
  return { categories, page }
}

async function bootstrap() {
  loading.value = true
  loadError.value = null
  try {
    const sourceList = await listSourceConfigs()
    sources.value = sourceList

    const enabledIds = new Set(sourceList.filter((source) => source.enabled).map((source) => source.id))
    const currentSelection = selectedSourceId.value
    const savedSelection = restoreSavedSourceId()

    const preferredSourceId =
      (currentSelection && enabledIds.has(currentSelection) ? currentSelection : null) ??
      (savedSelection && enabledIds.has(savedSelection) ? savedSelection : null)

    if (preferredSourceId) {
      await loadSource(preferredSourceId, { quiet: true, preserveSelectionOnFailure: true })
      return
    }

    const candidateIds = enabledSources.value.map((source) => source.id)
    for (const sourceId of candidateIds) {
      const success = await loadSource(sourceId, { quiet: true })
      if (success) {
        return
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
  }
}

async function loadSource(
  sourceId: string,
  options: { quiet?: boolean; preserveSelectionOnFailure?: boolean } = {},
) {
  sourceLoading.value = true
  loadError.value = null
  noUsableSource.value = false
  try {
    const catalog = await fetchSourceCatalog(sourceId)
    selectedSourceId.value = sourceId
    persistSelectedSourceId(sourceId)
    resetVodState()
    categoriesResponse.value = catalog.categories
    pageResponse.value = catalog.page
    return true
  } catch (error) {
    if (options.preserveSelectionOnFailure) {
      selectedSourceId.value = sourceId
      persistSelectedSourceId(sourceId)
    }
    resetVodState()
    if (!options.quiet) {
      loadError.value = error instanceof ApiError ? error.message : 'Unable to load VOD categories'
    }
    return false
  } finally {
    sourceLoading.value = false
  }
}

async function loadListPage(page: number, sourceId = selectedSourceId.value) {
  if (!sourceId) return
  sourceLoading.value = true
  loadError.value = null
  try {
    pageResponse.value = await getVodList({
      source_config_id: sourceId,
      type_id: selectedCategoryId.value,
      page,
    })
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
    submittedQuery.value = ''
    await loadListPage(1)
    return
  }

  searchLoading.value = true
  loadError.value = null
  try {
    submittedQuery.value = query
    pageResponse.value = await searchVod({
      source_config_id: selectedSourceId.value,
      q: query,
      page,
    })
  } catch (error) {
    loadError.value = error instanceof ApiError ? error.message : 'Unable to search VOD titles'
  } finally {
    searchLoading.value = false
  }
}

async function selectCategory(categoryId: string | null) {
  detail.value = null
  detailError.value = null
  episodeError.value = null
  playback.destroyPlayer()
  selectedCategoryId.value = categoryId
  submittedQuery.value = ''
  searchQuery.value = ''
  await loadListPage(1)
}

async function openDetail(item: VodBrowseItem) {
  if (!selectedSourceId.value || item.vod_id === null || item.vod_id === undefined) return
  detailLoading.value = true
  detailError.value = null
  episodeError.value = null
  playback.destroyPlayer()
  try {
    detail.value = await getVodDetail({
      source_config_id: selectedSourceId.value,
      vod_id: item.vod_id,
    })
  } catch (error) {
    detailError.value = error instanceof ApiError ? error.message : 'Unable to load VOD detail'
    message.error(detailError.value)
  } finally {
    detailLoading.value = false
  }
}

function closeDetail() {
  detail.value = null
  detailError.value = null
  episodeError.value = null
  playback.destroyPlayer()
}

async function playEpisode(groupSourceName: string, episodeIndex: number) {
  if (!selectedSourceId.value || !detail.value?.vod_id) return
  const key = `${groupSourceName}:${episodeIndex}`
  episodeLoadingKey.value = key
  episodeError.value = null
  try {
    const episode: VodEpisodePlayResponse = await getVodEpisodePlay({
      source_config_id: selectedSourceId.value,
      vod_id: detail.value.vod_id,
      source_name: groupSourceName,
      episode_index: episodeIndex,
    })
    await playback.loadEpisode(episode)
  } catch (error) {
    episodeError.value = error instanceof ApiError ? error.message : 'Unable to load episode playback metadata'
    message.error(episodeError.value)
  } finally {
    episodeLoadingKey.value = null
  }
}

async function changePage(direction: -1 | 1) {
  if (!pageResponse.value) return
  const nextPage = pageResponse.value.page + direction
  if (isSearchMode.value) {
    await runSearch(nextPage)
    return
  }
  await loadListPage(nextPage)
}

function onSourceChange(value: string | null) {
  if (!value) {
    selectedSourceId.value = null
    persistSelectedSourceId(null)
    resetVodState()
    return
  }
  void loadSource(value, { preserveSelectionOnFailure: true })
}

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
          <p class="mt-5 max-w-3xl text-base leading-7 text-white/60">
            Browse generic MacCMS-style JSON collector metadata only. Playback and spider runtime remain disabled.
          </p>
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
        <p class="text-sm uppercase tracking-[0.28em] text-white/42">No generic source</p>
        <h2 class="mt-3 text-4xl font-semibold text-white sm:text-6xl">No compatible VOD collector is available yet</h2>
        <p class="mt-5 text-base leading-7 text-white/58">
          Import a source snapshot with a generic MacCMS-style JSON collector endpoint, or enable another source package.
        </p>
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
        <p class="mt-5 text-base leading-7 text-white/58">
          Pick one imported source package from the selector to bind all VOD browsing requests to that source_config_id.
        </p>
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

    <VodDetailPanel
      :detail="detail"
      :detail-title="detailTitle"
      :detail-loading="detailLoading"
      :detail-error="detailError"
      :episode-loading-key="episodeLoadingKey"
      :episode-error="episodeError"
      :playback="playback"
      @close="closeDetail"
      @play-episode="playEpisode"
    />
  </section>
</template>
