<template>
  <section class="panel">
    <div class="panel-header">
      <div>
        <h1>{{ title }}</h1>
        <p>{{ subtitle }}</p>
      </div>
      <Button v-if="showCreate" :label="createLabel" class="primary-button" @click="$emit('open-create')" />
    </div>

    <div class="form-grid" :class="{ 'detail-open': showDetail }">
      <Card v-if="showDetail" class="content-card">
        <template #content>
          <slot name="detail" />
        </template>
      </Card>

      <Card v-if="!showDetail" class="content-card">
        <template #content>
          <slot name="table" />
        </template>
      </Card>
    </div>
  </section>
</template>

<script setup>
import Button from 'primevue/button'
import Card from 'primevue/card'

const props = defineProps({
  title: String,
  subtitle: String,
  createLabel: {
    type: String,
    default: 'Neu',
  },
  showCreate: {
    type: Boolean,
    default: true,
  },
  showDetail: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['open-create'])
</script>

<style scoped>
.panel {
  padding: 2rem;
  min-height: 100%;
  background: var(--p-surface-ground);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.panel-header h1 {
  margin: 0;
  font-size: 2rem;
  color: var(--p-text-color);
}

.panel-header p {
  margin: 0.5rem 0 0;
  color: var(--p-text-muted-color);
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.25rem;
}

.form-grid.detail-open {
  grid-template-columns: 1fr;
}

.content-card {
  border: 1px solid var(--p-content-border-color);
  box-shadow: var(--p-card-shadow);
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.85rem;
}

.table-scroll {
  overflow-x: auto;
}

.primary-button {
  font-weight: 700;
}
</style>
