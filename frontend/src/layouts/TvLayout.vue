<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import {
  Clock3,
  Home,
  MonitorPlay,
  PlaySquare,
  Settings,
  type LucideIcon,
} from 'lucide-vue-next'
import { vodPageHeaderTitle } from '@/composables/useVodPageHeader'

type NavItem = {
  label: string
  path: string
  icon: LucideIcon
}

const route = useRoute()
const isVodCatalogRoute = computed(() => route.name === 'vod')

const navItems: NavItem[] = [
  { label: 'Home', path: '/', icon: Home },
  { label: 'Live', path: '/live', icon: MonitorPlay },
  { label: 'VOD', path: '/vod', icon: PlaySquare },
  { label: 'History', path: '/history', icon: Clock3 },
  { label: 'Settings', path: '/settings', icon: Settings },
]

const pageTitle = computed(() => {
  if (isVodCatalogRoute.value) {
    return vodPageHeaderTitle.value || 'VOD'
  }
  return String(route.meta.title ?? 'Lets.TV')
})

function isNavItemActive(path: string) {
  if (path === '/') {
    return route.path === '/'
  }
  return route.path === path || route.path.startsWith(`${path}/`)
}
</script>

<template>
  <div class="min-h-screen pb-[calc(6.5rem+env(safe-area-inset-bottom))] text-white lg:pb-0">
    <aside
      class="glass-panel fixed left-5 top-5 z-30 hidden h-[calc(100vh-2.5rem)] w-24 flex-col items-center rounded-[2rem] px-3 py-5 lg:flex xl:w-64 xl:items-stretch"
      aria-label="Primary navigation"
    >
      <RouterLink
        to="/"
        class="mb-8 flex h-14 w-14 items-center justify-center rounded-3xl bg-white text-lg font-black text-cinema-950 xl:w-full xl:justify-start xl:px-5"
        aria-label="Lets.TV home"
      >
        <span>TV</span>
        <span class="ml-3 hidden text-base xl:inline">Lets.TV</span>
      </RouterLink>

      <nav class="flex w-full flex-1 flex-col gap-3">
        <RouterLink
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="tv-focus-card flex h-14 items-center justify-center rounded-3xl border border-transparent text-white/72 xl:justify-start xl:px-5"
          :class="{ 'bg-white/16 text-white shadow-glow': isNavItemActive(item.path) }"
        >
          <component :is="item.icon" class="h-5 w-5" aria-hidden="true" />
          <span class="ml-4 hidden font-medium xl:inline">{{ item.label }}</span>
        </RouterLink>
      </nav>
    </aside>

    <main class="px-5 pt-[calc(env(safe-area-inset-top)+1rem)] sm:px-8 sm:pt-8 lg:ml-32 lg:px-10 lg:pt-6 xl:ml-72">
      <header
        class="mb-6 flex flex-col gap-4 sm:mb-8"
        :class="isVodCatalogRoute ? 'sm:flex-row sm:items-start sm:justify-between' : 'sm:flex-row sm:items-center sm:justify-between'"
      >
        <div class="min-w-0 w-full sm:w-auto">
          <p class="text-sm uppercase tracking-[0.32em] text-white/42">Lets.TV</p>
          <div
            v-if="isVodCatalogRoute"
            class="mt-2 flex items-start justify-between gap-3 sm:block"
          >
            <h1 class="min-w-0 truncate text-3xl font-semibold tracking-normal text-white sm:text-6xl">
              {{ pageTitle }}
            </h1>
            <div
              id="vod-page-toolbar-mobile"
              class="flex shrink-0 justify-end sm:hidden"
            ></div>
          </div>
          <h1 v-else class="mt-2 truncate text-3xl font-semibold tracking-normal text-white sm:text-6xl">
            {{ pageTitle }}
          </h1>
        </div>
        <div
          v-if="isVodCatalogRoute"
          id="vod-page-toolbar-desktop"
          class="hidden sm:flex sm:w-auto sm:max-w-[11rem] lg:max-w-none"
        ></div>
      </header>

      <RouterView />
    </main>

    <nav
      class="glass-panel fixed inset-x-3 bottom-[calc(env(safe-area-inset-bottom)+0.75rem)] z-40 grid grid-cols-5 rounded-[2rem] p-2 lg:hidden"
      aria-label="Mobile navigation"
    >
      <RouterLink
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="tv-focus-card flex min-h-14 flex-col items-center justify-center rounded-3xl text-white/68"
        :class="{ 'bg-white/16 text-white': isNavItemActive(item.path) }"
      >
        <component :is="item.icon" class="h-5 w-5" aria-hidden="true" />
        <span class="mt-1 hidden text-[0.68rem] font-medium sm:block">{{ item.label }}</span>
      </RouterLink>
    </nav>
  </div>
</template>
