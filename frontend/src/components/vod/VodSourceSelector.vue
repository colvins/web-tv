<script setup lang="ts">
import { RefreshCw, Search } from 'lucide-vue-next'
import { NButton, NInput } from 'naive-ui'

withDefaults(defineProps<{
  searchQuery: string
  loading: boolean
  sourceLoading: boolean
  searchLoading: boolean
  compact?: boolean
}>(), {
  compact: false,
})

const emit = defineEmits<{
  refresh: []
  'update:searchQuery': [value: string]
  search: []
}>()
</script>

<template>
  <div class="flex gap-3" :class="compact ? 'flex-col' : 'justify-end'">
    <div class="flex min-w-0 gap-3" :class="compact ? 'flex-col' : 'items-center'">
      <NInput
        :value="searchQuery"
        round
        class="min-w-0"
        :class="compact ? 'w-full' : 'w-[11rem] xl:w-[12rem]'"
        placeholder="Search titles"
        clearable
        @update:value="(value) => emit('update:searchQuery', value)"
        @keyup.enter="emit('search')"
      />
      <NButton round type="primary" :loading="searchLoading" @click="emit('search')">
        <template #icon><Search class="h-4 w-4" /></template>
        Search
      </NButton>
    </div>

    <div class="flex items-center gap-2" :class="compact ? 'justify-end' : 'justify-end'">
      <NButton quaternary circle :loading="loading || sourceLoading" @click="emit('refresh')">
        <template #icon><RefreshCw class="h-4 w-4" /></template>
      </NButton>
    </div>
  </div>
</template>

<style scoped>
:deep(.n-input) {
  --n-height: 44px;
}

:deep(.n-input__input-el) {
  font-size: 0.95rem;
}
</style>
