<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import type { VodBrowseCategory } from '@/api/sourceConfigs'

const props = defineProps<{
  categories: VodBrowseCategory[]
  selectedCategoryId: string | null
}>()

const emit = defineEmits<{
  select: [categoryId: string | null]
}>()

const activeParentId = ref<string | null>(null)

const normalizedCategories = computed(() =>
  props.categories.map((category) => ({
    ...category,
    id: category.type_id === null || category.type_id === undefined ? null : String(category.type_id),
    parentId:
      category.parent_type_id === null || category.parent_type_id === undefined
        ? null
        : String(category.parent_type_id),
  })),
)

const hasParentStructure = computed(() =>
  normalizedCategories.value.some((category) => category.parentId && category.parentId !== category.id),
)

const parentCategories = computed(() => {
  if (!hasParentStructure.value) return []
  return normalizedCategories.value.filter((category) => !category.parentId || category.parentId === category.id)
})

const childCategories = computed(() => {
  if (!hasParentStructure.value || !activeParentId.value) return []
  return normalizedCategories.value.filter((category) => category.parentId === activeParentId.value && category.id !== activeParentId.value)
})

watch(
  () => [props.categories, props.selectedCategoryId] as const,
  () => {
    if (!hasParentStructure.value) {
      activeParentId.value = null
      return
    }

    const selected = normalizedCategories.value.find((category) => category.id === props.selectedCategoryId)
    if (selected?.parentId) {
      activeParentId.value = selected.parentId
      return
    }
    if (selected?.id) {
      activeParentId.value = selected.id
      return
    }
    activeParentId.value = parentCategories.value[0]?.id ?? null
  },
  { immediate: true, deep: true },
)

function parentButtonClass(parentId: string | null) {
  return activeParentId.value === parentId
    ? 'border-white/30 bg-white/14 text-white'
    : 'border-white/10 bg-white/6 text-white/62 hover:bg-white/10'
}

function childButtonClass(categoryId: string | null) {
  return props.selectedCategoryId === categoryId
    ? 'border-white/30 bg-white/14 text-white'
    : 'border-white/10 bg-white/6 text-white/62 hover:bg-white/10'
}

function selectParent(parentId: string | null) {
  activeParentId.value = parentId
}
</script>

<template>
  <div class="mt-6 grid gap-5">
    <div class="flex flex-wrap gap-3">
      <button
        type="button"
        class="rounded-full border px-4 py-2 text-sm transition"
        :class="childButtonClass(null)"
        @click="emit('select', null)"
      >
        All
      </button>
      <template v-if="!hasParentStructure">
        <button
          v-for="category in normalizedCategories"
          :key="`${category.id}-${category.type_name}`"
          type="button"
          class="rounded-full border px-4 py-2 text-sm transition"
          :class="childButtonClass(category.id)"
          @click="emit('select', category.id)"
        >
          {{ category.type_name ?? `Type ${category.type_id}` }}
        </button>
      </template>
    </div>

    <template v-if="hasParentStructure">
      <div class="grid gap-3">
        <p class="text-xs uppercase tracking-[0.18em] text-white/40">Browse</p>
        <div class="flex flex-wrap gap-3">
          <button
            v-for="parent in parentCategories"
            :key="`${parent.id}-${parent.type_name}`"
            type="button"
            class="rounded-full border px-4 py-2 text-sm transition"
            :class="parentButtonClass(parent.id)"
            @click="selectParent(parent.id)"
          >
            {{ parent.type_name ?? `Type ${parent.type_id}` }}
          </button>
        </div>
      </div>

      <div v-if="childCategories.length" class="grid gap-3">
        <p class="text-xs uppercase tracking-[0.18em] text-white/40">Categories</p>
        <div class="flex flex-wrap gap-3">
          <button
            v-for="category in childCategories"
            :key="`${category.id}-${category.type_name}`"
            type="button"
            class="rounded-full border px-4 py-2 text-sm transition"
            :class="childButtonClass(category.id)"
            @click="emit('select', category.id)"
          >
            {{ category.type_name ?? `Type ${category.type_id}` }}
          </button>
        </div>
      </div>
    </template>
  </div>
</template>
