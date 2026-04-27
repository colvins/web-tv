<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ChevronLeft, Film, RefreshCw, Search, Settings } from 'lucide-vue-next'
import { NButton, NInput, NSelect, useMessage } from 'naive-ui'
import { RouterLink } from 'vue-router'

import {
  getCurrentVodSite,
  getVodDetail,
  getVodCategories,
  getVodList,
  listSourceConfigs,
  searchVod,
  type VodBrowseDetailResponse,
  type CurrentVodSite,
  type SourceConfig,
  type VodBrowseCategoriesResponse,
  type VodBrowseItem,
  type VodBrowsePageResponse,
} from '@/api/sourceConfigs'
import { ApiError } from '@/api/client'

const message = useMessage()
const sources = ref<SourceConfig[]>([])
const currentVodSite = ref<CurrentVodSite | null>(null)
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

const sourceOptions = computed(() =>
  sources.value
    .filter((source) => source.enabled)
    .map((source) => ({
      label: `${source.name} · ${source.source_type.toUpperCase()}`,
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

async function bootstrap() {
  loading.value = true
  loadError.value = null
  noUsableSource.value = false
  try {
    const [sourceList, current] = await Promise.all([listSourceConfigs(), getCurrentVodSite()])
    sources.value = sourceList
    currentVodSite.value = current

    const enabledSources = sourceList.filter((source) => source.enabled)
    if (enabledSources.length === 0) {
      noUsableSource.value = true
      return
    }

    const candidateIds = [
      ...(current?.source_config_id ? [current.source_config_id] : []),
      ...enabledSources.map((source) => source.id),
    ].filter((value, index, values) => Boolean(value) && values.indexOf(value) === index) as string[]

    let resolved = false
    for (const sourceId of candidateIds) {
      const success = await loadSource(sourceId, { quiet: true })
      if (success) {
        resolved = true
        break
      }
    }
    noUsableSource.value = !resolved
  } catch (error) {
    loadError.value = error instanceof ApiError ? error.message : 'Unable to load VOD sources'
  } finally {
    loading.value = false
  }
}

async function loadSource(sourceId: string, options: { quiet?: boolean } = {}) {
  sourceLoading.value = true
  loadError.value = null
  try {
    const categories = await getVodCategories(sourceId)
    selectedSourceId.value = sourceId
    categoriesResponse.value = categories
    detail.value = null
    detailError.value = null
    selectedCategoryId.value = null
    submittedQuery.value = ''
    searchQuery.value = ''
    await loadListPage(1, sourceId)
    noUsableSource.value = false
    return true
  } catch (error) {
    if (!options.quiet) {
      loadError.value = error instanceof ApiError ? error.message : 'Unable to load VOD categories'
    }
    if (selectedSourceId.value === sourceId) {
      pageResponse.value = null
      categoriesResponse.value = null
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
  selectedCategoryId.value = categoryId
  submittedQuery.value = ''
  searchQuery.value = ''
  await loadListPage(1)
}

async function openDetail(item: VodBrowseItem) {
  if (!selectedSourceId.value || item.vod_id === null || item.vod_id === undefined) return
  detailLoading.value = true
  detailError.value = null
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
  if (!value) return
  void loadSource(value)
}

function posterAlt(item: VodBrowseItem) {
  return item.name
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

    <article v-else class="glass-panel rounded-[2.25rem] p-6 sm:p-8">
      <div class="grid gap-4 xl:grid-cols-[minmax(0,20rem)_minmax(0,1fr)]">
        <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-5">
          <p class="text-sm uppercase tracking-[0.18em] text-white/42">Source</p>
          <NSelect
            class="mt-4"
            :value="selectedSourceId"
            :options="sourceOptions"
            placeholder="Select a source"
            :loading="loading || sourceLoading"
            @update:value="onSourceChange"
          />
          <p v-if="currentVodSite?.source_config_id === selectedSourceId" class="mt-3 text-xs text-white/48">
            Current VOD selection points at this source package.
          </p>
        </div>

        <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-5">
          <div class="flex flex-col gap-4 lg:flex-row">
            <NInput
              v-model:value="searchQuery"
              placeholder="Search titles"
              clearable
              @keyup.enter="runSearch(1)"
            />
            <div class="flex gap-3">
              <NButton round type="primary" :loading="searchLoading" @click="runSearch(1)">
                <template #icon><Search class="h-4 w-4" /></template>
                Search
              </NButton>
              <NButton round secondary :disabled="!submittedQuery && !selectedCategoryId" @click="selectCategory(null)">
                Reset
              </NButton>
            </div>
          </div>
          <p class="mt-4 text-sm text-white/48">
            Search and category browsing use read-only collector metadata only.
          </p>
        </div>
      </div>

      <div class="mt-6 flex flex-wrap gap-3">
        <button
          type="button"
          class="rounded-full border px-4 py-2 text-sm transition"
          :class="selectedCategoryId === null ? 'border-white/30 bg-white/14 text-white' : 'border-white/10 bg-white/6 text-white/62 hover:bg-white/10'"
          @click="selectCategory(null)"
        >
          All
        </button>
        <button
          v-for="category in categoriesResponse?.categories ?? []"
          :key="`${category.type_id}-${category.type_name}`"
          type="button"
          class="rounded-full border px-4 py-2 text-sm transition"
          :class="
            selectedCategoryId === String(category.type_id)
              ? 'border-white/30 bg-white/14 text-white'
              : 'border-white/10 bg-white/6 text-white/62 hover:bg-white/10'
          "
          @click="selectCategory(category.type_id === null ? null : String(category.type_id))"
        >
          {{ category.type_name ?? `Type ${category.type_id}` }}
        </button>
      </div>
    </article>

    <div v-if="sourceLoading || searchLoading" class="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
      <div v-for="index in 8" :key="index" class="glass-panel min-h-80 animate-pulse rounded-[2rem] p-5">
        <div class="aspect-[3/4] rounded-[1.5rem] bg-white/8"></div>
        <div class="mt-5 h-5 w-2/3 rounded-full bg-white/10"></div>
        <div class="mt-3 h-3 w-1/3 rounded-full bg-white/8"></div>
      </div>
    </div>

    <div v-else-if="pageResponse?.items.length" class="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
      <article
        v-for="item in pageResponse.items"
        :key="`${item.vod_id}-${item.name}`"
        class="tv-focus-card glass-panel overflow-hidden rounded-[2rem] p-4"
      >
        <button type="button" class="block w-full text-left" @click="openDetail(item)">
        <div class="relative overflow-hidden rounded-[1.5rem] bg-white/6">
          <img
            v-if="item.poster"
            :src="item.poster"
            :alt="posterAlt(item)"
            class="aspect-[3/4] w-full object-cover"
            loading="lazy"
          />
          <div v-else class="flex aspect-[3/4] items-center justify-center text-white/30">
            <Film class="h-12 w-12" />
          </div>
          <div
            v-if="item.remarks"
            class="absolute left-3 top-3 rounded-full border border-black/10 bg-black/55 px-3 py-1 text-xs text-white"
          >
            {{ item.remarks }}
          </div>
        </div>

        <div class="mt-5">
          <h3 class="line-clamp-2 text-lg font-semibold text-white">{{ item.name }}</h3>
          <p class="mt-2 text-sm text-white/54">{{ item.category_name ?? 'Uncategorized' }}</p>
          <div class="mt-4 flex flex-wrap gap-2 text-xs text-white/60">
            <span v-if="item.year" class="rounded-full border border-white/10 bg-white/6 px-3 py-1">{{ item.year }}</span>
            <span v-if="item.area" class="rounded-full border border-white/10 bg-white/6 px-3 py-1">{{ item.area }}</span>
            <span
              v-if="item.vod_id !== null && item.vod_id !== undefined"
              class="rounded-full border border-white/10 bg-white/6 px-3 py-1"
            >
              ID {{ item.vod_id }}
            </span>
          </div>
        </div>
        </button>
      </article>
    </div>

    <div
      v-else-if="!loading && !sourceLoading && !searchLoading && !noUsableSource"
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

    <article v-if="detail || detailLoading || detailError" class="glass-panel rounded-[2.25rem] p-6 sm:p-8">
      <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p class="text-sm uppercase tracking-[0.26em] text-white/42">Detail</p>
          <h3 class="mt-3 text-2xl font-semibold text-white sm:text-3xl">{{ detailTitle }}</h3>
        </div>
        <NButton round secondary @click="closeDetail">
          <template #icon><ChevronLeft class="h-4 w-4" /></template>
          Back to results
        </NButton>
      </div>

      <div v-if="detailLoading" class="mt-6 grid gap-5 lg:grid-cols-[18rem_minmax(0,1fr)]">
        <div class="aspect-[3/4] animate-pulse rounded-[2rem] bg-white/8"></div>
        <div class="space-y-4">
          <div class="h-8 w-2/3 animate-pulse rounded-full bg-white/10"></div>
          <div class="h-4 w-full animate-pulse rounded-full bg-white/8"></div>
          <div class="h-4 w-5/6 animate-pulse rounded-full bg-white/8"></div>
        </div>
      </div>

      <p v-else-if="detailError" class="mt-6 rounded-3xl border border-red-300/18 bg-red-400/10 p-4 text-sm text-red-100">
        {{ detailError }}
      </p>

      <div v-else-if="detail" class="mt-6 grid gap-6 lg:grid-cols-[18rem_minmax(0,1fr)]">
        <div class="overflow-hidden rounded-[2rem] border border-white/10 bg-white/6">
          <img
            v-if="detail.poster"
            :src="detail.poster"
            :alt="detail.name"
            class="aspect-[3/4] w-full object-cover"
          />
          <div v-else class="flex aspect-[3/4] items-center justify-center text-white/30">
            <Film class="h-16 w-16" />
          </div>
        </div>

        <div class="space-y-5">
          <div class="flex flex-wrap gap-2 text-xs text-white/62">
            <span v-if="detail.category_name" class="rounded-full border border-white/10 bg-white/6 px-3 py-1">{{ detail.category_name }}</span>
            <span v-if="detail.year" class="rounded-full border border-white/10 bg-white/6 px-3 py-1">{{ detail.year }}</span>
            <span v-if="detail.area" class="rounded-full border border-white/10 bg-white/6 px-3 py-1">{{ detail.area }}</span>
            <span v-if="detail.language" class="rounded-full border border-white/10 bg-white/6 px-3 py-1">{{ detail.language }}</span>
            <span v-if="detail.remarks" class="rounded-full border border-white/10 bg-white/6 px-3 py-1">{{ detail.remarks }}</span>
          </div>

          <div class="grid gap-4 md:grid-cols-2">
            <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-4">
              <p class="text-xs uppercase tracking-[0.16em] text-white/40">Actor</p>
              <p class="mt-2 text-sm leading-6 text-white/78">{{ detail.actor ?? 'Not provided' }}</p>
            </div>
            <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-4">
              <p class="text-xs uppercase tracking-[0.16em] text-white/40">Director</p>
              <p class="mt-2 text-sm leading-6 text-white/78">{{ detail.director ?? 'Not provided' }}</p>
            </div>
          </div>

          <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-5">
            <p class="text-xs uppercase tracking-[0.16em] text-white/40">Description</p>
            <p class="mt-3 text-sm leading-7 text-white/74">{{ detail.description ?? 'No description returned by the collector.' }}</p>
          </div>

          <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-5">
            <p class="text-xs uppercase tracking-[0.16em] text-white/40">Collector metadata</p>
            <div class="mt-3 grid gap-3 sm:grid-cols-3 text-sm text-white/70">
              <p>Site: {{ detail.site.site_name ?? detail.site.site_key ?? 'Unknown' }}</p>
              <p>Host: {{ detail.site.api_host ?? 'Unknown' }}</p>
              <p>Path: {{ detail.site.api_path ?? 'Unknown' }}</p>
            </div>
            <div class="mt-3 flex flex-wrap gap-2">
              <span
                v-for="queryKey in detail.site.api_query_keys"
                :key="queryKey"
                class="rounded-full border border-white/10 bg-white/6 px-3 py-1 text-xs text-white/62"
              >
                {{ queryKey }}
              </span>
            </div>
          </div>

          <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-5">
            <div class="flex items-center justify-between gap-4">
              <p class="text-xs uppercase tracking-[0.16em] text-white/40">Play sources</p>
              <span class="text-xs text-white/46">Playback not implemented</span>
            </div>
            <div class="mt-4 grid gap-3">
              <article
                v-for="group in detail.play_sources"
                :key="group.source_name"
                class="rounded-[1.25rem] border border-white/10 bg-white/6 p-4"
              >
                <div class="flex flex-wrap items-center justify-between gap-3">
                  <h4 class="text-sm font-semibold text-white">{{ group.source_name }}</h4>
                  <div class="flex flex-wrap gap-2 text-xs text-white/60">
                    <span class="rounded-full border border-white/10 bg-black/18 px-3 py-1">{{ group.episode_count }} episodes</span>
                    <span class="rounded-full border border-white/10 bg-black/18 px-3 py-1">{{ group.has_play_urls ? 'URLs stored' : 'No URLs' }}</span>
                  </div>
                </div>
                <div class="mt-3 flex flex-wrap gap-2">
                  <span
                    v-for="episode in group.sample_episode_names"
                    :key="episode"
                    class="rounded-full border border-white/10 bg-black/18 px-3 py-1 text-xs text-white/64"
                  >
                    {{ episode }}
                  </span>
                </div>
              </article>
              <p v-if="detail.play_sources.length === 0" class="text-sm text-white/54">
                No play source groups were returned by the collector.
              </p>
            </div>
          </div>
        </div>
      </div>
    </article>
  </section>
</template>
