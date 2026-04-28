<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  CheckCircle2,
  CloudDownload,
  Edit3,
  Plus,
  Power,
  RefreshCw,
  Rows3,
  Trash2,
  Waves,
} from 'lucide-vue-next'
import {
  NButton,
  NForm,
  NFormItem,
  NInput,
  NModal,
  NSwitch,
  useMessage,
  type FormInst,
  type FormRules,
} from 'naive-ui'

import {
  createSourceConfig,
  deleteSourceConfig,
  extractLiveChannels,
  getCurrentVodSite,
  getLatestSourceSnapshot,
  getLatestVodCapabilityAnalysis,
  importSourceConfig,
  listSourceConfigs,
  listSourceVodSites,
  previewLiveChannels,
  setCurrentVodSite,
  updateSourceConfig,
  updateVodSite,
  type CurrentVodSite,
  type ImportJob,
  type LiveExtractionPreview,
  type LiveExtractionStats,
  type SourceConfig,
  type SourceConfigPayload,
  type SourceSnapshot,
  type VodCapabilityAnalysis,
  type VodSite,
} from '@/api/sourceConfigs'
import { ApiError } from '@/api/client'

const message = useMessage()
const sources = ref<SourceConfig[]>([])
const loading = ref(false)
const saving = ref(false)
const importingIds = ref<Set<string>>(new Set())
const extractingLiveIds = ref<Set<string>>(new Set())
const latestJob = ref<ImportJob | null>(null)
const latestSnapshot = ref<SourceSnapshot | null>(null)
const latestLiveExtraction = ref<LiveExtractionStats | null>(null)
const livePreviewSource = ref<SourceConfig | null>(null)
const livePreview = ref<LiveExtractionPreview | null>(null)
const livePreviewLoading = ref(false)
const confirmingLiveImport = ref(false)
const currentVodSite = ref<CurrentVodSite | null>(null)
const settingCurrentIds = ref<Set<string>>(new Set())
const vodAnalysisOpenIds = ref<Set<string>>(new Set())
const vodAnalysisLoadingIds = ref<Set<string>>(new Set())
const vodAnalysisBySource = ref<Record<string, VodCapabilityAnalysis | null | undefined>>({})
const vodAnalysisErrors = ref<Record<string, string | null | undefined>>({})
const siteModalOpen = ref(false)
const selectedSource = ref<SourceConfig | null>(null)
const selectedSites = ref<VodSite[]>([])
const loadingSites = ref(false)
const modalOpen = ref(false)
const deleteTarget = ref<SourceConfig | null>(null)
const editingSource = ref<SourceConfig | null>(null)
const formRef = ref<FormInst | null>(null)

const form = reactive<SourceConfigPayload>({
  name: '',
  source_type: 'json',
  url: '',
  enabled: true,
})

const rules: FormRules = {
  name: [{ required: true, message: 'Name is required', trigger: ['input', 'blur'] }],
  url: [
    { required: true, message: 'URL is required', trigger: ['input', 'blur'] },
    {
      validator: (_rule, value: string) => {
        if (!value) return true
        try {
          const parsed = new URL(value)
          return parsed.protocol === 'http:' || parsed.protocol === 'https:'
        } catch {
          return false
        }
      },
      message: 'Use a valid http or https URL',
      trigger: ['input', 'blur'],
    },
  ],
}

const enabledCount = computed(() => sources.value.filter((source) => source.enabled).length)
const importedCount = computed(() => sources.value.filter((source) => source.last_success_at).length)
const modalTitle = computed(() => (editingSource.value ? 'Edit Source' : 'Add Source'))
const latestImportedSource = computed(
  () => sources.value.find((source) => source.id === latestJob.value?.source_config_id) ?? null,
)
const latestSiteNames = computed(() =>
  (latestSnapshot.value?.site_samples ?? [])
    .map((site) => site.name?.trim())
    .filter((value): value is string => Boolean(value)),
)
const latestCategoryNames = computed(() => {
  const names: string[] = []
  for (const sample of latestSnapshot.value?.site_samples ?? []) {
    const categories = sample.categories_hint
    if (Array.isArray(categories)) {
      names.push(...categories.map((value) => String(value).trim()).filter(Boolean))
      continue
    }
    if (typeof categories === 'string' && categories.trim()) {
      names.push(categories.trim())
    }
  }
  return Array.from(new Set(names)).slice(0, 8)
})

function resetForm(source?: SourceConfig) {
  editingSource.value = source ?? null
  form.name = source?.name ?? ''
  form.source_type = source?.source_type ?? 'json'
  form.url = source?.url ?? ''
  form.enabled = source?.enabled ?? true
}

