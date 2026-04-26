<script setup lang="ts">
defineProps<{
  title: string
  description: string
  count?: number
}>()
</script>

<template>
  <section class="mb-10">
    <div class="mb-4 flex items-end justify-between gap-4">
      <h2 class="text-2xl font-semibold text-white">{{ title }}</h2>
    </div>
    <div class="flex gap-5 overflow-x-auto pb-5 [scrollbar-width:none]">
      <article
        v-for="index in count ?? 5"
        :key="index"
        tabindex="0"
        class="tv-focus-card glass-panel flex aspect-[16/9] min-w-[16rem] max-w-[28rem] flex-1 items-end rounded-[2rem] p-5 sm:min-w-[22rem]"
      >
        <div>
          <div class="mb-3 h-2 w-20 rounded-full bg-white/14"></div>
          <p class="max-w-72 text-sm leading-6 text-white/54">{{ description }}</p>
        </div>
      </article>
    </div>
  </section>
</template>
