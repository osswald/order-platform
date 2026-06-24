import { computed, ref } from 'vue'
import { apiJson } from '../api'

const countries = ref([])
const loading = ref(false)
let loadPromise = null

export function useCountries() {
  const countryOptions = computed(() =>
    countries.value.map((country) => ({
      title: country.name,
      value: country.id,
    })),
  )

  async function fetchCountries({ force = false } = {}) {
    if (!force && countries.value.length) {
      return countries.value
    }
    if (loadPromise && !force) {
      return loadPromise
    }
    loading.value = true
    loadPromise = (async () => {
      try {
        countries.value = await apiJson('/countries/')
        return countries.value
      } finally {
        loading.value = false
        loadPromise = null
      }
    })()
    return loadPromise
  }

  function invalidateCountries() {
    countries.value = []
    loadPromise = null
  }

  function countryById(id) {
    return countries.value.find((country) => Number(country.id) === Number(id)) || null
  }

  function countryName(id) {
    return countryById(id)?.name || ''
  }

  return {
    countries,
    loading,
    countryOptions,
    fetchCountries,
    invalidateCountries,
    countryById,
    countryName,
  }
}
