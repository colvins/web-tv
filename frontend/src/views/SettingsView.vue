<script setup lang="ts">
import SettingsPanel from '@/components/SettingsPanel.vue'
</script>

<template>
  <div class="grid gap-5">
    <SettingsPanel
      title="Playback"
      description="Playback preferences and device behavior will be configured here as player features are added."
    />
    <RouterLink to="/settings/sources" class="tv-focus-card glass-panel rounded-[2rem] p-6">
      <h2 class="text-2xl font-semibold">Sources</h2>
      <p class="mt-3 max-w-2xl text-sm leading-6 text-white/58">
        Manage live, VOD, parse API, and source configuration records.
      </p>
    </RouterLink>
  </div>
</template>
