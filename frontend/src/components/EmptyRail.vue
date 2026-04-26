<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'

defineProps<{
  title: string
  description: string
  count?: number
}>()

const railRef = ref<HTMLElement | null>(null)
const canScrollLeft = ref(false)
const canScrollRight = ref(false)
const isDragging = ref(false)

let dragStartX = 0
let dragStartScrollLeft = 0

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
  const cardWidth = firstCard?.getBoundingClientRect().width ?? rail.clientWidth * 0.75
  rail.scrollBy({
    left: direction * (cardWidth + 20),
    behavior: 'smooth',
  })
}

function onPointerDown(event: PointerEvent) {
  if (event.pointerType !== 'mouse' || event.button !== 0 || !railRef.value) return

  isDragging.value = true
  dragStartX = event.clientX
  dragStartScrollLeft = railRef.value.scrollLeft
  railRef.value.setPointerCapture(event.pointerId)
}

function onPointerMove(event: PointerEvent) {
  if (!isDragging.value || !railRef.value) return

  event.preventDefault()
  railRef.value.scrollLeft = dragStartScrollLeft - (event.clientX - dragStartX)
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
</script>

<template>
  <section class="mb-10">
    <div class="mb-4 flex items-end justify-between gap-4">
      <h2 class="text-2xl font-semibold text-white">{{ title }}</h2>
      <div class="flex gap-2" aria-label="Rail scroll controls">
        <button
          type="button"
          class="tv-focus-card glass-panel flex h-10 w-10 items-center justify-center rounded-full text-white transition-opacity disabled:pointer-events-none disabled:opacity-30"
          :disabled="!canScrollLeft"
          :aria-label="`Scroll ${title} left`"
          @click="scrollByCard(-1)"
        >
          <ChevronLeft class="h-5 w-5" aria-hidden="true" />
        </button>
        <button
          type="button"
          class="tv-focus-card glass-panel flex h-10 w-10 items-center justify-center rounded-full text-white transition-opacity disabled:pointer-events-none disabled:opacity-30"
          :disabled="!canScrollRight"
          :aria-label="`Scroll ${title} right`"
          @click="scrollByCard(1)"
        >
          <ChevronRight class="h-5 w-5" aria-hidden="true" />
        </button>
      </div>
    </div>
    <div class="relative">
      <div
        class="pointer-events-none absolute inset-y-0 left-0 z-10 w-12 bg-gradient-to-r from-cinema-950/90 to-transparent transition-opacity"
        :class="canScrollLeft ? 'opacity-100' : 'opacity-0'"
        aria-hidden="true"
      ></div>
      <div
        class="pointer-events-none absolute inset-y-0 right-0 z-10 w-12 bg-gradient-to-l from-cinema-950/90 to-transparent transition-opacity"
        :class="canScrollRight ? 'opacity-100' : 'opacity-0'"
        aria-hidden="true"
      ></div>
      <div
        ref="railRef"
        class="rail-scroll flex gap-5 overflow-x-auto pb-5 [scrollbar-width:none]"
        :class="isDragging ? 'cursor-grabbing select-none' : 'cursor-grab'"
        @scroll="updateScrollState"
        @pointerdown="onPointerDown"
        @pointermove="onPointerMove"
        @pointerup="stopDragging"
        @pointercancel="stopDragging"
        @pointerleave="stopDragging"
      >
        <article
          v-for="index in count ?? 5"
          :key="index"
          data-rail-card
          tabindex="0"
          class="tv-focus-card glass-panel flex aspect-[16/9] min-w-[16rem] max-w-[28rem] flex-1 items-end rounded-[2rem] p-5 sm:min-w-[22rem]"
        >
          <div>
            <div class="mb-3 h-2 w-20 rounded-full bg-white/14"></div>
            <p class="max-w-72 text-sm leading-6 text-white/54">{{ description }}</p>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>

<style scoped>
.rail-scroll::-webkit-scrollbar {
  display: none;
}

.rail-scroll {
  scroll-behavior: smooth;
  -webkit-overflow-scrolling: touch;
  touch-action: pan-x;
}
</style>
