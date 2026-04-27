<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'

import type { RecentVodPlaybackItem } from '@/stores/app'
import VodPoster from '@/components/vod/VodPoster.vue'
import { buildVodCatalogQuery } from '@/utils/vodRouteState'

const props = defineProps<{
  items: RecentVodPlaybackItem[]
}>()

const railRef = ref<HTMLElement | null>(null)
const canScrollLeft = ref(false)
const canScrollRight = ref(false)
const isDragging = ref(false)
const dragStartX = ref(0)
const dragStartScrollLeft = ref(0)

const sortedItems = computed(() =>
  [...props.items].sort((left, right) => new Date(right.watchedAt).getTime() - new Date(left.watchedAt).getTime()),
)

function detailLocation(item: RecentVodPlaybackItem) {
  return {
    name: 'vod-detail',
    params: {
      sourceConfigId: item.sourceConfigId,
      vodId: item.vodId,
    },
    query: buildVodCatalogQuery({
      sourceId: item.sourceConfigId,
      siteKey: item.siteKey,
    }),
  }
}

function updateScrollState() {
  const rail = railRef.value
  if (!rail) return

  const maxScroll = rail.scrollWidth - rail.clientWidth
  canScrollLeft.value = rail.scrollLeft > 2
  canScrollRight.value = rail.scrollLeft < maxScroll - 2
}

function scrollByCard(direction: -1 | 1) {
  const rail = railRef.value
  if (!rail) return

  const firstCard = rail.querySelector<HTMLElement>('[data-rail-card]')
  const cardWidth = firstCard?.getBoundingClientRect().width ?? 280
  rail.scrollBy({
    left: direction * (cardWidth + 20),
    behavior: 'smooth',
  })
}

function onPointerDown(event: PointerEvent) {
  if (event.pointerType !== 'mouse' || event.button !== 0 || !railRef.value) return

  isDragging.value = true
  dragStartX.value = event.clientX
  dragStartScrollLeft.value = railRef.value.scrollLeft
  railRef.value.setPointerCapture(event.pointerId)
}

function onPointerMove(event: PointerEvent) {
  if (!isDragging.value || !railRef.value) return

  event.preventDefault()
  railRef.value.scrollLeft = dragStartScrollLeft.value - (event.clientX - dragStartX.value)
}

function stopDragging(event: PointerEvent) {
  if (!railRef.value || !isDragging.value) return

  isDragging.value = false
  if (railRef.value.hasPointerCapture(event.pointerId)) {
    railRef.value.releasePointerCapture(event.pointerId)
  }
}

onMounted(async () => {
  await nextTick()
  updateScrollState()
  window.addEventListener('resize', updateScrollState)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', updateScrollState)
})

watch(
  () => props.items.length,
  async () => {
    await nextTick()
    updateScrollState()
  },
)
</script>

<template>
  <section class="mt-10">
    <div class="mb-4 flex items-end justify-between gap-4">
      <div>
        <p class="text-sm uppercase tracking-[0.28em] text-white/42">Library</p>
        <h2 class="mt-2 text-2xl font-semibold text-white">Continue Watching</h2>
      </div>
      <div class="flex gap-2" aria-label="Continue watching scroll controls">
        <button
          type="button"
          class="tv-focus-card glass-panel flex h-10 w-10 items-center justify-center rounded-full text-white transition-opacity disabled:pointer-events-none disabled:opacity-30"
          :disabled="!canScrollLeft"
          aria-label="Scroll continue watching left"
          @click="scrollByCard(-1)"
        >
          <ChevronLeft class="h-5 w-5" />
        </button>
        <button
          type="button"
          class="tv-focus-card glass-panel flex h-10 w-10 items-center justify-center rounded-full text-white transition-opacity disabled:pointer-events-none disabled:opacity-30"
          :disabled="!canScrollRight"
          aria-label="Scroll continue watching right"
          @click="scrollByCard(1)"
        >
          <ChevronRight class="h-5 w-5" />
        </button>
      </div>
    </div>

    <div v-if="sortedItems.length === 0" class="glass-panel rounded-[2rem] border border-white/10 p-6 text-white/56 sm:p-8">
      Recent VOD plays will appear here after you start an episode.
    </div>

    <div v-else class="relative">
      <div
        class="pointer-events-none absolute inset-y-0 left-0 z-10 w-12 bg-gradient-to-r from-cinema-950/90 to-transparent transition-opacity"
        :class="canScrollLeft ? 'opacity-100' : 'opacity-0'"
      ></div>
      <div
        class="pointer-events-none absolute inset-y-0 right-0 z-10 w-12 bg-gradient-to-l from-cinema-950/90 to-transparent transition-opacity"
        :class="canScrollRight ? 'opacity-100' : 'opacity-0'"
      ></div>
      <div
        ref="railRef"
        class="continue-scroll flex gap-5 overflow-x-auto pb-5 [scrollbar-width:none]"
        :class="isDragging ? 'cursor-grabbing select-none' : 'cursor-grab'"
        @scroll="updateScrollState"
        @pointerdown="onPointerDown"
        @pointermove="onPointerMove"
        @pointerup="stopDragging"
        @pointercancel="stopDragging"
        @pointerleave="stopDragging"
      >
        <RouterLink
          v-for="item in sortedItems"
          :key="`${item.sourceConfigId}-${item.vodId}`"
          :to="detailLocation(item)"
          data-rail-card
          class="tv-focus-card glass-panel block min-w-[12rem] overflow-hidden rounded-[1.75rem] border border-white/10 p-3 sm:min-w-[14rem] sm:max-w-[16rem]"
        >
          <VodPoster
            :src="item.poster"
            :alt="item.name"
            :class="'rounded-[1.2rem]'"
            aspect-class="aspect-[2/3]"
            image-class="h-full w-full object-cover"
          />
          <div class="mt-4">
            <h3 class="line-clamp-2 text-sm font-semibold text-white sm:text-base">{{ item.name }}</h3>
            <p class="mt-2 line-clamp-1 text-xs text-white/54">{{ item.episodeName }}</p>
            <div class="mt-3 flex flex-wrap gap-2 text-[11px] text-white/54">
              <span v-if="item.remarks" class="rounded-full border border-white/10 bg-white/6 px-2.5 py-1">{{ item.remarks }}</span>
              <span v-if="item.year" class="rounded-full border border-white/10 bg-white/6 px-2.5 py-1">{{ item.year }}</span>
            </div>
          </div>
        </RouterLink>
      </div>
    </div>
  </section>
</template>

<style scoped>
.continue-scroll::-webkit-scrollbar {
  display: none;
}

.continue-scroll {
  scroll-behavior: smooth;
  -webkit-overflow-scrolling: touch;
  touch-action: pan-x;
}
</style>
