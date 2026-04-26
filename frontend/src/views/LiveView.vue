<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Search, SlidersHorizontal, Tv } from 'lucide-vue-next'
import { NButton, NInput, NSwitch, useMessage } from 'naive-ui'

import {
  listLiveChannels,
  listLiveGroups,
  updateLiveChannel,
  type LiveChannel,
  type LiveChannelGroup,
} from '@/api/sourceConfigs'
import { ApiError } from '@/api/client'

const message = useMessage()
const groups = ref<LiveChannelGroup[]>([])
const channels = ref<LiveChannel[]>([])
const selectedGroupId = ref<string | null>(null)
const query = ref('')
const loading = ref(false)
const togglingIds = ref<Set<string>>(new Set())

const selectedGroupName = computed(
  () => groups.value.find((group) => group.id === selectedGroupId.value)?.name ?? 'All Channels',
)

async function loadLiveData() {
  loading.value = true
  try {
    const [groupResult, channelResult] = await Promise.all([
      listLiveGroups(),
      listLiveChannels({ group_id: selectedGroupId.value ?? undefined, q: query.value || undefined }),
    ])
    groups.value = groupResult
    channels.value = channelResult
  } catch (error) {
    message.error(error instanceof ApiError ? error.message : 'Unable to load live channels')
  } finally {
    loading.value = false
  }
}

async function toggleChannel(channel: LiveChannel, enabled: boolean) {
  const previous = channel.enabled
  channel.enabled = enabled
  togglingIds.value = new Set(togglingIds.value).add(channel.id)
  try {
    const updated = await updateLiveChannel(channel.id, enabled)
    channels.value = channels.value.map((item) => (item.id === updated.id ? updated : item))
  } catch (error) {
    channel.enabled = previous
    message.error(error instanceof ApiError ? error.message : 'Unable to update channel')
  } finally {
    const next = new Set(togglingIds.value)
    next.delete(channel.id)
    togglingIds.value = next
  }
}

let searchTimer: number | undefined
watch(query, () => {
  window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(loadLiveData, 250)
})

watch(selectedGroupId, loadLiveData)

onMounted(loadLiveData)
</script>

<template>
  <section class="grid gap-6">
    <div class="glass-panel rounded-[2.5rem] p-6 sm:p-8">
      <div class="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p class="text-sm uppercase tracking-[0.28em] text-white/42">Live TV</p>
          <h2 class="mt-3 text-4xl font-semibold text-white sm:text-6xl">{{ selectedGroupName }}</h2>
          <p class="mt-4 max-w-3xl text-sm leading-6 text-white/58">
            Imported M3U channels are listed here for source verification. Playback is not enabled yet.
          </p>
        </div>
        <div class="flex w-full flex-col gap-3 sm:flex-row xl:w-auto">
          <NInput v-model:value="query" round clearable placeholder="Search channels" class="min-w-72">
            <template #prefix><Search class="h-4 w-4 text-white/42" /></template>
          </NInput>
          <NButton round secondary :loading="loading" @click="loadLiveData">
            <template #icon><SlidersHorizontal class="h-4 w-4" /></template>
            Refresh
          </NButton>
        </div>
      </div>
    </div>

    <div class="flex gap-3 overflow-x-auto pb-2">
      <button
        class="tv-focus-card shrink-0 rounded-full border px-5 py-3 text-sm transition"
        :class="selectedGroupId === null ? 'border-aurora/40 bg-aurora/18 text-white' : 'border-white/10 bg-white/6 text-white/62'"
        @click="selectedGroupId = null"
      >
        All
      </button>
      <button
        v-for="group in groups"
        :key="group.id"
        class="tv-focus-card shrink-0 rounded-full border px-5 py-3 text-sm transition"
        :class="selectedGroupId === group.id ? 'border-aurora/40 bg-aurora/18 text-white' : 'border-white/10 bg-white/6 text-white/62'"
        @click="selectedGroupId = group.id"
      >
        {{ group.name }}
        <span class="ml-2 text-white/42">{{ group.channel_count }}</span>
      </button>
    </div>

    <div v-if="loading && channels.length === 0" class="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
      <div v-for="index in 8" :key="index" class="glass-panel h-56 animate-pulse rounded-[2rem]"></div>
    </div>

    <div
      v-else-if="channels.length === 0"
      class="glass-panel flex min-h-72 items-end rounded-[2.5rem] p-7 sm:p-10"
    >
      <div>
        <p class="text-sm uppercase tracking-[0.28em] text-white/42">No Channels</p>
        <h2 class="mt-3 max-w-2xl text-3xl font-semibold sm:text-5xl">Import and extract a live M3U source first.</h2>
      </div>
    </div>

    <div v-else class="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
      <article
        v-for="channel in channels"
        :key="channel.id"
        tabindex="0"
        class="tv-focus-card glass-panel flex min-h-60 flex-col overflow-hidden rounded-[2rem]"
      >
        <div class="flex h-32 items-center justify-center bg-white/6">
          <img
            v-if="channel.tvg_logo"
            :src="channel.tvg_logo"
            :alt="channel.name"
            class="max-h-24 max-w-[70%] object-contain"
            loading="lazy"
          />
          <div v-else class="flex h-20 w-20 items-center justify-center rounded-[1.5rem] bg-white/10">
            <Tv class="h-9 w-9 text-white/62" />
          </div>
        </div>
        <div class="flex flex-1 flex-col p-5">
          <div class="flex items-start justify-between gap-4">
            <div>
              <h3 class="line-clamp-2 text-xl font-semibold text-white">{{ channel.name }}</h3>
              <p class="mt-2 text-sm text-white/46">{{ channel.group_title ?? 'Ungrouped' }}</p>
            </div>
            <NSwitch
              :value="channel.enabled"
              :loading="togglingIds.has(channel.id)"
              @update:value="(value) => toggleChannel(channel, value)"
            />
          </div>
          <p class="mt-auto line-clamp-2 break-all pt-5 font-mono text-xs text-white/40">
            {{ channel.stream_url }}
          </p>
        </div>
      </article>
    </div>
  </section>
</template>
