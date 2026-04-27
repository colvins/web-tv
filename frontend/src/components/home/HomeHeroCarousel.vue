<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import type { VodBrowseItem } from '@/api/sourceConfigs'
import VodPoster from '@/components/vod/VodPoster.vue'
import { buildVodCatalogQuery } from '@/utils/vodRouteState'

const props = defineProps<{
  sourceConfigId: string | null
  siteKey: string | null
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
    <div class="relative min-h-[24rem] p-4 sm:p-6 xl:min-h-[28rem]">
      <div ref="gridRef" class="relative z-10 h-full overflow-hidden rounded-[2rem] border border-white/10 bg-black/18 p-3 backdrop-blur-xl">
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
