<template>
  <div>
    <h1>Lagerbestand</h1>
    <p class="muted">{{ event?.name }}</p>

    <div v-if="!stockGroups.length" class="card">
      <p>Keine Artikel mit Bestandsführung für dieses Event.</p>
    </div>
    <template v-else>
      <section v-for="group in stockGroups" :key="group.key" class="stock-section">
        <h2>{{ group.name }}</h2>
        <ul class="stock-list">
          <li v-for="a in group.items" :key="a.id" class="stock-row">
            <span class="name">{{ a.name }}</span>
            <span class="qty" :class="{ warn: !a.sellable }">{{ a.in_stock ?? 0 }} Stk.</span>
            <span v-if="!a.sellable" class="badge muted">nicht verkaufbar</span>
          </li>
        </ul>
      </section>
    </template>

    <button type="button" class="btn" style="width: 100%; margin-top: 1rem" @click="router.push({ name: 'hub' })">
      Zurück
    </button>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useBundle } from '../composables/useBundle'
import { useEventContext } from '../composables/useEventContext'
import { stockGroupsForEvent } from '@vendiqo/frontend-shared/stockByStation'

const router = useRouter()
const { event } = useEventContext()
const { refreshBundle } = useBundle()
const stockGroups = computed(() => stockGroupsForEvent(event.value))

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
.stock-section {
  margin-top: 1.25rem;
}
.stock-section:first-of-type {
  margin-top: 1rem;
}
.stock-section h2 {
  margin: 0 0 0.5rem;
  font-size: 1rem;
  font-weight: 600;
}
.stock-list {
  list-style: none;
  padding: 0;
  margin: 0;
  border: 1px solid var(--border);
  border-radius: 0.75rem;
  overflow: hidden;
}
.stock-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--border);
}
.stock-row:last-child {
  border-bottom: none;
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
