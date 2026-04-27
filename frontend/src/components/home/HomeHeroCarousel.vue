<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ChevronRight, Settings } from 'lucide-vue-next'

import type { VodBrowseItem } from '@/api/sourceConfigs'
import VodPoster from '@/components/vod/VodPoster.vue'
import { buildVodCatalogQuery } from '@/utils/vodRouteState'

const props = defineProps<{
  sourceConfigId: string | null
  siteKey: string | null
  sourceName: string | null
  siteName: string | null
  items: VodBrowseItem[]
  loading: boolean
}>()

const gridRef = ref<HTMLElement | null>(null)
const itemsPerSlide = ref(4)
const activeSlide = ref(0)

let resizeObserver: ResizeObserver | undefined
let autoplayTimer: number | undefined

const slides = computed(() => {
  const chunkSize = Math.max(1, itemsPerSlide.value)
  const nextSlides: VodBrowseItem[][] = []

  for (let index = 0; index < props.items.length; index += chunkSize) {
    nextSlides.push(props.items.slice(index, index + chunkSize))
  }

  return nextSlides
})

const hasSlides = computed(() => slides.value.length > 0)

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

function updateItemsPerSlide() {
  const width = gridRef.value?.clientWidth ?? window.innerWidth

  if (width >= 1400) {
    itemsPerSlide.value = 6
    return
  }
  if (width >= 1100) {
    itemsPerSlide.value = 5
    return
  }
  if (width >= 860) {
    itemsPerSlide.value = 4
    return
  }
  if (width >= 620) {
    itemsPerSlide.value = 3
    return
  }
  itemsPerSlide.value = 2
}

function clearAutoplayTimer() {
  window.clearInterval(autoplayTimer)
  autoplayTimer = undefined
}

function startAutoplay() {
  clearAutoplayTimer()
  if (slides.value.length <= 1) return

  autoplayTimer = window.setInterval(() => {
    activeSlide.value = (activeSlide.value + 1) % slides.value.length
  }, 3600)
}

onMounted(() => {
  updateItemsPerSlide()
  if (typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => updateItemsPerSlide())
    if (gridRef.value) {
      resizeObserver.observe(gridRef.value)
    }
  } else {
    window.addEventListener('resize', updateItemsPerSlide)
  }
  startAutoplay()
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  window.removeEventListener('resize', updateItemsPerSlide)
  clearAutoplayTimer()
})

watch(
  () => slides.value.length,
  (length) => {
    if (activeSlide.value >= length) {
      activeSlide.value = 0
    }
    startAutoplay()
  },
)
</script>

<template>
  <section class="relative overflow-hidden rounded-[2.5rem] border border-white/10 bg-[radial-gradient(circle_at_top_left,rgba(225,90,65,0.24),transparent_36%),radial-gradient(circle_at_bottom_right,rgba(67,116,255,0.22),transparent_34%),linear-gradient(135deg,rgba(7,9,16,0.96),rgba(15,18,28,0.88))] shadow-[0_32px_100px_rgba(0,0,0,0.34)]">
    <div class="absolute inset-0 bg-[linear-gradient(90deg,rgba(3,5,10,0.92)_0%,rgba(3,5,10,0.76)_34%,rgba(3,5,10,0.34)_62%,rgba(3,5,10,0.7)_100%)]"></div>
    <div class="relative grid min-h-[24rem] gap-8 p-6 sm:p-8 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.15fr)] lg:items-end lg:p-10 xl:min-h-[28rem]">
      <div class="relative z-10 flex flex-col justify-end">
        <p class="text-sm uppercase tracking-[0.28em] text-white/46">Watch Now</p>
        <h2 class="mt-3 max-w-xl text-4xl font-semibold text-white sm:text-5xl xl:text-6xl">
          {{ sourceName ?? 'Choose a VOD source to fill the home screen.' }}
        </h2>
        <p class="mt-4 max-w-xl text-sm leading-7 text-white/68 sm:text-base">
          {{
            sourceName
              ? `Latest posters from ${siteName ?? sourceName} rotate here automatically.`
              : 'Set a current VOD site in Settings to surface the newest movie and series posters here.'
          }}
        </p>
        <div class="mt-6 flex flex-wrap gap-3">
          <RouterLink
            v-if="sourceName"
            to="/vod"
            class="tv-focus-card inline-flex min-h-12 items-center rounded-full bg-white px-5 py-3 text-sm font-semibold text-cinema-950 transition hover:bg-white/92"
          >
            Open VOD
            <ChevronRight class="ml-2 h-4 w-4" />
          </RouterLink>
          <RouterLink
            v-else
            to="/settings/sources"
            class="tv-focus-card inline-flex min-h-12 items-center rounded-full border border-white/14 bg-white/8 px-5 py-3 text-sm font-medium text-white/86 transition hover:bg-white/12"
          >
            Configure sources
            <Settings class="ml-2 h-4 w-4" />
          </RouterLink>
        </div>
      </div>

      <div ref="gridRef" class="relative z-10 overflow-hidden rounded-[2rem] border border-white/10 bg-black/18 p-3 backdrop-blur-xl">
        <div v-if="loading" class="grid gap-3" :style="{ gridTemplateColumns: `repeat(${itemsPerSlide}, minmax(0, 1fr))` }">
          <div
            v-for="index in itemsPerSlide"
            :key="index"
            class="aspect-[2/3] animate-pulse rounded-[1.35rem] bg-white/8"
          ></div>
        </div>

        <div
          v-else-if="hasSlides"
          class="flex transition-transform duration-700 ease-out"
          :style="{ transform: `translateX(-${activeSlide * 100}%)` }"
        >
          <div
            v-for="(slide, slideIndex) in slides"
            :key="slideIndex"
            class="grid w-full shrink-0 gap-3"
            :style="{ gridTemplateColumns: `repeat(${slide.length}, minmax(0, 1fr))` }"
          >
            <RouterLink
              v-for="item in slide"
              :key="`${item.vod_id}-${item.name}`"
              :to="detailLocation(item)"
              class="group block overflow-hidden rounded-[1.35rem]"
            >
              <VodPoster
                :src="item.poster"
                :alt="item.name"
                aspect-class="aspect-[2/3]"
                image-class="h-full w-full object-cover transition duration-500 group-hover:scale-[1.03]"
              />
            </RouterLink>
          </div>
        </div>

        <div v-else class="flex min-h-[16rem] items-center justify-center rounded-[1.5rem] border border-dashed border-white/10 bg-black/22 px-6 text-center text-sm text-white/54">
          Latest posters will appear here after the current VOD site returns catalog items.
        </div>

        <div v-if="slides.length > 1" class="mt-4 flex justify-center gap-2">
          <button
            v-for="(_, index) in slides"
            :key="index"
            type="button"
            class="h-1.5 rounded-full transition-all"
            :class="activeSlide === index ? 'w-8 bg-white' : 'w-3 bg-white/24'"
            :aria-label="`Show poster slide ${index + 1}`"
            @click="activeSlide = index"
          ></button>
        </div>
      </div>
    </div>
  </section>
</template>
