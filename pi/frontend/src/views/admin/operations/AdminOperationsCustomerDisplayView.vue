<template>
  <div>
    <h1>Kundendisplay</h1>
    <p class="muted">URL für das Kundendisplay an der Kasse.</p>

    <div v-if="!hasCashRegisters" class="card">
      <p class="muted">Für dieses Event sind keine Kassen konfiguriert.</p>
    </div>

    <div v-else class="card">
      <div v-if="showRegisterSelect" class="field">
        <label for="ops-register">Kasse</label>
        <select id="ops-register" v-model="opsRegisterUuid" class="select">
          <option v-for="reg in cashRegisters" :key="String(reg.uuid)" :value="String(reg.uuid)">{{ reg.name }}</option>
        </select>
      </div>
      <p v-else-if="singleRegisterName" class="muted register-name">{{ singleRegisterName }}</p>

      <code v-if="displayUrl" class="display-url">{{ displayUrl }}</code>
      <div class="row">
        <button type="button" class="btn" :disabled="!displayUrl" @click="copyDisplayUrl">URL kopieren</button>
        <button type="button" class="btn" :disabled="!displayUrl" @click="openDisplay">Display öffnen</button>
      </div>
    </div>

    <button type="button" class="btn" style="width: 100%; margin-top: 1.5rem" @click="goBack">Zurück</button>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAdminOperations } from '@/composables/useAdminOperations'

const router = useRouter()
const {
  hasCashRegisters,
  showRegisterSelect,
  singleRegisterName,
  opsRegisterUuid,
  cashRegisters,
  displayUrl,
  copyDisplayUrl,
  openDisplay,
} = useAdminOperations()

function goBack() {
  router.push({ name: 'admin-operations' })
}
</script>

<style scoped>
.register-name {
  margin: 0 0 0.75rem;
  font-size: 0.95rem;
}
.display-url {
  display: block;
  word-break: break-all;
  font-size: 0.8rem;
  margin-bottom: 0.75rem;
}
</style>
