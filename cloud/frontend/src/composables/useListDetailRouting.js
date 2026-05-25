import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

function parseRouteId(value) {
  if (value == null || value === '') return null
  const id = Number(value)
  return Number.isFinite(id) ? id : null
}

/**
 * URL-driven list / new / detail navigation for ListDetailLayout pages.
 * @param {string} listRouteName - e.g. 'waiters' (routes: waiters, waiters-new, waiters-detail)
 */
export function useListDetailRouting(listRouteName) {
  const route = useRoute()
  const router = useRouter()

  const detailRouteName = `${listRouteName}-detail`
  const newRouteName = `${listRouteName}-new`

  const isCreateMode = computed(() => route.name === newRouteName)
  const editMode = computed(() => route.name === detailRouteName)
  const showDetail = computed(() => isCreateMode.value || editMode.value)
  const routeEntityId = computed(() =>
    editMode.value ? parseRouteId(route.params.id) : null,
  )

  function organisationQuery() {
    const query = {}
    if (route.query.organisation != null && route.query.organisation !== '') {
      query.organisation = route.query.organisation
    }
    return query
  }

  function goToList() {
    return router.push({ name: listRouteName, query: organisationQuery() })
  }

  function goToCreate() {
    return router.push({ name: newRouteName, query: organisationQuery() })
  }

  function goToDetail(id) {
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

export function listDetailRoutes({ path, listName, component, meta }) {
  return [
    { path, name: listName, component, meta },
    { path: `${path}/new`, name: `${listName}-new`, component, meta },
    { path: `${path}/:id(\\d+)`, name: `${listName}-detail`, component, meta },
  ]
}