function openCreateModal() {
  resetForm()
  modalOpen.value = true
}

function openEditModal(source: SourceConfig) {
  resetForm(source)
  modalOpen.value = true
}

async function loadSources() {
  loading.value = true
  try {
    sources.value = await listSourceConfigs()
  } catch (error) {
    showError(error, 'Unable to load sources')
  } finally {
    loading.value = false
  }
}

async function loadCurrentVodSite() {
  try {
    currentVodSite.value = await getCurrentVodSite()
  } catch (error) {
    showError(error, 'Unable to load current VOD site')
  }
}

async function loadLatestSnapshot(sourceConfigId: string) {
  try {
    latestSnapshot.value = await getLatestSourceSnapshot(sourceConfigId)
  } catch (error) {
    if (error instanceof ApiError) {
      latestSnapshot.value = null
      return
    }
    latestSnapshot.value = null
  }
}

async function submitForm() {
  await formRef.value?.validate()
  saving.value = true
  try {
    if (editingSource.value) {
      const updated = await updateSourceConfig(editingSource.value.id, {
        name: form.name,
        url: form.url,
        enabled: form.enabled,
      })
      sources.value = sources.value.map((source) => (source.id === updated.id ? updated : source))
      message.success('Source updated')
      modalOpen.value = false
      return
    }

    const created = await createSourceConfig({
      name: form.name,
      source_type: 'json',
      url: form.url,
      enabled: form.enabled,
    })
    modalOpen.value = false
    await runImport(created, { successMessage: 'Detection and import completed' })
  } catch (error) {
    showError(error, 'Unable to save source')
  } finally {
    saving.value = false
  }
}

async function toggleSource(source: SourceConfig, enabled: boolean) {
  const previous = source.enabled
  source.enabled = enabled
  try {
    const updated = await updateSourceConfig(source.id, { enabled })
    sources.value = sources.value.map((item) => (item.id === updated.id ? updated : item))
    await loadCurrentVodSite()
  } catch (error) {
    source.enabled = previous
    showError(error, 'Unable to update source')
  }
}

async function runImport(
  source: SourceConfig,
  options: { successMessage?: string } = {},
) {
  importingIds.value = new Set(importingIds.value).add(source.id)
  latestSnapshot.value = null
  try {
    latestJob.value = await importSourceConfig(source.id)
    resetVodAnalysis(source.id)
    await Promise.all([loadSources(), loadCurrentVodSite(), loadLatestSnapshot(source.id)])
    if (latestJob.value.status === 'success') {
      message.success(options.successMessage ?? 'Import completed')
      const refreshed = sources.value.find((item) => item.id === source.id) ?? source
      if (isLivePlaylistImport(refreshed, latestJob.value)) {
        await openLivePreview(refreshed)
      }
    } else {
      message.error('Import failed')
    }
  } catch (error) {
    showError(error, 'Unable to import source')
  } finally {
    const next = new Set(importingIds.value)
    next.delete(source.id)
    importingIds.value = next
  }
}

async function extractLive(source: SourceConfig) {
  extractingLiveIds.value = new Set(extractingLiveIds.value).add(source.id)
  try {
    latestLiveExtraction.value = await extractLiveChannels(source.id)
    closeLivePreview()
    await loadSources()
    message.success(`Extracted ${latestLiveExtraction.value.channels_count} live channels`)
  } catch (error) {
    showError(error, 'Unable to extract live channels')
  } finally {
    const next = new Set(extractingLiveIds.value)
    next.delete(source.id)
    extractingLiveIds.value = next
  }
}

async function openLivePreview(source: SourceConfig) {
  livePreviewSource.value = source
  livePreview.value = null
  livePreviewLoading.value = true
  try {
    livePreview.value = await previewLiveChannels(source.id)
  } catch (error) {
    livePreviewSource.value = null
    showError(error, 'Unable to preview live channels')
  } finally {
    livePreviewLoading.value = false
  }
}

async function confirmLiveImport() {
  if (!livePreviewSource.value || !livePreview.value) return
  confirmingLiveImport.value = true
  try {
    await extractLive(livePreviewSource.value)
  } finally {
    confirmingLiveImport.value = false
  }
}

function closeLivePreview() {
  livePreviewSource.value = null
  livePreview.value = null
  livePreviewLoading.value = false
}

async function openSites(source: SourceConfig) {
  selectedSource.value = source
  siteModalOpen.value = true
  loadingSites.value = true
  try {
    selectedSites.value = await listSourceVodSites(source.id)
  } catch (error) {
    showError(error, 'Unable to load sites')
  } finally {
    loadingSites.value = false
  }
}

