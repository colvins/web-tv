<script setup lang="ts">
import { onMounted, ref } from 'vue'

import HomeContinueWatchingRail from '@/components/home/HomeContinueWatchingRail.vue'
import { listRecentVodPlayback, type RecentVodPlaybackItem } from '@/utils/recentVodPlayback'

const historyItems = ref<RecentVodPlaybackItem[]>([])

onMounted(() => {
  historyItems.value = listRecentVodPlayback()
})
</script>

<template>
  <section class="pb-8">
    <HomeContinueWatchingRail
      :items="historyItems"
      title="Watch History"
      eyebrow="History"
      empty-message="Recent VOD plays will appear here after you start an episode."
    />
  </section>
</template>
