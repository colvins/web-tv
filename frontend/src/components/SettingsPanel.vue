<script setup lang="ts">
defineProps<{
  title: string
  description: string
}>()
</script>

<template>
  <article class="glass-panel rounded-[2rem] p-6">
    <h2 class="text-2xl font-semibold">{{ title }}</h2>
    <p class="mt-3 max-w-2xl text-sm leading-6 text-white/58">{{ description }}</p>
    <slot />
  </article>
</template>
