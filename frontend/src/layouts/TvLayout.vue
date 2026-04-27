<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import {
  Clock3,
  Heart,
  Home,
  MonitorPlay,
  PlaySquare,
  Search,
  Settings,
  type LucideIcon,
} from 'lucide-vue-next'

type NavItem = {
  label: string
  path: string
  icon: LucideIcon
}

const route = useRoute()

const navItems: NavItem[] = [
  { label: 'Home', path: '/', icon: Home },
  { label: 'Live', path: '/live', icon: MonitorPlay },
  { label: 'VOD', path: '/vod', icon: PlaySquare },
  { label: 'Search', path: '/search', icon: Search },
  { label: 'Favorites', path: '/favorites', icon: Heart },
  { label: 'History', path: '/history', icon: Clock3 },
  { label: 'Settings', path: '/settings', icon: Settings },
]

const pageTitle = computed(() => String(route.meta.title ?? 'web-tv'))

function isNavItemActive(path: string) {
  if (path === '/') {
    return route.path === '/'
  }
  return route.path === path || route.path.startsWith(`${path}/`)
}
</script>

<template>
  <div class="min-h-screen pb-24 text-white lg:pb-0">
    <aside
      class="glass-panel fixed left-5 top-5 z-30 hidden h-[calc(100vh-2.5rem)] w-24 flex-col items-center rounded-[2rem] px-3 py-5 lg:flex xl:w-64 xl:items-stretch"
      aria-label="Primary navigation"
    >
      <RouterLink
        to="/"
        class="mb-8 flex h-14 w-14 items-center justify-center rounded-3xl bg-white text-lg font-black text-cinema-950 xl:w-full xl:justify-start xl:px-5"
        aria-label="web-tv home"
      >
        <span>TV</span>
        <span class="ml-3 hidden text-base xl:inline">web-tv</span>
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

    <main class="px-5 pt-6 sm:px-8 lg:ml-32 lg:px-10 xl:ml-72">
      <header class="mb-8 flex items-center justify-between gap-4">
        <div>
          <p class="text-sm uppercase tracking-[0.32em] text-white/42">web-tv</p>
          <h1 class="mt-2 text-4xl font-semibold tracking-normal text-white sm:text-6xl">
            {{ pageTitle }}
          </h1>
        </div>
        <RouterLink
          to="/search"
          class="tv-focus-card glass-panel hidden min-h-12 rounded-3xl px-5 py-3 text-sm font-medium text-white/78 sm:block"
        >
          Search library
        </RouterLink>
      </header>

      <RouterView />
    </main>

    <nav
      class="glass-panel fixed inset-x-3 bottom-3 z-40 grid grid-cols-7 rounded-[2rem] p-2 lg:hidden"
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
