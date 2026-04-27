<script setup lang="ts">
import { Film } from 'lucide-vue-next'
import { ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    src: string | null
    alt: string
    aspectClass?: string
    iconClass?: string
    imageClass?: string
  }>(),
  {
    aspectClass: 'aspect-[3/4]',
    iconClass: 'h-12 w-12',
    imageClass: 'h-full w-full object-cover',
  },
)

const failed = ref(false)

watch(
  () => props.src,
  () => {
    failed.value = false
  },
)
</script>

<template>
  <div class="relative overflow-hidden bg-white/6" :class="aspectClass">
    <img
      v-if="src && !failed"
      :src="src"
      :alt="alt"
      :class="imageClass"
      loading="lazy"
      @error="failed = true"
    />
    <div v-else class="flex h-full w-full items-center justify-center text-white/30">
      <Film :class="iconClass" />
    </div>
  </div>
</template>
