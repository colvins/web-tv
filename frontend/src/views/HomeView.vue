<script setup lang="ts">
import EmptyRail from '@/components/EmptyRail.vue'
</script>

<template>
  <section class="mb-10 grid gap-5 xl:grid-cols-[1.5fr_1fr]">
    <div
      tabindex="0"
      class="tv-focus-card glass-panel flex min-h-[22rem] items-end rounded-[2.5rem] bg-[linear-gradient(135deg,rgba(137,180,255,0.2),rgba(255,184,107,0.12))] p-7 sm:p-10"
    >
      <div>
        <p class="mb-3 text-sm uppercase tracking-[0.28em] text-white/52">Ready</p>
        <h2 class="max-w-2xl text-4xl font-semibold sm:text-6xl">Connect sources to begin watching.</h2>
      </div>
    </div>
    <div class="glass-panel rounded-[2.5rem] p-7">
      <p class="text-sm uppercase tracking-[0.28em] text-white/42">Status</p>
      <div class="mt-8 grid gap-4">
        <RouterLink to="/settings/sources" class="tv-focus-card rounded-3xl border border-white/10 p-5">
          Configure sources
        </RouterLink>
        <RouterLink to="/live" class="tv-focus-card rounded-3xl border border-white/10 p-5">
          Browse live channels
        </RouterLink>
      </div>
    </div>
  </section>
  <EmptyRail title="Continue Watching" description="Playback history will appear here after content is played." />
  <EmptyRail title="Favorites" description="Favorite channels and VOD items will appear in this rail." />
</template>
