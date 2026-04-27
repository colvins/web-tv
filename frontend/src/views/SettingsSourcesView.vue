<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  CloudDownload,
  DatabaseZap,
  Edit3,
  CheckCircle2,
  Plus,
  Power,
  RefreshCw,
  Rows3,
  Trash2,
} from 'lucide-vue-next'
import {
  NButton,
  NForm,
  NFormItem,
  NInput,
  NModal,
  NSelect,
  NSwitch,
  useMessage,
  type FormInst,
  type FormRules,
} from 'naive-ui'

import {
  createSourceConfig,
  deleteSourceConfig,
  extractLiveChannels,
  extractVodSites,
  getCurrentVodSite,
  getLatestVodCapabilityAnalysis,
  importSourceConfig,
  listSourceVodSites,
  listSourceConfigs,
  setCurrentVodSite,
  updateVodSite,
  updateSourceConfig,
  type ImportJob,
  type LiveExtractionStats,
  type CurrentVodSite,
  type SourceConfig,
  type SourceConfigPayload,
  type SourceType,
  type VodCapabilityAnalysis,
  type VodSite,
} from '@/api/sourceConfigs'
import { ApiError } from '@/api/client'

const message = useMessage()
const sources = ref<SourceConfig[]>([])
const loading = ref(false)
const saving = ref(false)
const importingIds = ref<Set<string>>(new Set())
const extractingIds = ref<Set<string>>(new Set())
const extractingLiveIds = ref<Set<string>>(new Set())
const latestJob = ref<ImportJob | null>(null)
const latestLiveExtraction = ref<LiveExtractionStats | null>(null)
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

const sourceTypeOptions: Array<{ label: string; value: SourceType }> = [
  { label: 'JSON', value: 'json' },
  { label: 'M3U', value: 'm3u' },
  { label: 'TXT', value: 'txt' },
  { label: 'M3U8', value: 'm3u8' },
]

const form = reactive<SourceConfigPayload>({
  name: '',
  source_type: 'json',
  url: '',
  enabled: true,
})

