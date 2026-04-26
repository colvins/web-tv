<script setup lang="ts">
import EmptyRail from '@/components/EmptyRail.vue'
</script>

<template>
  <EmptyRail title="VOD Library" description="VOD catalog entries will appear here after VOD sites are configured." :count="6" />
  <EmptyRail title="Recently Updated" description="Cached VOD updates will populate this rail." :count="4" />
</template>
