<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  CloudDownload,
  Edit3,
  Plus,
  Power,
  RefreshCw,
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
  importSourceConfig,
  listSourceConfigs,
  updateSourceConfig,
  type ImportJob,
  type SourceConfig,
  type SourceConfigPayload,
  type SourceType,
} from '@/api/sourceConfigs'
import { ApiError } from '@/api/client'

const message = useMessage()
const sources = ref<SourceConfig[]>([])
const loading = ref(false)
const saving = ref(false)
const importingIds = ref<Set<string>>(new Set())
const latestJob = ref<ImportJob | null>(null)
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
  } catch (error) {
    source.enabled = previous
    showError(error, 'Unable to update source')
  }
}

async function runImport(source: SourceConfig) {
  importingIds.value = new Set(importingIds.value).add(source.id)
  try {
    latestJob.value = await importSourceConfig(source.id)
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

onMounted(loadSources)
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
          <p v-if="source.last_error" class="rounded-2xl border border-red-300/20 bg-red-400/10 p-3 text-red-100">
            {{ source.last_error }}
          </p>
        </div>

        <div class="mt-6 flex gap-3">
          <NButton
            round
            type="primary"
            :loading="importingIds.has(source.id)"
            @click="runImport(source)"
          >
            <template #icon><CloudDownload class="h-4 w-4" /></template>
            Import
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
</template>

<style scoped>
:deep(.source-modal) {
  width: min(92vw, 34rem);
  border-radius: 2rem;
  background: rgba(14, 16, 22, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.14);
  backdrop-filter: blur(28px);
}
</style>
