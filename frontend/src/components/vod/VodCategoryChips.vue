<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import type { VodBrowseCategory } from '@/api/sourceConfigs'

const props = defineProps<{
  categories: VodBrowseCategory[]
  selectedCategoryId: string | null
  compact?: boolean
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
      category.parent_type_id === null || category.parent_type_id === undefined || String(category.parent_type_id) === '0'
        ? null
        : String(category.parent_type_id),
  })),
)

const categoriesById = computed(() => {
  const entries = normalizedCategories.value
    .filter((category): category is (typeof normalizedCategories.value)[number] & { id: string } => Boolean(category.id))
    .map((category) => [category.id, category] as const)
  return new Map(entries)
})

const childrenByParentId = computed(() => {
  const mapping = new Map<string, typeof normalizedCategories.value>()
  for (const category of normalizedCategories.value) {
    if (!category.parentId || category.parentId === category.id) continue
    const existing = mapping.get(category.parentId) ?? []
    existing.push(category)
    mapping.set(category.parentId, existing)
  }
  return mapping
})

const hasChildren = (categoryId: string | null) => Boolean(categoryId && childrenByParentId.value.get(categoryId)?.length)

const rootCategories = computed(() =>
  normalizedCategories.value.filter((category) => !category.parentId || !categoriesById.value.has(category.parentId)),
)

const groupedRootCategories = computed(() => rootCategories.value.filter((category) => hasChildren(category.id)))
const rootLeafCategories = computed(() => rootCategories.value.filter((category) => !hasChildren(category.id)))
const displayedRootCategories = computed(() => [...groupedRootCategories.value, ...rootLeafCategories.value])

const hasParentStructure = computed(() => groupedRootCategories.value.length > 0)

function leafDescendants(parentId: string | null) {
  if (!parentId) return []

  const leaves: typeof normalizedCategories.value = []
  const stack = [...(childrenByParentId.value.get(parentId) ?? [])]

  while (stack.length) {
    const category = stack.shift()
    if (!category) continue
    if (hasChildren(category.id)) {
      stack.push(...(childrenByParentId.value.get(category.id ?? '') ?? []))
      continue
    }
    leaves.push(category)
  }

  return leaves
}

const childCategories = computed(() => {
  if (!hasParentStructure.value || !activeParentId.value) return []
  return leafDescendants(activeParentId.value)
})

watch(
  () => [props.categories, props.selectedCategoryId] as const,
  () => {
    if (!hasParentStructure.value) {
      activeParentId.value = null
      return
    }

    const selected = normalizedCategories.value.find((category) => category.id === props.selectedCategoryId)
    if (selected?.id && hasChildren(selected.id)) {
      activeParentId.value = selected.id
      return
    }
    if (selected?.parentId) {
      let currentParentId: string | null = selected.parentId
      while (currentParentId) {
        const parentCategory = categoriesById.value.get(currentParentId)
        if (!parentCategory) break
        if (hasChildren(parentCategory.id)) {
          activeParentId.value = parentCategory.id
          return
        }
        currentParentId = parentCategory.parentId
      }
      return
    }
    if (props.selectedCategoryId === null) {
      activeParentId.value = null
    }
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

function selectAll() {
  activeParentId.value = null
  emit('select', null)
}

function selectRootLeaf(categoryId: string | null) {
  activeParentId.value = null
  emit('select', categoryId)
}
</script>

<template>
  <div class="grid" :class="compact ? 'gap-4' : 'mt-6 gap-5'">
    <div class="flex flex-wrap gap-3">
      <button
        type="button"
        class="rounded-full border transition"
        :class="[compact ? 'px-3.5 py-2 text-xs' : 'px-4 py-2 text-sm', childButtonClass(null)]"
        @click="selectAll()"
      >
        All
      </button>
    </div>

    <template v-if="hasParentStructure">
      <div class="grid gap-3">
        <p class="text-xs uppercase tracking-[0.18em] text-white/40">Browse</p>
        <div class="flex flex-wrap" :class="compact ? 'gap-2' : 'gap-3'">
          <button
            v-for="category in displayedRootCategories"
            :key="`${category.id}-${category.type_name}`"
            type="button"
            class="rounded-full border transition"
            :class="[
              compact ? 'px-3.5 py-2 text-xs' : 'px-4 py-2 text-sm',
              hasChildren(category.id) ? parentButtonClass(category.id) : childButtonClass(category.id),
            ]"
            @click="hasChildren(category.id) ? selectParent(category.id) : selectRootLeaf(category.id)"
          >
            {{ category.type_name ?? `Type ${category.type_id}` }}
          </button>
        </div>
      </div>

      <div v-if="childCategories.length" class="grid gap-3">
        <p class="text-xs uppercase tracking-[0.18em] text-white/40">Categories</p>
        <div class="flex flex-wrap" :class="compact ? 'gap-2' : 'gap-3'">
          <button
            v-for="category in childCategories"
            :key="`${category.id}-${category.type_name}`"
            type="button"
            class="rounded-full border transition"
            :class="[compact ? 'px-3.5 py-2 text-xs' : 'px-4 py-2 text-sm', childButtonClass(category.id)]"
            @click="emit('select', category.id)"
          >
            {{ category.type_name ?? `Type ${category.type_id}` }}
          </button>
        </div>
      </div>
    </template>

    <div v-else class="grid gap-3">
      <p class="text-xs uppercase tracking-[0.18em] text-white/40">Browse</p>
      <div class="flex flex-wrap" :class="compact ? 'gap-2' : 'gap-3'">
        <button
          v-for="category in normalizedCategories"
          :key="`${category.id}-${category.type_name}`"
          type="button"
          class="rounded-full border transition"
          :class="[compact ? 'px-3.5 py-2 text-xs' : 'px-4 py-2 text-sm', childButtonClass(category.id)]"
          @click="emit('select', category.id)"
        >
          {{ category.type_name ?? `Type ${category.type_id}` }}
        </button>
      </div>
    </div>
  </div>
</template>