async function toggleVodAnalysis(source: SourceConfig) {
  if (vodAnalysisOpenIds.value.has(source.id)) {
    const next = new Set(vodAnalysisOpenIds.value)
    next.delete(source.id)
    vodAnalysisOpenIds.value = next
    return
  }

  const next = new Set(vodAnalysisOpenIds.value)
  next.add(source.id)
  vodAnalysisOpenIds.value = next

  if (vodAnalysisBySource.value[source.id] !== undefined || vodAnalysisLoadingIds.value.has(source.id)) {
    return
  }

  vodAnalysisLoadingIds.value = new Set(vodAnalysisLoadingIds.value).add(source.id)
  try {
    const analysis = await getLatestVodCapabilityAnalysis(source.id)
    vodAnalysisBySource.value = {
      ...vodAnalysisBySource.value,
      [source.id]: analysis,
    }
    vodAnalysisErrors.value = {
      ...vodAnalysisErrors.value,
      [source.id]: null,
    }
  } catch (error) {
    vodAnalysisErrors.value = {
      ...vodAnalysisErrors.value,
      [source.id]: error instanceof ApiError ? error.message : 'Unable to load VOD analysis',
    }
  } finally {
    const loadingNext = new Set(vodAnalysisLoadingIds.value)
    loadingNext.delete(source.id)
    vodAnalysisLoadingIds.value = loadingNext
  }
}

function resetVodAnalysis(sourceId: string) {
  const nextAnalyses = { ...vodAnalysisBySource.value }
  const nextErrors = { ...vodAnalysisErrors.value }
  delete nextAnalyses[sourceId]
  delete nextErrors[sourceId]
  vodAnalysisBySource.value = nextAnalyses
  vodAnalysisErrors.value = nextErrors
}

async function toggleVodSite(site: VodSite, enabled: boolean) {
  const previous = site.enabled
  site.enabled = enabled
  try {
    const updated = await updateVodSite(site.id, enabled)
    selectedSites.value = selectedSites.value.map((item) => (item.id === updated.id ? updated : item))
    if (selectedSource.value) {
      selectedSites.value = await listSourceVodSites(selectedSource.value.id)
    }
    await Promise.all([loadCurrentVodSite(), loadSources()])
  } catch (error) {
    site.enabled = previous
    showError(error, 'Unable to update site')
  }
}

async function useVodSite(site: VodSite) {
  settingCurrentIds.value = new Set(settingCurrentIds.value).add(site.id)
  try {
    currentVodSite.value = await setCurrentVodSite(site.id)
    message.success('Current VOD site updated')
  } catch (error) {
    showError(error, 'Unable to set current VOD site')
  } finally {
    const next = new Set(settingCurrentIds.value)
    next.delete(site.id)
    settingCurrentIds.value = next
  }
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  const target = deleteTarget.value
  saving.value = true
  try {
    await deleteSourceConfig(target.id)
    sources.value = sources.value.filter((source) => source.id !== target.id)
    deleteTarget.value = null
    message.success('Source deleted')
  } catch (error) {
    showError(error, 'Unable to delete source')
  } finally {
    saving.value = false
  }
}

function showError(error: unknown, fallback: string) {
  message.error(error instanceof ApiError ? error.message : fallback)
}

