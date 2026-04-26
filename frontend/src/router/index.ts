import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import FavoritesView from '@/views/FavoritesView.vue'
import HistoryView from '@/views/HistoryView.vue'
import HomeView from '@/views/HomeView.vue'
import LiveView from '@/views/LiveView.vue'
import SearchView from '@/views/SearchView.vue'
import SettingsSourcesView from '@/views/SettingsSourcesView.vue'
import SettingsView from '@/views/SettingsView.vue'
import VodView from '@/views/VodView.vue'

const routes: RouteRecordRaw[] = [
  { path: '/', name: 'home', component: HomeView, meta: { title: 'Watch Now' } },
  { path: '/live', name: 'live', component: LiveView, meta: { title: 'Live TV' } },
  { path: '/vod', name: 'vod', component: VodView, meta: { title: 'VOD' } },
  { path: '/search', name: 'search', component: SearchView, meta: { title: 'Search' } },
  { path: '/favorites', name: 'favorites', component: FavoritesView, meta: { title: 'Favorites' } },
  { path: '/history', name: 'history', component: HistoryView, meta: { title: 'History' } },
  { path: '/settings', name: 'settings', component: SettingsView, meta: { title: 'Settings' } },
  {
    path: '/settings/sources',
    name: 'settings-sources',
    component: SettingsSourcesView,
    meta: { title: 'Sources' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.afterEach((to) => {
  document.title = `${String(to.meta.title ?? 'web-tv')} - web-tv`
})

export default router
