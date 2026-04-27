<script setup lang="ts">
import type { VodBrowseItem } from '@/api/sourceConfigs'
import VodPoster from './VodPoster.vue'

defineProps<{
  items: VodBrowseItem[]
  loading: boolean
  mobile?: boolean
}>()

const emit = defineEmits<{
  selectItem: [item: VodBrowseItem]
}>()
</script>

<template>
  <div
    v-if="loading"
    class="grid"
    :class="mobile ? 'grid-cols-2 gap-3 pb-[calc(7rem+env(safe-area-inset-bottom))]' : 'gap-5 sm:grid-cols-2 xl:grid-cols-4'"
  >
    <div
      v-for="index in 8"
      :key="index"
      class="glass-panel animate-pulse"
      :class="mobile ? 'min-h-56 rounded-[1.5rem] p-3' : 'min-h-80 rounded-[2rem] p-5'"
    >
      <div :class="mobile ? 'aspect-[3/4] rounded-[1.1rem] bg-white/8' : 'aspect-[3/4] rounded-[1.5rem] bg-white/8'"></div>
      <div class="mt-4 h-4 w-2/3 rounded-full bg-white/10"></div>
      <div class="mt-2 h-3 w-1/3 rounded-full bg-white/8"></div>
    </div>
  </div>

  <div
    v-else
    class="grid"
    :class="mobile ? 'grid-cols-2 gap-3 pb-[calc(7rem+env(safe-area-inset-bottom))]' : 'gap-5 sm:grid-cols-2 xl:grid-cols-4'"
  >
    <article
      v-for="item in items"
      :key="`${item.vod_id}-${item.name}`"
      class="tv-focus-card glass-panel overflow-hidden"
      :class="mobile ? 'rounded-[1.5rem] p-3' : 'rounded-[2rem] p-4'"
    >
      <button type="button" class="block w-full text-left" @click="emit('selectItem', item)">
        <div class="relative" :class="mobile ? 'rounded-[1.1rem]' : 'rounded-[1.5rem]'">
          <VodPoster
            :src="item.poster"
            :alt="item.name"
            :class="mobile ? 'rounded-[1.1rem]' : 'rounded-[1.5rem]'"
            image-class="aspect-[3/4] w-full object-cover"
          />
          <div
            v-if="item.remarks"
            class="absolute left-2 top-2 rounded-full border border-black/10 bg-black/55 px-2.5 py-1 text-[11px] text-white"
          >
            {{ item.remarks }}
          </div>
        </div>

        <div :class="mobile ? 'mt-3' : 'mt-5'">
          <h3 class="line-clamp-2 font-semibold text-white" :class="mobile ? 'text-sm leading-5' : 'text-lg'">{{ item.name }}</h3>
          <p class="mt-2 text-white/54" :class="mobile ? 'line-clamp-1 text-xs' : 'text-sm'">{{ item.category_name ?? '未分类' }}</p>
          <div class="mt-3 flex flex-wrap gap-2 text-xs text-white/60" :class="mobile ? 'mt-2' : 'mt-4'">
            <span v-if="item.year" class="rounded-full border border-white/10 bg-white/6 px-2.5 py-1">{{ item.year }}</span>
            <span v-if="item.area && !mobile" class="rounded-full border border-white/10 bg-white/6 px-3 py-1">{{ item.area }}</span>
            <span
              v-if="item.vod_id !== null && item.vod_id !== undefined && !mobile"
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
