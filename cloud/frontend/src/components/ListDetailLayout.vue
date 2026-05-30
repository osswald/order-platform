<template>
  <section class="vq-page panel">
    <div class="vq-page-header panel-header">
      <div>
        <h1>{{ title }}</h1>
        <p>{{ subtitle }}</p>
      </div>
      <v-btn v-if="showCreate" color="primary" @click="$emit('open-create')">
        {{ createLabel }}
      </v-btn>
    </div>

    <div class="form-grid" :class="{ 'detail-open': showDetail }">
      <v-card v-if="showDetail" class="content-card" variant="flat" border>
        <v-card-text class="content-card-body">
          <slot name="detail" />
        </v-card-text>
      </v-card>

      <v-card v-if="!showDetail" class="content-card" variant="flat" border>
        <v-card-text class="content-card-body">
          <slot name="table" />
        </v-card-text>
      </v-card>
    </div>
  </section>
</template>

<script setup>
defineProps({
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

defineEmits(['open-create'])
</script>

<style scoped>
.form-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.25rem;
}

.content-card {
  overflow: visible;
}
</style>
