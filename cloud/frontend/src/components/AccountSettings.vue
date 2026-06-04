<template>
  <section class="settings-panel">
    <v-card class="settings-card version-card" max-width="42rem">
      <v-card-title>System</v-card-title>
      <v-card-subtitle>Installierte Version dieser Anwendung.</v-card-subtitle>
      <v-card-text>
        <p class="version-line">Vendiqo ERP {{ label }}</p>
      </v-card-text>
    </v-card>

    <v-card class="settings-card" max-width="42rem">
      <v-card-title>Passwort ändern</v-card-title>
      <v-card-subtitle>Aktualisieren Sie Ihr eigenes Passwort.</v-card-subtitle>
      <v-card-text>
        <p class="form-required-legend"><span class="vq-asterisk">*</span> Pflichtfeld</p>
        <v-form ref="formRef" @submit.prevent="changePassword">
          <div class="form-field">
            <v-text-field
              v-model="form.currentPassword"
              label="Aktuelles Passwort"
              placeholder="Aktuelles Passwort"
              :type="showCurrent ? 'text' : 'password'"
              :append-inner-icon="showCurrent ? 'mdi-eye-off' : 'mdi-eye'"
              autocomplete="current-password"
              hide-details="auto"
              required
              :rules="[rules.required]"
              @click:append-inner="showCurrent = !showCurrent"
            />
          </div>
          <div class="form-field">
            <v-text-field
              v-model="form.newPassword"
              label="Neues Passwort"
              placeholder="Neues Passwort"
              :type="showNew ? 'text' : 'password'"
              :append-inner-icon="showNew ? 'mdi-eye-off' : 'mdi-eye'"
              autocomplete="new-password"
              hide-details="auto"
              required
              :rules="[rules.required]"
              @click:append-inner="showNew = !showNew"
            />
          </div>
          <div class="form-field">
            <v-text-field
              v-model="form.confirmPassword"
              label="Neues Passwort bestätigen"
              placeholder="Neues Passwort bestätigen"
              :type="showConfirm ? 'text' : 'password'"
              :append-inner-icon="showConfirm ? 'mdi-eye-off' : 'mdi-eye'"
              autocomplete="new-password"
              hide-details="auto"
              required
              :rules="confirmRules"
              @click:append-inner="showConfirm = !showConfirm"
            />
          </div>
          <div class="actions">
            <v-btn color="primary" type="submit">Passwort speichern</v-btn>
          </div>
          <p v-if="message" :class="messageType">{{ message }}</p>
        </v-form>
      </v-card-text>
    </v-card>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { apiFetch } from '../api'
import { useAppVersion } from '../composables/useAppVersion'
import { rules, validateForm } from '../utils/formRules.js'

const { label } = useAppVersion()

const form = ref({
  currentPassword: '',
  newPassword: '',
  confirmPassword: '',
})
const formRef = ref(null)
const message = ref('')
const messageType = ref('')
const showCurrent = ref(false)
const showNew = ref(false)
const showConfirm = ref(false)

const confirmRules = computed(() => [
  rules.required,
  rules.passwordMatch(form.value.newPassword),
])

async function changePassword() {
  if (!(await validateForm(formRef))) return
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
  } catch {
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

.version-card {
  margin-bottom: 1.5rem;
}

.version-line {
  margin: 0;
  opacity: 0.7;
  font-size: 0.95rem;
}

@media (max-width: 700px) {
  .settings-panel {
    padding: 1rem;
  }
}
</style>
