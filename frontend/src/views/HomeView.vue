<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { ApiError } from '@/api/client'
import { getCurrentVodSite, getVodList, type CurrentVodSite, type VodBrowseItem } from '@/api/sourceConfigs'
import HomeContinueWatchingRail from '@/components/home/HomeContinueWatchingRail.vue'
import HomeHeroCarousel from '@/components/home/HomeHeroCarousel.vue'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

const currentVodSite = ref<CurrentVodSite | null>(null)
const latestItems = ref<VodBrowseItem[]>([])
const heroLoading = ref(false)
const heroError = ref<string | null>(null)

const recentItems = computed(() => appStore.recentVodPlayback)

async function loadHomeHero() {
  heroLoading.value = true
  heroError.value = null

  try {
    currentVodSite.value = await getCurrentVodSite()

    if (!currentVodSite.value?.source_config_id) {
      latestItems.value = []
      return
    }

    const response = await getVodList({
      source_config_id: currentVodSite.value.source_config_id,
      site_key: currentVodSite.value.site_key,
      page: 1,
    })
    latestItems.value = response.items.filter((item) => Boolean(item.poster)).slice(0, 18)
  } catch (error) {
    latestItems.value = []
    heroError.value = error instanceof ApiError ? error.message : 'Unable to load home recommendations'
  } finally {
    heroLoading.value = false
  }
}

onMounted(() => {
  appStore.ensurePersistentStateLoaded()
  void loadHomeHero()
})
</script>

<template>
  <section class="pb-8">
    <HomeHeroCarousel
      :source-config-id="currentVodSite?.source_config_id ?? null"
      :site-key="currentVodSite?.site_key ?? null"
      :items="latestItems"
      :loading="heroLoading"
    />

    <p v-if="heroError" class="mt-4 rounded-[1.5rem] border border-red-300/16 bg-red-400/10 px-4 py-3 text-sm text-red-100">
      {{ heroError }}
    </p>

    <HomeContinueWatchingRail :items="recentItems" />
  </section>
</template>