function formatDate(value: string | null) {
  if (!value) return 'Never'
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function detectedTypeLabel(source: SourceConfig | null) {
  if (!source?.latest_detected_format) return 'Not imported'
  if (source.latest_detected_format === 'catvod_json' || source.latest_detected_format === 'base64_json' || source.latest_detected_format === 'binary_wrapped') {
    return 'CatVod-style config'
  }
  if (source.latest_detected_format === 'm3u' || source.latest_detected_format === 'txt') {
    return 'Live playlist'
  }
  if (source.latest_detected_format === 'plain_json' && source.vod_site_count > 0) {
    return 'MacCMS VOD collector'
  }
  return 'Unsupported'
}

function isCurrentSite(site: VodSite) {
  return currentVodSite.value?.id === site.id
}

function sourceCurrentLabel(source: SourceConfig) {
  if (currentVodSite.value?.source_config_id !== source.id) return null
  return `${currentVodSite.value.site_name} / ${currentVodSite.value.site_key}`
}

function supportsLiveExtraction(source: SourceConfig) {
  return ['m3u', 'm3u8', 'txt'].includes(source.source_type)
}

function isLivePlaylistImport(source: SourceConfig, job: ImportJob | null) {
  if (!job || job.status !== 'success') return false
  return ['m3u', 'txt'].includes(job.detected_format ?? '') || ['m3u', 'm3u8', 'txt'].includes(source.source_type)
}

function isVodAnalysisOpen(sourceId: string) {
  return vodAnalysisOpenIds.value.has(sourceId)
}

function vodSummary(sourceId: string) {
  return vodAnalysisBySource.value[sourceId]?.summary ?? null
}

onMounted(async () => {
  await Promise.all([loadSources(), loadCurrentVodSite()])
})
</script>

<template>
  <section class="grid gap-6">
    <div class="glass-panel rounded-[2.5rem] p-6 sm:p-8">
      <div class="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p class="text-sm uppercase tracking-[0.28em] text-white/42">Source Library</p>
          <h2 class="mt-3 text-3xl font-semibold sm:text-5xl">Detect and import source URLs.</h2>
          <p class="mt-4 max-w-3xl text-sm leading-6 text-white/58">
            Add a source name and URL, then let the backend detect whether it is a MacCMS VOD collector, CatVod-style config, live playlist, or unsupported response.
          </p>
        </div>
        <div class="flex flex-wrap gap-3">
          <NButton round secondary :loading="loading" @click="loadSources">
            <template #icon><RefreshCw class="h-4 w-4" /></template>
            Refresh
          </NButton>
          <NButton round type="primary" @click="openCreateModal">
            <template #icon><Plus class="h-4 w-4" /></template>
            Add Source
          </NButton>
        </div>
      </div>

      <div class="mt-8 grid gap-4 sm:grid-cols-4">
        <div class="rounded-[1.5rem] border border-white/10 bg-white/6 p-5">
          <p class="text-sm text-white/46">Total</p>
          <p class="mt-2 text-3xl font-semibold">{{ sources.length }}</p>
        </div>
        <div class="rounded-[1.5rem] border border-white/10 bg-white/6 p-5">
          <p class="text-sm text-white/46">Enabled</p>
          <p class="mt-2 text-3xl font-semibold">{{ enabledCount }}</p>
        </div>
        <div class="rounded-[1.5rem] border border-white/10 bg-white/6 p-5">
          <p class="text-sm text-white/46">Imported</p>
          <p class="mt-2 text-3xl font-semibold">{{ importedCount }}</p>
        </div>
        <div class="rounded-[1.5rem] border border-white/10 bg-white/6 p-5">
          <p class="text-sm text-white/46">Current VOD site</p>
          <p class="mt-2 text-sm font-semibold text-white">
            <span v-if="currentVodSite">{{ currentVodSite.site_name }} / {{ currentVodSite.site_key }}</span>
            <span v-else>No VOD site selected</span>
          </p>
        </div>
      </div>
    </div>

    <article v-if="latestJob" class="glass-panel rounded-[2rem] p-6 sm:p-7">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p class="text-sm uppercase tracking-[0.28em] text-white/42">Latest Detect / Import</p>
          <h2 class="mt-3 text-2xl font-semibold text-white">
            {{ detectedTypeLabel(latestImportedSource) }}
          </h2>
          <p class="mt-2 text-sm text-white/56">
            {{ latestImportedSource?.name ?? latestJob.source_config_id }}
          </p>
        </div>
        <div class="grid gap-3 text-sm text-white/62 sm:grid-cols-4 lg:min-w-[38rem]">
          <div class="rounded-3xl border border-white/10 bg-white/6 p-4">
            <span class="block text-white/40">Status</span>
            <span class="mt-1 block text-white">{{ latestJob.status }}</span>
          </div>
          <div class="rounded-3xl border border-white/10 bg-white/6 p-4">
            <span class="block text-white/40">Detected format</span>
            <span class="mt-1 block text-white">{{ latestJob.detected_format ?? 'Unknown' }}</span>
          </div>
          <div class="rounded-3xl border border-white/10 bg-white/6 p-4">
            <span class="block text-white/40">VOD sites</span>
            <span class="mt-1 block text-white">{{ latestImportedSource?.vod_site_count ?? 0 }}</span>
          </div>
          <div class="rounded-3xl border border-white/10 bg-white/6 p-4">
            <span class="block text-white/40">Live channels</span>
            <span class="mt-1 block text-white">{{ latestImportedSource?.live_channel_count ?? 0 }}</span>
          </div>
        </div>
      </div>

      <p
        v-if="latestJob.detection_note"
        class="mt-5 rounded-2xl border border-white/10 bg-white/6 p-4 text-sm leading-6 text-white/66"
      >
        {{ latestJob.detection_note }}
      </p>
      <p v-if="latestJob.error_message" class="mt-5 rounded-2xl border border-red-300/20 bg-red-400/10 p-4 text-red-100">
        {{ latestJob.error_message }}
      </p>

      <div v-if="latestSiteNames.length || latestCategoryNames.length" class="mt-5 grid gap-4 md:grid-cols-2">
        <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-4">
          <p class="text-xs uppercase tracking-[0.16em] text-white/40">Sample site names</p>
          <div class="mt-3 flex flex-wrap gap-2">
            <span
              v-for="siteName in latestSiteNames"
              :key="siteName"
              class="rounded-full border border-white/10 bg-white/6 px-3 py-1 text-xs text-white/70"
            >
              {{ siteName }}
            </span>
            <span v-if="latestSiteNames.length === 0" class="text-sm text-white/46">No site samples</span>
          </div>
        </div>
        <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-4">
          <p class="text-xs uppercase tracking-[0.16em] text-white/40">Sample categories</p>
          <div class="mt-3 flex flex-wrap gap-2">
            <span
              v-for="category in latestCategoryNames"
              :key="category"
              class="rounded-full border border-white/10 bg-white/6 px-3 py-1 text-xs text-white/70"
            >
              {{ category }}
            </span>
            <span v-if="latestCategoryNames.length === 0" class="text-sm text-white/46">No category samples</span>
          </div>
        </div>
      </div>
    </article>

    <article v-if="latestLiveExtraction" class="glass-panel rounded-[2rem] p-6 sm:p-7">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p class="text-sm uppercase tracking-[0.28em] text-white/42">Latest Live Extraction</p>
          <h2 class="mt-3 text-2xl font-semibold text-white">
            {{ latestLiveExtraction.channels_count }} channels
          </h2>
        </div>
        <div class="grid gap-3 text-sm text-white/62 sm:grid-cols-3 lg:min-w-[34rem]">
          <div class="rounded-3xl border border-white/10 bg-white/6 p-4">
            <span class="block text-white/40">Groups</span>
            <span class="mt-1 block text-white">{{ latestLiveExtraction.groups_count }}</span>
          </div>
          <div class="rounded-3xl border border-white/10 bg-white/6 p-4">
            <span class="block text-white/40">Created</span>
            <span class="mt-1 block text-white">{{ latestLiveExtraction.created_count }}</span>
          </div>
          <div class="rounded-3xl border border-white/10 bg-white/6 p-4">
            <span class="block text-white/40">Updated</span>
            <span class="mt-1 block text-white">{{ latestLiveExtraction.updated_count }}</span>
          </div>
        </div>
      </div>
    </article>

    <div v-if="loading && sources.length === 0" class="grid gap-5 md:grid-cols-2 2xl:grid-cols-3">
      <div v-for="index in 3" :key="index" class="glass-panel min-h-64 animate-pulse rounded-[2rem] p-6">
        <div class="h-4 w-24 rounded-full bg-white/12"></div>
        <div class="mt-16 h-7 w-3/4 rounded-full bg-white/10"></div>
        <div class="mt-5 h-3 w-full rounded-full bg-white/8"></div>
      </div>
    </div>

    <div
      v-else-if="sources.length === 0"
      class="glass-panel flex min-h-72 items-end rounded-[2.5rem] p-7 sm:p-10"
    >
      <div>
        <p class="text-sm uppercase tracking-[0.28em] text-white/42">No sources</p>
        <h2 class="mt-3 max-w-2xl text-3xl font-semibold sm:text-5xl">Create your first source config.</h2>
      </div>
    </div>

    <div v-else class="grid gap-5 md:grid-cols-2 2xl:grid-cols-3">
      <article
        v-for="source in sources"
        :key="source.id"
        tabindex="0"
        class="tv-focus-card glass-panel flex min-h-72 flex-col rounded-[2rem] p-6"
      >
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0">
            <span class="rounded-full border border-white/12 bg-white/8 px-3 py-1 text-xs uppercase tracking-[0.18em] text-white/62">
              {{ detectedTypeLabel(source) }}
            </span>
            <h3 class="mt-5 text-2xl font-semibold text-white">{{ source.name }}</h3>
          </div>
          <NSwitch
            :value="source.enabled"
            :round="true"
            @update:value="(value) => toggleSource(source, value)"
          >
            <template #checked-icon><Power class="h-3 w-3" /></template>
            <template #unchecked-icon><Power class="h-3 w-3" /></template>
          </NSwitch>
        </div>

        <p class="mt-5 truncate text-sm leading-6 text-white/56" :title="source.url">{{ source.url }}</p>

        <div class="mt-6 grid gap-3 text-sm text-white/50">
          <div class="flex justify-between gap-4">
            <span>Detected format</span>
            <span class="text-right text-white/72">{{ source.latest_detected_format ?? 'Not imported' }}</span>
          </div>
          <div class="flex justify-between gap-4">
            <span>Last import</span>
            <span class="text-white/72">{{ formatDate(source.last_import_at) }}</span>
          </div>
          <div class="flex justify-between gap-4">
            <span>VOD sites</span>
            <span class="text-white/72">{{ source.vod_site_count }}</span>
          </div>
          <div class="flex justify-between gap-4">
            <span>Live channels</span>
            <span class="text-white/72">{{ source.live_channel_count }}</span>
          </div>
          <div v-if="sourceCurrentLabel(source)" class="rounded-2xl border border-aurora/25 bg-aurora/10 p-3 text-white">
            <span class="block text-xs uppercase tracking-[0.18em] text-white/48">Current</span>
            <span class="mt-1 block text-sm">{{ sourceCurrentLabel(source) }}</span>
          </div>
          <p v-if="source.last_error" class="rounded-2xl border border-red-300/20 bg-red-400/10 p-3 text-red-100">
            {{ source.last_error }}
          </p>
        </div>

        <div class="mt-6 flex flex-wrap gap-3">
          <NButton
            round
            type="primary"
            :loading="importingIds.has(source.id)"
            @click="runImport(source)"
          >
            <template #icon><CloudDownload class="h-4 w-4" /></template>
            Detect / Import
          </NButton>
          <NButton round secondary :disabled="source.vod_site_count === 0" @click="openSites(source)">
            <template #icon><Rows3 class="h-4 w-4" /></template>
            Sites
          </NButton>
        </div>

        <details class="mt-4 rounded-[1.5rem] border border-white/10 bg-black/18 p-4">
          <summary class="cursor-pointer list-none text-sm font-medium text-white/74">
            Advanced
          </summary>
          <div class="mt-4 flex flex-wrap gap-3">
            <NButton v-if="supportsLiveExtraction(source)" round secondary :loading="extractingLiveIds.has(source.id)" @click="extractLive(source)">
              <template #icon><Waves class="h-4 w-4" /></template>
              Extract Live
            </NButton>
            <NButton
              round
              secondary
              :loading="vodAnalysisLoadingIds.has(source.id)"
              @click="toggleVodAnalysis(source)"
            >
              <template #icon><Rows3 class="h-4 w-4" /></template>
              {{ isVodAnalysisOpen(source.id) ? 'Hide VOD Capability' : 'View VOD Capability' }}
            </NButton>
            <NButton round secondary @click="openEditModal(source)">
              <template #icon><Edit3 class="h-4 w-4" /></template>
              Edit
            </NButton>
            <NButton round secondary type="error" @click="deleteTarget = source">
              <template #icon><Trash2 class="h-4 w-4" /></template>
              Delete
            </NButton>
          </div>

          <div
            v-if="isVodAnalysisOpen(source.id)"
            class="mt-4 rounded-[1.5rem] border border-white/10 bg-black/16 p-4"
          >
            <div v-if="vodAnalysisLoadingIds.has(source.id)" class="space-y-3">
              <div class="h-3 w-28 animate-pulse rounded-full bg-white/12"></div>
              <div class="grid grid-cols-2 gap-2 sm:grid-cols-5">
                <div v-for="index in 5" :key="index" class="h-16 animate-pulse rounded-2xl bg-white/8"></div>
              </div>
            </div>
            <div v-else-if="vodAnalysisErrors[source.id]" class="rounded-2xl border border-red-300/20 bg-red-400/10 p-3 text-xs leading-5 text-red-100">
              {{ vodAnalysisErrors[source.id] }}
            </div>
            <div v-else-if="vodSummary(source.id)" class="space-y-3">
              <div class="flex items-center justify-between gap-4">
                <span class="text-xs uppercase tracking-[0.18em] text-white/42">VOD capability</span>
                <span class="text-xs text-white/42">Snapshot summary</span>
              </div>
              <div class="grid grid-cols-2 gap-2 sm:grid-cols-5">
                <div class="rounded-2xl border border-white/8 bg-white/6 p-3">
                  <span class="block text-[11px] uppercase tracking-[0.16em] text-white/38">Total</span>
                  <span class="mt-2 block text-lg font-semibold text-white">{{ vodSummary(source.id)?.total_sites }}</span>
                </div>
                <div class="rounded-2xl border border-emerald-300/12 bg-emerald-300/8 p-3">
                  <span class="block text-[11px] uppercase tracking-[0.16em] text-white/38">Generic</span>
                  <span class="mt-2 block text-lg font-semibold text-white">{{ vodSummary(source.id)?.generic_candidate_count }}</span>
                </div>
                <div class="rounded-2xl border border-amber-300/14 bg-amber-300/10 p-3">
                  <span class="block text-[11px] uppercase tracking-[0.16em] text-white/38">Spider</span>
                  <span class="mt-2 block text-lg font-semibold text-white">{{ vodSummary(source.id)?.spider_required_count }}</span>
                </div>
                <div class="rounded-2xl border border-red-300/14 bg-red-300/10 p-3">
                  <span class="block text-[11px] uppercase tracking-[0.16em] text-white/38">Unsupported</span>
                  <span class="mt-2 block text-lg font-semibold text-white">{{ vodSummary(source.id)?.unsupported_special_count }}</span>
                </div>
                <div class="rounded-2xl border border-white/8 bg-white/6 p-3">
                  <span class="block text-[11px] uppercase tracking-[0.16em] text-white/38">Unknown</span>
                  <span class="mt-2 block text-lg font-semibold text-white">{{ vodSummary(source.id)?.unknown_count }}</span>
                </div>
              </div>
            </div>
            <p v-else class="text-sm leading-6 text-white/48">No VOD analysis yet.</p>
          </div>
        </details>
      </article>
    </div>
  </section>

  <NModal v-model:show="modalOpen" preset="card" :title="modalTitle" class="source-modal" :bordered="false">
    <NForm ref="formRef" :model="form" :rules="rules" label-placement="top">
      <NFormItem label="Name" path="name">
        <NInput v-model:value="form.name" placeholder="Primary source" />
      </NFormItem>
      <NFormItem label="URL" path="url">
        <NInput v-model:value="form.url" placeholder="https://example.com/source-or-collector" />
      </NFormItem>
      <NFormItem label="Enabled">
        <NSwitch v-model:value="form.enabled" />
      </NFormItem>
      <div class="mt-4 flex justify-end gap-3">
        <NButton round @click="modalOpen = false">Cancel</NButton>
        <NButton round type="primary" :loading="saving" @click="submitForm">
          {{ editingSource ? 'Save' : 'Detect / Import' }}
        </NButton>
      </div>
    </NForm>
  </NModal>

  <NModal
    :show="deleteTarget !== null"
    preset="card"
    title="Delete Source"
    class="source-modal"
    :bordered="false"
    @update:show="(show) => { if (!show) deleteTarget = null }"
  >
    <p class="text-base leading-7 text-white/70">
      Delete <span class="font-semibold text-white">{{ deleteTarget?.name }}</span>? This removes only the source
      configuration record.
    </p>
    <div class="mt-6 flex justify-end gap-3">
      <NButton round @click="deleteTarget = null">Cancel</NButton>
      <NButton round type="error" :loading="saving" @click="confirmDelete">Delete</NButton>
    </div>
  </NModal>

  <NModal
    v-model:show="siteModalOpen"
    preset="card"
    :title="selectedSource ? `${selectedSource.name} Sites` : 'VOD Sites'"
    class="sites-modal"
    :bordered="false"
  >
    <div v-if="loadingSites" class="grid gap-3">
      <div v-for="index in 3" :key="index" class="h-24 animate-pulse rounded-3xl bg-white/8"></div>
    </div>
    <div v-else class="grid max-h-[70vh] gap-3 overflow-y-auto pr-1">
      <article
        v-for="site in selectedSites"
        :key="site.id"
        class="rounded-3xl border bg-white/6 p-4"
        :class="isCurrentSite(site) ? 'border-aurora/60 shadow-glow' : 'border-white/10'"
      >
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <h3 class="text-lg font-semibold text-white">{{ site.site_name }}</h3>
              <span class="rounded-full border border-white/10 px-2 py-1 text-xs text-white/54">
                {{ site.site_key }}
              </span>
              <span class="rounded-full border border-white/10 px-2 py-1 text-xs text-white/54">
                type {{ site.site_type ?? 'unknown' }}
              </span>
              <span
                v-if="isCurrentSite(site)"
                class="rounded-full border border-aurora/30 bg-aurora/15 px-2 py-1 text-xs text-white"
              >
                Current
              </span>
            </div>
            <p class="mt-3 break-all text-sm leading-6 text-white/54">{{ site.api ?? 'No API' }}</p>
          </div>
          <div class="flex shrink-0 items-center gap-3">
            <NButton
              round
              size="small"
              type="primary"
              :disabled="!site.enabled || isCurrentSite(site)"
              :loading="settingCurrentIds.has(site.id)"
              @click="useVodSite(site)"
            >
              <template #icon><CheckCircle2 class="h-4 w-4" /></template>
              {{ isCurrentSite(site) ? 'Current' : 'Use This' }}
            </NButton>
            <NSwitch :value="site.enabled" @update:value="(value) => toggleVodSite(site, value)" />
          </div>
        </div>
        <p v-if="site.analysis_note" class="mt-3 rounded-2xl border border-white/10 bg-black/18 p-3 text-xs leading-5 text-white/54">
          {{ site.analysis_note }}
        </p>
      </article>
      <p v-if="selectedSites.length === 0" class="rounded-3xl border border-white/10 bg-white/6 p-6 text-white/58">
        No sites extracted for this source.
      </p>
    </div>
  </NModal>

  <NModal
    :show="livePreviewSource !== null"
    preset="card"
    :title="livePreviewSource ? `${livePreviewSource.name} Live Preview` : 'Live Preview'"
    class="sites-modal"
    :bordered="false"
    @update:show="(show) => { if (!show && !confirmingLiveImport) closeLivePreview() }"
  >
    <div v-if="livePreviewLoading" class="grid gap-3">
      <div class="h-20 animate-pulse rounded-3xl bg-white/8"></div>
      <div class="h-28 animate-pulse rounded-3xl bg-white/8"></div>
      <div class="h-52 animate-pulse rounded-3xl bg-white/8"></div>
    </div>
    <div v-else-if="livePreview" class="space-y-4">
      <div class="grid gap-3 text-sm text-white/62 sm:grid-cols-3">
        <div class="rounded-3xl border border-white/10 bg-white/6 p-4">
          <span class="block text-white/40">Detected format</span>
          <span class="mt-1 block text-white">{{ livePreview.detected_format ?? 'Unknown' }}</span>
        </div>
        <div class="rounded-3xl border border-white/10 bg-white/6 p-4">
          <span class="block text-white/40">Live channels</span>
          <span class="mt-1 block text-white">{{ livePreview.channels_count }}</span>
        </div>
        <div class="rounded-3xl border border-white/10 bg-white/6 p-4">
          <span class="block text-white/40">Groups</span>
          <span class="mt-1 block text-white">{{ livePreview.groups_count }}</span>
        </div>
      </div>

      <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-4">
        <p class="text-xs uppercase tracking-[0.16em] text-white/40">Group names</p>
        <div class="mt-3 flex flex-wrap gap-2">
          <span
            v-for="groupName in livePreview.group_names"
            :key="groupName"
            class="rounded-full border border-white/10 bg-white/6 px-3 py-1 text-xs text-white/70"
          >
            {{ groupName }}
          </span>
          <span v-if="livePreview.group_names.length === 0" class="text-sm text-white/46">No groups found</span>
        </div>
      </div>

      <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-4">
        <div class="flex items-center justify-between gap-4">
          <p class="text-xs uppercase tracking-[0.16em] text-white/40">Preview channels</p>
          <span class="text-xs text-white/42">First {{ livePreview.preview_channels.length }} items</span>
        </div>
        <div class="mt-3 grid max-h-[40vh] gap-3 overflow-y-auto pr-1">
          <article
            v-for="channel in livePreview.preview_channels"
            :key="`${channel.name}-${channel.stream_url}`"
            class="rounded-3xl border border-white/10 bg-white/6 p-4"
          >
            <div class="flex flex-wrap items-center gap-2">
              <h3 class="text-sm font-semibold text-white">{{ channel.name }}</h3>
              <span
                v-if="channel.group_title"
                class="rounded-full border border-white/10 px-2 py-1 text-[11px] text-white/54"
              >
                {{ channel.group_title }}
              </span>
            </div>
            <p class="mt-2 break-all text-xs leading-5 text-white/46">{{ channel.stream_url }}</p>
          </article>
          <p v-if="livePreview.preview_channels.length === 0" class="text-sm text-white/46">No channels found.</p>
        </div>
      </div>

      <div
        v-if="livePreview.warnings.length"
        class="rounded-[1.5rem] border border-amber-300/16 bg-amber-300/10 p-4 text-sm leading-6 text-amber-50"
      >
        <p v-for="warning in livePreview.warnings" :key="warning">{{ warning }}</p>
      </div>

      <div class="flex justify-end gap-3">
        <NButton round :disabled="confirmingLiveImport" @click="closeLivePreview">Cancel</NButton>
        <NButton
          round
          type="primary"
          :disabled="livePreview.channels_count === 0"
          :loading="confirmingLiveImport || extractingLiveIds.has(livePreviewSource?.id ?? '')"
          @click="confirmLiveImport"
        >
          Confirm Import
        </NButton>
      </div>
    </div>
  </NModal>
</template>

<style scoped>
:deep(.source-modal) {
  width: min(92vw, 34rem);
  border-radius: 2rem;
  background: rgba(14, 16, 22, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.14);
  backdrop-filter: blur(28px);
}

:deep(.sites-modal) {
  width: min(94vw, 58rem);
  border-radius: 2rem;
  background: rgba(14, 16, 22, 0.92);
  border: 1px solid rgba(255, 255, 255, 0.14);
  backdrop-filter: blur(28px);
}
</style>
