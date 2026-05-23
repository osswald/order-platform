<template>
  <div class="card">
    <h2>Stationen</h2>
    <p class="muted">Kein App-Layout konfiguriert — Artikel pro Station.</p>
    <div v-for="st in stations" :key="st.uuid" class="station">
      <h3>{{ st.name }}</h3>
      <div class="arts">
        <button
          v-for="a in stationArticles(st)"
          :key="a.id"
          type="button"
          class="art-btn"
          @click="$emit('pick', [a.id])"
        >
          {{ a.name }}
          <span class="muted">{{ formatPrice(a) }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { isArticleSellable } from '../utils/bundleHelpers'
import { formatPrice as formatPriceAmount } from '../utils/money'

const props = defineProps({
  event: { type: Object, required: true },
})

defineEmits(['pick'])

const stations = computed(() => props.event?.configuration?.stations || [])

function stationArticles(st) {
  const arts = props.event?.articles || {}
  const out = []
  for (const id of st.article_ids || []) {
    const a = arts[String(id)] || arts[id]
    if (a && isArticleSellable(a)) out.push({ ...a, id: Number(id) })
  }
  return out
}

function formatPrice(a) {
  return formatPriceAmount(a.price ?? 0)
}
</script>

<style scoped>
.station {
  margin-bottom: 1rem;
}
.station h3 {
  font-size: 0.95rem;
  margin: 0 0 0.5rem;
}
.arts {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.art-btn {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 0.55rem 0.75rem;
  border-radius: 0.5rem;
  border: 1px solid var(--border);
  background: #334155;
  color: var(--text);
  cursor: pointer;
  min-height: 48px;
  font-size: 0.9rem;
  touch-action: manipulation;
}
</style>
