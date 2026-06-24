import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { LocationQueryRaw, RouteRecordName, RouteRecordRaw, RouteMeta } from 'vue-router'
import type { Component } from 'vue'
import '@/router/meta'

function parseRouteId(value: unknown): number | null {
  if (value == null || value === '') return null
  const id = Number(value)
  return Number.isFinite(id) ? id : null
}

export interface OrganisationQuery extends LocationQueryRaw {
  organisation?: string
}

/**
 * URL-driven list / new / detail navigation for ListDetailLayout pages.
 */
export function useListDetailRouting(listRouteName: RouteRecordName) {
  const route = useRoute()
  const router = useRouter()

  const detailRouteName = `${String(listRouteName)}-detail`
  const newRouteName = `${String(listRouteName)}-new`

  const isCreateMode = computed(() => route.name === newRouteName)
  const editMode = computed(() => route.name === detailRouteName)
  const showDetail = computed(() => isCreateMode.value || editMode.value)
  const routeEntityId = computed(() =>
    editMode.value ? parseRouteId(route.params.id) : null,
  )

  function organisationQuery(): OrganisationQuery {
    const query: OrganisationQuery = {}
    if (route.query.organisation != null && route.query.organisation !== '') {
      query.organisation = String(route.query.organisation)
    }
    return query
  }

  function goToList() {
    return router.push({ name: listRouteName, query: organisationQuery() })
  }

  function goToCreate() {
    return router.push({ name: newRouteName, query: organisationQuery() })
  }

  function goToDetail(id: number | string) {
    return router.push({
      name: detailRouteName,
      params: { id: String(id) },
      query: organisationQuery(),
    })
  }

  return {
    isCreateMode,
    editMode,
    showDetail,
    routeEntityId,
    organisationQuery,
    goToList,
    goToCreate,
    goToDetail,
  }
}

export interface ListDetailRoutesOptions {
  path: string
  listName: string
  component: Component
  meta: RouteMeta
  createMeta?: RouteMeta
  detailMeta?: RouteMeta
}

export function listDetailRoutes({
  path,
  listName,
  component,
  meta,
  createMeta,
  detailMeta,
}: ListDetailRoutesOptions): RouteRecordRaw[] {
  return [
    { path, name: listName, component, meta },
    {
      path: `${path}/new`,
      name: `${listName}-new`,
      component,
      meta: createMeta ?? meta,
    },
    {
      path: `${path}/:id(\\d+)`,
      name: `${listName}-detail`,
      component,
      meta: detailMeta ?? meta,
    },
  ]
}
