<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'

import type { VodBrowseItem } from '@/api/sourceConfigs'
import VodPoster from '@/components/vod/VodPoster.vue'
import { buildVodCatalogQuery } from '@/utils/vodRouteState'

const props = defineProps<{
  sourceConfigId: string | null
  siteKey: string | null
  items: VodBrowseItem[]
  loading: boolean
}>()

const railRef = ref<HTMLElement | null>(null)
const canScrollLeft = ref(false)
const canScrollRight = ref(false)

let autoplayTimer: number | undefined

function detailLocation(item: VodBrowseItem) {
  if (!props.sourceConfigId || item.vod_id === null || item.vod_id === undefined) {
    return '/vod'
  }

  return {
    name: 'vod-detail',
    params: {
      sourceConfigId: props.sourceConfigId,
      vodId: String(item.vod_id),
    },
    query: buildVodCatalogQuery({
      sourceId: props.sourceConfigId,
      siteKey: props.siteKey,
    }),
  }
}

function clearAutoplayTimer() {
  window.clearInterval(autoplayTimer)
  autoplayTimer = undefined
}

function updateScrollState() {
  const rail = railRef.value
  if (!rail) return

  const maxScroll = rail.scrollWidth - rail.clientWidth
  canScrollLeft.value = rail.scrollLeft > 2
  canScrollRight.value = rail.scrollLeft < maxScroll - 2
}

function scrollByPoster(direction: -1 | 1) {
  const rail = railRef.value
  if (!rail) return

  const firstCard = rail.querySelector<HTMLElement>('[data-hero-card]')
  const cardWidth = firstCard?.getBoundingClientRect().width ?? 180
  rail.scrollBy({
    left: direction * (cardWidth + 16) * 2,
    behavior: 'smooth',
  })
}

function startAutoplay() {
  clearAutoplayTimer()
  if (props.items.length <= 1) return

  autoplayTimer = window.setInterval(() => {
    const rail = railRef.value
    if (!rail) return

    const maxScroll = rail.scrollWidth - rail.clientWidth
    if (rail.scrollLeft >= maxScroll - 4) {
      rail.scrollTo({ left: 0, behavior: 'smooth' })
      return
    }
    scrollByPoster(1)
  }, 3600)
}

onMounted(async () => {
  await nextTick()
  updateScrollState()
  window.addEventListener('resize', updateScrollState)
  startAutoplay()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', updateScrollState)
  clearAutoplayTimer()
})

watch(
  () => props.items.length,
  async () => {
    await nextTick()
    updateScrollState()
    startAutoplay()
  },
)
</script>

<template>
  <section class="glass-panel overflow-hidden rounded-[2.5rem] border border-white/10 p-4 shadow-[0_24px_80px_rgba(0,0,0,0.28)] sm:p-5">
    <div class="mb-4 flex items-center justify-end gap-2">
      <button
        type="button"
        class="tv-focus-card flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/6 text-white transition disabled:pointer-events-none disabled:opacity-30"
        :disabled="!canScrollLeft"
        aria-label="Scroll posters left"
        @click="scrollByPoster(-1)"
      >
        <ChevronLeft class="h-5 w-5" />
      </button>
      <button
        type="button"
        class="tv-focus-card flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/6 text-white transition disabled:pointer-events-none disabled:opacity-30"
        :disabled="!canScrollRight"
        aria-label="Scroll posters right"
        @click="scrollByPoster(1)"
      >
        <ChevronRight class="h-5 w-5" />
      </button>
    </div>

    <div v-if="loading" class="hero-scroll flex gap-4 overflow-x-auto pb-2">
      <div
        v-for="index in 6"
        :key="index"
        class="aspect-[2/3] w-[9rem] shrink-0 animate-pulse rounded-[1.35rem] bg-white/8 sm:w-[10rem] xl:w-[11rem]"
      ></div>
    </div>

    <div
      v-else-if="props.items.length > 0"
      class="relative"
    >
      <div
        class="pointer-events-none absolute inset-y-0 left-0 z-10 w-12 bg-gradient-to-r from-cinema-950/88 to-transparent transition-opacity"
        :class="canScrollLeft ? 'opacity-100' : 'opacity-0'"
      ></div>
      <div
        class="pointer-events-none absolute inset-y-0 right-0 z-10 w-12 bg-gradient-to-l from-cinema-950/88 to-transparent transition-opacity"
        :class="canScrollRight ? 'opacity-100' : 'opacity-0'"
      ></div>
      <div
        ref="railRef"
        class="hero-scroll flex gap-4 overflow-x-auto pb-2 [scrollbar-width:none]"
        @scroll="updateScrollState"
      >
        <RouterLink
          v-for="item in props.items"
          :key="`${item.vod_id}-${item.name}`"
          :to="detailLocation(item)"
          data-hero-card
          class="group block w-[9rem] shrink-0 overflow-hidden rounded-[1.35rem] sm:w-[10rem] xl:w-[11rem]"
        >
          <VodPoster
            :src="item.poster"
            :alt="item.name"
            :class="'rounded-[1.35rem]'"
            aspect-class="aspect-[2/3]"
            image-class="h-full w-full object-cover transition duration-500 group-hover:scale-[1.03]"
          />
        </RouterLink>
      </div>
    </div>

    <div v-else class="flex min-h-[16rem] items-center justify-center rounded-[1.5rem] border border-dashed border-white/10 bg-black/22 px-6 text-center text-sm text-white/54">
      Latest posters will appear here after the current VOD site returns catalog items.
    </div>
  </section>
</template>

<style scoped>
.hero-scroll::-webkit-scrollbar {
  display: none;
}

.hero-scroll {
  scroll-behavior: smooth;
  -webkit-overflow-scrolling: touch;
}
</style>
