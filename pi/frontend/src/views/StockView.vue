<template>
  <div>
    <h1>Lagerbestand</h1>
    <p class="muted">{{ event?.name }}</p>

    <div v-if="!articles.length" class="card">
      <p>Keine Artikel mit Bestandsführung für dieses Event.</p>
    </div>
    <ul v-else class="stock-list">
      <li v-for="a in articles" :key="a.id" class="stock-row">
        <span class="name">{{ a.name }}</span>
        <span class="qty" :class="{ warn: !a.sellable }">{{ a.in_stock ?? 0 }} Stk.</span>
        <span v-if="!a.sellable" class="badge muted">nicht verkaufbar</span>
      </li>
    </ul>

    <button type="button" class="btn" style="width: 100%; margin-top: 1rem" @click="router.push({ name: 'hub' })">
      Zurück
    </button>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { stockArticlesForEvent } from '../store'
import { useBundle } from '../composables/useBundle'
import { useEventContext } from '../composables/useEventContext'

const router = useRouter()
const { event } = useEventContext()
const { refreshBundle } = useBundle()
const articles = computed(() => stockArticlesForEvent(event.value))

function onVisible() {
  if (document.visibilityState === 'visible') refreshBundle()
}

onMounted(() => {
  refreshBundle()
  document.addEventListener('visibilitychange', onVisible)
})

onUnmounted(() => {
  document.removeEventListener('visibilitychange', onVisible)
})
</script>

<style scoped>
.stock-list {
  list-style: none;
  padding: 0;
  margin: 1rem 0 0;
}
.stock-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--border);
}
.name {
  flex: 1;
  font-weight: 500;
}
.qty {
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.qty.warn {
  color: var(--danger);
}
.badge {
  font-size: 0.75rem;
  width: 100%;
}
</style>
