<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RefreshCw, Settings } from 'lucide-vue-next'
import { NButton, useMessage } from 'naive-ui'
import { RouterLink } from 'vue-router'

import { getCurrentVodSite, type CurrentVodSite } from '@/api/sourceConfigs'
import { ApiError } from '@/api/client'

const message = useMessage()
const currentSite = ref<CurrentVodSite | null>(null)
const loading = ref(false)

async function loadCurrentSite() {
  loading.value = true
  try {
    currentSite.value = await getCurrentVodSite()
  } catch (error) {
    message.error(error instanceof ApiError ? error.message : 'Unable to load current VOD site')
  } finally {
    loading.value = false
  }
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
  </section>
</template>
