<script setup lang="ts">
import type { VodBrowseItem } from '@/api/sourceConfigs'
import VodPoster from './VodPoster.vue'

defineProps<{
  items: VodBrowseItem[]
  loading: boolean
}>()

const emit = defineEmits<{
  selectItem: [item: VodBrowseItem]
}>()
</script>

<template>
  <div v-if="loading" class="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
    <div v-for="index in 8" :key="index" class="glass-panel min-h-80 animate-pulse rounded-[2rem] p-5">
      <div class="aspect-[3/4] rounded-[1.5rem] bg-white/8"></div>
      <div class="mt-5 h-5 w-2/3 rounded-full bg-white/10"></div>
      <div class="mt-3 h-3 w-1/3 rounded-full bg-white/8"></div>
    </div>
  </div>

  <div v-else class="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
    <article
      v-for="item in items"
      :key="`${item.vod_id}-${item.name}`"
      class="tv-focus-card glass-panel overflow-hidden rounded-[2rem] p-4"
    >
      <button type="button" class="block w-full text-left" @click="emit('selectItem', item)">
        <div class="relative rounded-[1.5rem]">
          <VodPoster
            :src="item.poster"
            :alt="item.name"
            class="rounded-[1.5rem]"
            image-class="aspect-[3/4] w-full object-cover"
          />
          <div
            v-if="item.remarks"
            class="absolute left-3 top-3 rounded-full border border-black/10 bg-black/55 px-3 py-1 text-xs text-white"
          >
            {{ item.remarks }}
          </div>
        </div>

        <div class="mt-5">
          <h3 class="line-clamp-2 text-lg font-semibold text-white">{{ item.name }}</h3>
          <p class="mt-2 text-sm text-white/54">{{ item.category_name ?? 'Uncategorized' }}</p>
          <div class="mt-4 flex flex-wrap gap-2 text-xs text-white/60">
            <span v-if="item.year" class="rounded-full border border-white/10 bg-white/6 px-3 py-1">{{ item.year }}</span>
            <span v-if="item.area" class="rounded-full border border-white/10 bg-white/6 px-3 py-1">{{ item.area }}</span>
            <span
              v-if="item.vod_id !== null && item.vod_id !== undefined"
              class="rounded-full border border-white/10 bg-white/6 px-3 py-1"
            >
              ID {{ item.vod_id }}
            </span>
          </div>
        </div>
      </button>
    </article>
  </div>
</template>
