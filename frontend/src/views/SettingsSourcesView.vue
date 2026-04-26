<script setup lang="ts">
import SettingsPanel from '@/components/SettingsPanel.vue'
</script>

<template>
  <div class="grid gap-5">
    <SettingsPanel
      title="Source Configuration"
      description="Source management screens will connect to the backend models without embedding parser, spider, or player logic in this skeleton."
    />
    <div class="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
      <SettingsPanel title="Live Sources" description="Live source records and refresh settings." />
      <SettingsPanel title="VOD Sites" description="VOD site connection records and priorities." />
      <SettingsPanel title="Parse APIs" description="Parse API endpoints and request configuration." />
      <SettingsPanel title="Cache" description="VOD cache visibility and maintenance controls." />
    </div>
  </div>
</template>
