<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RefreshCw, Settings } from 'lucide-vue-next'
import { NButton, useMessage } from 'naive-ui'
import { RouterLink } from 'vue-router'

import {
  getCurrentVodSite,
  getCurrentVodSiteAnalysis,
  type CurrentVodSite,
  type CurrentVodSiteAnalysis,
} from '@/api/sourceConfigs'
import { ApiError } from '@/api/client'

const message = useMessage()
const currentSite = ref<CurrentVodSite | null>(null)
const analysis = ref<CurrentVodSiteAnalysis | null>(null)
const analysisError = ref<string | null>(null)
const loading = ref(false)

const knownFlagItems = computed(() =>
  analysis.value
    ? Object.entries(analysis.value.known_flags).map(([key, value]) => ({
        key,
        value: formatFlagValue(value),
      }))
    : [],
)

async function loadCurrentSite() {
  loading.value = true
  analysis.value = null
  analysisError.value = null
  try {
    currentSite.value = await getCurrentVodSite()
    if (currentSite.value) {
      try {
        const result = await getCurrentVodSiteAnalysis()
        if (result) {
          analysis.value = result
        } else {
          analysisError.value = 'Compatibility analysis is unavailable for the selected site.'
        }
      } catch (error) {
        analysisError.value =
          error instanceof ApiError ? error.message : 'Unable to load compatibility analysis'
      }
    }
  } catch (error) {
    message.error(error instanceof ApiError ? error.message : 'Unable to load current VOD site')
  } finally {
    loading.value = false
  }
}

function formatFlagValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return 'Not provided'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (typeof value === 'number' && (value === 0 || value === 1)) return value === 1 ? 'Yes' : 'No'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function supportLevelLabel(level: CurrentVodSiteAnalysis['support_assessment']['level']) {
  return level.replaceAll('_', ' ')
}

onMounted(loadCurrentSite)
</script>

