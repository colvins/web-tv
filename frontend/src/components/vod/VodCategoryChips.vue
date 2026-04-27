<script setup lang="ts">
import type { VodBrowseCategory } from '@/api/sourceConfigs'

defineProps<{
  categories: VodBrowseCategory[]
  selectedCategoryId: string | null
}>()

const emit = defineEmits<{
  select: [categoryId: string | null]
}>()
</script>

<template>
  <div class="mt-6 flex flex-wrap gap-3">
    <button
      type="button"
      class="rounded-full border px-4 py-2 text-sm transition"
      :class="selectedCategoryId === null ? 'border-white/30 bg-white/14 text-white' : 'border-white/10 bg-white/6 text-white/62 hover:bg-white/10'"
      @click="emit('select', null)"
    >
      All
    </button>
    <button
      v-for="category in categories"
      :key="`${category.type_id}-${category.type_name}`"
      type="button"
      class="rounded-full border px-4 py-2 text-sm transition"
      :class="
        selectedCategoryId === String(category.type_id)
          ? 'border-white/30 bg-white/14 text-white'
          : 'border-white/10 bg-white/6 text-white/62 hover:bg-white/10'
      "
      @click="emit('select', category.type_id === null ? null : String(category.type_id))"
    >
      {{ category.type_name ?? `Type ${category.type_id}` }}
    </button>
  </div>
</template>
