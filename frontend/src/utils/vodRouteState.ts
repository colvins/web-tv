import type { LocationQuery, LocationQueryRaw } from 'vue-router'

export type VodCatalogRouteState = {
  sourceId: string | null
  siteKey: string | null
  categoryId: string | null
  query: string
  page: number
}

function getQueryValue(value: LocationQuery[string]): string | null {
  if (Array.isArray(value)) {
    return value[0] ?? null
  }
  return value ?? null
}

export function parseVodCatalogRouteState(query: LocationQuery): VodCatalogRouteState {
  const pageValue = Number.parseInt(getQueryValue(query.page) ?? '1', 10)

  return {
    sourceId: getQueryValue(query.source),
    siteKey: getQueryValue(query.site),
    categoryId: getQueryValue(query.category),
    query: (getQueryValue(query.q) ?? '').trim(),
    page: Number.isFinite(pageValue) && pageValue > 0 ? pageValue : 1,
  }
}

export function buildVodCatalogQuery(state: Partial<VodCatalogRouteState>): LocationQueryRaw {
  const query: LocationQueryRaw = {}

  if (state.sourceId) {
    query.source = state.sourceId
  }
  if (state.siteKey) {
    query.site = state.siteKey
  }
  if (state.categoryId) {
    query.category = state.categoryId
  }
  if (state.query) {
    query.q = state.query
  }
  if (state.page && state.page > 1) {
    query.page = String(state.page)
  }

  return query
}

export function getVodCatalogRouteKey(state: VodCatalogRouteState): string {
  return JSON.stringify([state.sourceId, state.siteKey, state.categoryId, state.query, state.page])
}
