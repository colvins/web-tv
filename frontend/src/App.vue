<script setup lang="ts">
import { darkTheme, NConfigProvider, NGlobalStyle, NMessageProvider } from 'naive-ui'

import TvLayout from '@/layouts/TvLayout.vue'
</script>

<template>
  <NConfigProvider :theme="darkTheme">
    <NMessageProvider>
      <NGlobalStyle />
      <TvLayout />
    </NMessageProvider>
  </NConfigProvider>
</template>
