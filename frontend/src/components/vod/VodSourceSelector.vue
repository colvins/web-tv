<script setup lang="ts">
import { Search } from 'lucide-vue-next'
import { NButton, NInput } from 'naive-ui'

withDefaults(defineProps<{
  searchQuery: string
  searchLoading: boolean
  compact?: boolean
}>(), {
  compact: false,
})

const emit = defineEmits<{
  'update:searchQuery': [value: string]
  search: []
}>()
</script>

<template>
  <div class="flex w-full justify-end sm:w-auto">
    <div class="flex min-w-0 items-center" :class="compact ? 'gap-2' : 'gap-3'">
      <NInput
        :value="searchQuery"
        round
        class="min-w-0"
        :class="compact ? 'vod-search-input-compact w-[4.5rem] shrink-0' : 'w-[11rem] xl:w-[12rem]'"
        placeholder="Search titles"
        clearable
        @update:value="(value) => emit('update:searchQuery', value)"
        @keyup.enter="emit('search')"
      />
      <NButton
        :round="true"
        type="primary"
        :size="compact ? 'small' : 'medium'"
        :class="compact ? 'w-8 min-w-8 px-0' : ''"
        :loading="searchLoading"
        @click="emit('search')"
      >
        <template #icon><Search class="h-4 w-4" /></template>
        <span v-if="!compact">Search</span>
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

.vod-search-input-compact:deep(.n-input) {
  --n-height: 34px;
}

.vod-search-input-compact:deep(.n-input__input-el) {
  font-size: 0.82rem;
}
</style>
