<template>
  <section class="settings-panel">
    <Card class="settings-card version-card">
      <template #title>System</template>
      <template #subtitle>Installierte Version dieser Anwendung.</template>
      <template #content>
        <p class="version-line">Vendiqo ERP {{ label }}</p>
      </template>
    </Card>

    <Card class="settings-card">
      <template #title>Passwort ändern</template>
      <template #subtitle>Aktualisieren Sie Ihr eigenes Passwort.</template>
      <template #content>
        <div class="form-field">
          <label>Aktuelles Passwort</label>
          <Password v-model="form.currentPassword" :feedback="false" toggleMask placeholder="Aktuelles Passwort" />
        </div>
        <div class="form-field">
          <label>Neues Passwort</label>
          <Password v-model="form.newPassword" :feedback="false" toggleMask placeholder="Neues Passwort" />
        </div>
        <div class="form-field">
          <label>Neues Passwort bestätigen</label>
          <Password v-model="form.confirmPassword" :feedback="false" toggleMask placeholder="Neues Passwort bestätigen" />
        </div>
        <div class="actions">
          <Button label="Passwort speichern" :disabled="!canSave" @click="changePassword" />
        </div>
        <p v-if="message" :class="messageType">{{ message }}</p>
      </template>
    </Card>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Password from 'primevue/password'
import { apiFetch } from '../api'
import { useAppVersion } from '../composables/useAppVersion'

const { label } = useAppVersion()

const form = ref({
  currentPassword: '',
  newPassword: '',
  confirmPassword: '',
})
const message = ref('')
const messageType = ref('')

const canSave = computed(() => {
  return (
    form.value.currentPassword &&
    form.value.newPassword &&
    form.value.confirmPassword &&
    form.value.newPassword === form.value.confirmPassword
  )
})

async function changePassword() {
  if (form.value.newPassword !== form.value.confirmPassword) {
    message.value = 'Die neuen Passwörter stimmen nicht überein.'
    messageType.value = 'error'
    return
  }
  try {
    const response = await apiFetch('/auth/change-password', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        current_password: form.value.currentPassword,
        new_password: form.value.newPassword,
      }),
    })
    if (!response.ok) throw new Error(await response.text())
    form.value = {
      currentPassword: '',
      newPassword: '',
      confirmPassword: '',
    }
    message.value = 'Passwort aktualisiert.'
    messageType.value = 'success'
  } catch (error) {
    message.value = 'Passwort konnte nicht geändert werden.'
    messageType.value = 'error'
  }
}
</script>

<style scoped>
.settings-panel {
  min-height: 100%;
  padding: 2rem;
}

.settings-card {
  max-width: 42rem;
}

.version-card {
  margin-bottom: 1.5rem;
}

.version-line {
  margin: 0;
  color: var(--p-text-muted-color);
  font-size: 0.95rem;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  margin-bottom: 1rem;
}

label {
  color: var(--p-text-color);
  font-size: 0.875rem;
  font-weight: 600;
}

:deep(.p-password),
:deep(.p-inputtext) {
  width: 100%;
}

.actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 1.25rem;
}

.success,
.error {
  margin-top: 1rem;
}

@media (max-width: 700px) {
  .settings-panel {
    padding: 1rem;
  }
}
</style>