const rules: FormRules = {
  name: [{ required: true, message: 'Name is required', trigger: ['input', 'blur'] }],
  source_type: [{ required: true, message: 'Type is required', trigger: ['change', 'blur'] }],
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
const modalTitle = computed(() => (editingSource.value ? 'Edit Source' : 'Add Source'))

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

async function submitForm() {
  await formRef.value?.validate()
  saving.value = true
  try {
    if (editingSource.value) {
      const updated = await updateSourceConfig(editingSource.value.id, { ...form })
      sources.value = sources.value.map((source) => (source.id === updated.id ? updated : source))
      message.success('Source updated')
    } else {
      const created = await createSourceConfig({ ...form })
      sources.value = [created, ...sources.value]
      message.success('Source created')
    }
    modalOpen.value = false
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

async function runImport(source: SourceConfig) {
  importingIds.value = new Set(importingIds.value).add(source.id)
  try {
    latestJob.value = await importSourceConfig(source.id)
    resetVodAnalysis(source.id)
    await loadSources()
    if (latestJob.value.status === 'success') {
      message.success('Import completed')
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

async function extractSites(source: SourceConfig) {
  extractingIds.value = new Set(extractingIds.value).add(source.id)
  try {
    selectedSites.value = await extractVodSites(source.id)
    resetVodAnalysis(source.id)
    selectedSource.value = source
    siteModalOpen.value = true
    await loadSources()
    await loadCurrentVodSite()
    message.success(`Extracted ${selectedSites.value.length} sites`)
  } catch (error) {
    showError(error, 'Unable to extract sites')
  } finally {
    const next = new Set(extractingIds.value)
    next.delete(source.id)
    extractingIds.value = next
  }
}

async function extractLive(source: SourceConfig) {
  extractingLiveIds.value = new Set(extractingLiveIds.value).add(source.id)
  try {
    latestLiveExtraction.value = await extractLiveChannels(source.id)
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

function formatBytes(value: number | null) {
  if (value === null) return 'Unknown'
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / 1024 / 1024).toFixed(2)} MB`
}

function shortSha(value: string | null) {
  return value ? value.slice(0, 12) : 'None'
}

function formatConfidence(value: number | null) {
  return value === null ? 'Unknown' : `${Math.round(value * 100)}%`
}

function shortApi(value: string | null) {
  if (!value) return 'No API'
  return value.length > 64 ? `${value.slice(0, 64)}...` : value
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
          <h2 class="mt-3 text-3xl font-semibold sm:text-5xl">Manage source configs.</h2>
          <p class="mt-4 max-w-3xl text-sm leading-6 text-white/58">
            Add JSON, M3U, TXT, and M3U8 source endpoints. Import and parsing behavior stays outside this screen.
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

      <div class="mt-8 grid gap-4 sm:grid-cols-3">
        <div class="rounded-[1.5rem] border border-white/10 bg-white/6 p-5">
          <p class="text-sm text-white/46">Total</p>
          <p class="mt-2 text-3xl font-semibold">{{ sources.length }}</p>
        </div>
        <div class="rounded-[1.5rem] border border-white/10 bg-white/6 p-5">
          <p class="text-sm text-white/46">Enabled</p>
          <p class="mt-2 text-3xl font-semibold">{{ enabledCount }}</p>
        </div>
        <div class="rounded-[1.5rem] border border-white/10 bg-white/6 p-5">
          <p class="text-sm text-white/46">Types</p>
          <p class="mt-2 text-3xl font-semibold">4</p>
        </div>
      </div>
      <div class="mt-4 rounded-[1.5rem] border border-white/10 bg-white/6 p-5">
        <p class="text-sm text-white/46">Current VOD site</p>
        <p class="mt-2 text-lg font-semibold text-white">
          <span v-if="currentVodSite">{{ currentVodSite.site_name }} / {{ currentVodSite.site_key }}</span>
          <span v-else>No VOD site selected</span>
        </p>
      </div>
    </div>

    <article v-if="latestJob" class="glass-panel rounded-[2rem] p-6 sm:p-7">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p class="text-sm uppercase tracking-[0.28em] text-white/42">Latest Import</p>
          <h2 class="mt-3 text-2xl font-semibold text-white">
            {{ latestJob.status }}
          </h2>
        </div>
        <div class="grid gap-3 text-sm text-white/62 sm:grid-cols-3 lg:min-w-[34rem]">
          <div class="rounded-3xl border border-white/10 bg-white/6 p-4">
            <span class="block text-white/40">Format</span>
            <span class="mt-1 block text-white">{{ latestJob.detected_format ?? 'Unknown' }}</span>
          </div>
          <div class="rounded-3xl border border-white/10 bg-white/6 p-4">
            <span class="block text-white/40">Confidence</span>
            <span class="mt-1 block text-white">{{ formatConfidence(latestJob.detection_confidence) }}</span>
          </div>
          <div class="rounded-3xl border border-white/10 bg-white/6 p-4">
            <span class="block text-white/40">Type</span>
            <span class="mt-1 block break-words text-white">{{ latestJob.content_type ?? 'Unknown' }}</span>
          </div>
          <div class="rounded-3xl border border-white/10 bg-white/6 p-4">
            <span class="block text-white/40">Length</span>
            <span class="mt-1 block text-white">{{ formatBytes(latestJob.content_length) }}</span>
          </div>
          <div class="rounded-3xl border border-white/10 bg-white/6 p-4">
            <span class="block text-white/40">SHA256</span>
            <span class="mt-1 block font-mono text-white">{{ shortSha(latestJob.content_sha256) }}</span>
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
      <pre
        v-if="latestJob.raw_preview"
        class="mt-5 max-h-80 overflow-auto whitespace-pre-wrap break-words rounded-[1.5rem] border border-white/10 bg-black/24 p-5 text-sm leading-6 text-white/68"
      >{{ latestJob.raw_preview }}</pre>
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
      <div v-if="latestLiveExtraction.warnings.length" class="mt-5 grid gap-2">
        <p
          v-for="warning in latestLiveExtraction.warnings"
          :key="warning"
          class="rounded-2xl border border-white/10 bg-white/6 p-4 text-sm leading-6 text-white/66"
        >
          {{ warning }}
        </p>
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
          <div>
            <span class="rounded-full border border-white/12 bg-white/8 px-3 py-1 text-xs uppercase tracking-[0.18em] text-white/62">
              {{ source.source_type }}
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

        <p class="mt-5 line-clamp-2 break-all text-sm leading-6 text-white/56">{{ source.url }}</p>

        <div class="mt-auto grid gap-3 pt-8 text-sm text-white/50">
          <div class="flex justify-between gap-4">
            <span>Last import</span>
            <span class="text-white/72">{{ formatDate(source.last_import_at) }}</span>
          </div>
          <div class="flex justify-between gap-4">
            <span>Last success</span>
            <span class="text-white/72">{{ formatDate(source.last_success_at) }}</span>
          </div>
          <div class="flex justify-between gap-4">
            <span>VOD sites</span>
            <span class="text-white/72">{{ source.vod_site_count }}</span>
          </div>
          <div class="flex justify-between gap-4">
            <span>Live channels</span>
            <span class="text-white/72">{{ source.live_channel_count }}</span>
          </div>
          <div
            v-if="isVodAnalysisOpen(source.id)"
            class="rounded-[1.5rem] border border-white/10 bg-black/16 p-4"
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
            Import
          </NButton>
          <NButton
            round
            secondary
            :loading="extractingIds.has(source.id)"
            @click="extractSites(source)"
          >
            <template #icon><DatabaseZap class="h-4 w-4" /></template>
            Extract Sites
          </NButton>
          <NButton
            v-if="supportsLiveExtraction(source)"
            round
            secondary
            :loading="extractingLiveIds.has(source.id)"
            @click="extractLive(source)"
          >
            <template #icon><DatabaseZap class="h-4 w-4" /></template>
            Extract Live
          </NButton>
          <NButton round secondary :disabled="source.vod_site_count === 0" @click="openSites(source)">
            <template #icon><Rows3 class="h-4 w-4" /></template>
            Sites
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
          <NButton round secondary class="flex-1" @click="openEditModal(source)">
            <template #icon><Edit3 class="h-4 w-4" /></template>
            Edit
          </NButton>
          <NButton round secondary type="error" @click="deleteTarget = source">
            <template #icon><Trash2 class="h-4 w-4" /></template>
          </NButton>
        </div>
      </article>
    </div>
  </section>

  <NModal v-model:show="modalOpen" preset="card" :title="modalTitle" class="source-modal" :bordered="false">
    <NForm ref="formRef" :model="form" :rules="rules" label-placement="top">
      <NFormItem label="Name" path="name">
        <NInput v-model:value="form.name" placeholder="Primary source" />
      </NFormItem>
      <NFormItem label="Type" path="source_type">
        <NSelect v-model:value="form.source_type" :options="sourceTypeOptions" />
      </NFormItem>
      <NFormItem label="URL" path="url">
        <NInput v-model:value="form.url" placeholder="https://example.com/source.json" />
      </NFormItem>
      <NFormItem label="Enabled">
        <NSwitch v-model:value="form.enabled" />
      </NFormItem>
      <div class="mt-4 flex justify-end gap-3">
        <NButton round @click="modalOpen = false">Cancel</NButton>
        <NButton round type="primary" :loading="saving" @click="submitForm">Save</NButton>
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
            <p class="mt-3 break-all text-sm leading-6 text-white/54">{{ shortApi(site.api) }}</p>
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
