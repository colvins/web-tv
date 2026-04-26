<script setup lang="ts">
import { darkTheme, NConfigProvider, NGlobalStyle } from 'naive-ui'

import TvLayout from '@/layouts/TvLayout.vue'
</script>

<template>
  <NConfigProvider :theme="darkTheme">
    <NGlobalStyle />
    <TvLayout />
  </NConfigProvider>
</template>
