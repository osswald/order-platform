<template>
  <div>
    <div v-if="events.length" class="event-context">
      <div v-if="showEventSelect" class="field">
        <label for="ops-event">Event</label>
        <select id="ops-event" v-model="opsEventId" class="select">
          <option v-for="e in events" :key="e.id" :value="e.id">{{ e.name }}</option>
        </select>
      </div>
      <p v-else-if="singleEventName" class="muted event-name">{{ singleEventName }}</p>
    </div>

    <router-view />
  </div>
</template>

<script setup lang="ts">
import { useAdminOperations } from '@/composables/useAdminOperations'

const {
  events,
  opsEventId,
  showEventSelect,
  singleEventName,
} = useAdminOperations()
</script>

<style scoped>
.event-context {
  margin-bottom: 1rem;
}
.event-name {
  margin: 0;
  font-size: 0.95rem;
}
</style>