<template>
  <section class="grid gap-6">
    <div
      v-if="!currentSite"
      class="glass-panel flex min-h-[24rem] items-end rounded-[2.5rem] p-7 sm:p-10"
    >
      <div class="max-w-3xl">
        <p class="text-sm uppercase tracking-[0.28em] text-white/42">VOD Source</p>
        <h2 class="mt-3 text-4xl font-semibold text-white sm:text-6xl">No VOD site selected</h2>
        <p class="mt-5 text-base leading-7 text-white/58">
          Choose a site from Source Settings before browsing VOD.
        </p>
        <div class="mt-8 flex flex-wrap gap-3">
          <RouterLink
            to="/settings/sources"
            class="tv-focus-card glass-panel inline-flex min-h-12 items-center rounded-3xl px-5 text-sm font-medium"
          >
            <Settings class="mr-2 h-4 w-4" aria-hidden="true" />
            Source Settings
          </RouterLink>
          <NButton round secondary :loading="loading" @click="loadCurrentSite">
            <template #icon><RefreshCw class="h-4 w-4" /></template>
            Refresh
          </NButton>
        </div>
      </div>
    </div>

    <article
      v-else
      class="glass-panel overflow-hidden rounded-[2.5rem] bg-[linear-gradient(135deg,rgba(137,180,255,0.18),rgba(255,184,107,0.1))] p-7 sm:p-10"
    >
      <div class="flex flex-col gap-8 xl:flex-row xl:items-end xl:justify-between">
        <div class="max-w-4xl">
          <p class="text-sm uppercase tracking-[0.28em] text-white/48">Current VOD Source</p>
          <h2 class="mt-4 text-4xl font-semibold text-white sm:text-6xl">{{ currentSite.site_name }}</h2>
          <p class="mt-5 max-w-3xl text-base leading-7 text-white/62">
            Browsing is not enabled yet. This page only verifies the selected source.
          </p>
        </div>
        <NButton round secondary :loading="loading" @click="loadCurrentSite">
          <template #icon><RefreshCw class="h-4 w-4" /></template>
          Refresh
        </NButton>
      </div>

      <div class="mt-10 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-5">
          <p class="text-sm text-white/42">Site key</p>
          <p class="mt-2 break-all text-lg font-semibold text-white">{{ currentSite.site_key }}</p>
        </div>
        <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-5">
          <p class="text-sm text-white/42">Type</p>
          <p class="mt-2 text-lg font-semibold text-white">{{ currentSite.site_type ?? 'Unknown' }}</p>
        </div>
        <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-5">
          <p class="text-sm text-white/42">Enabled</p>
          <p class="mt-2 text-lg font-semibold text-white">{{ currentSite.enabled ? 'Yes' : 'No' }}</p>
        </div>
        <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-5 md:col-span-2">
          <p class="text-sm text-white/42">API</p>
          <p class="mt-2 break-all text-lg font-semibold text-white">{{ currentSite.api ?? 'None' }}</p>
        </div>
        <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-5">
          <p class="text-sm text-white/42">Source package</p>
          <p class="mt-2 text-lg font-semibold text-white">{{ currentSite.source_name ?? 'Unknown' }}</p>
        </div>
        <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-5 md:col-span-2 xl:col-span-3">
          <p class="text-sm text-white/42">Source config ID</p>
          <p class="mt-2 break-all font-mono text-sm text-white/78">{{ currentSite.source_config_id ?? 'None' }}</p>
        </div>
      </div>
    </article>

    <article v-if="currentSite" class="glass-panel rounded-[2.25rem] p-6 sm:p-8">
      <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p class="text-sm uppercase tracking-[0.26em] text-white/42">Compatibility Analysis</p>
          <h3 class="mt-3 text-2xl font-semibold text-white sm:text-3xl">
            {{ analysis ? supportLevelLabel(analysis.support_assessment.level) : 'Source metadata' }}
          </h3>
        </div>
        <div
          v-if="analysis"
          class="rounded-full border border-white/10 bg-white/8 px-4 py-2 text-sm capitalize text-white/78"
        >
          {{ supportLevelLabel(analysis.support_assessment.level) }}
        </div>
      </div>

      <p v-if="analysisError" class="mt-5 rounded-3xl border border-amber-300/20 bg-amber-300/10 p-4 text-sm text-amber-100">
        {{ analysisError }}
      </p>

      <div v-else-if="analysis" class="mt-7 grid gap-4 lg:grid-cols-3">
        <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-5 lg:col-span-2">
          <p class="text-sm text-white/42">Assessment</p>
          <p class="mt-3 text-lg font-semibold text-white">{{ analysis.support_assessment.reason }}</p>
          <p class="mt-3 text-sm leading-6 text-white/58">{{ analysis.support_assessment.next_step }}</p>
        </div>
        <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-5">
          <p class="text-sm text-white/42">Raw keys</p>
          <div class="mt-3 flex flex-wrap gap-2">
            <span
              v-for="key in analysis.raw_keys"
              :key="key"
              class="rounded-full bg-white/8 px-3 py-1 text-xs text-white/72"
            >
              {{ key }}
            </span>
            <span v-if="analysis.raw_keys.length === 0" class="text-sm text-white/52">No raw keys</span>
          </div>
        </div>

        <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-5 lg:col-span-2">
          <p class="text-sm text-white/42">Known flags</p>
          <div class="mt-4 grid gap-3 sm:grid-cols-2">
            <div v-for="item in knownFlagItems" :key="item.key" class="min-w-0">
              <p class="text-xs uppercase tracking-[0.16em] text-white/32">{{ item.key }}</p>
              <p class="mt-1 break-all text-sm text-white/78">{{ item.value }}</p>
            </div>
          </div>
        </div>

        <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-5">
          <p class="text-sm text-white/42">ext analysis</p>
          <div class="mt-3 space-y-2 text-sm text-white/70">
            <p>Present: {{ analysis.ext_analysis.present ? 'Yes' : 'No' }}</p>
            <p>Type: {{ analysis.ext_analysis.value_type ?? 'None' }}</p>
            <p>URL-like: {{ analysis.ext_analysis.looks_like_url ? 'Yes' : 'No' }}</p>
            <p>JSON-like: {{ analysis.ext_analysis.looks_like_json ? 'Yes' : 'No' }}</p>
            <p>Base64-like: {{ analysis.ext_analysis.looks_like_base64 ? 'Yes' : 'No' }}</p>
            <p>Opaque: {{ analysis.ext_analysis.looks_like_executable_or_opaque ? 'Yes' : 'No' }}</p>
          </div>
          <p
            v-if="analysis.ext_analysis.summary"
            class="mt-4 max-h-28 overflow-auto break-all rounded-2xl bg-white/6 p-3 font-mono text-xs text-white/58"
          >
            {{ analysis.ext_analysis.summary }}
          </p>
        </div>

        <div
          v-if="analysis.warnings.length"
          class="rounded-[1.5rem] border border-amber-300/18 bg-amber-300/10 p-5 lg:col-span-3"
        >
          <p class="text-sm text-amber-100/70">Warnings</p>
          <ul class="mt-3 grid gap-2 text-sm text-amber-50/82">
            <li v-for="warning in analysis.warnings" :key="warning">{{ warning }}</li>
          </ul>
        </div>
      </div>

      <div v-else class="mt-7 grid gap-4 lg:grid-cols-3">
        <div class="rounded-[1.5rem] border border-white/10 bg-black/18 p-5 lg:col-span-3">
          <p class="text-sm text-white/52">Loading compatibility analysis...</p>
        </div>
      </div>
    </article>
  </section>
</template>
