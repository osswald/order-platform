<template>
  <section class="settings-panel">
    <v-card class="settings-card version-card" max-width="42rem">
      <v-card-title>{{ $t('settings.system') }}</v-card-title>
      <v-card-subtitle>{{ $t('settings.systemSubtitle') }}</v-card-subtitle>
      <v-card-text>
        <p class="version-line">{{ $t('settings.versionLine', { version: label }) }}</p>
      </v-card-text>
    </v-card>

    <v-card class="settings-card appearance-card" max-width="42rem">
      <v-card-title>{{ $t('settings.appearance') }}</v-card-title>
      <v-card-subtitle>{{ $t('settings.appearanceSubtitle') }}</v-card-subtitle>
      <v-card-text>
        <v-btn-toggle
          v-model="themePreference"
          mandatory
          divided
          color="primary"
          @update:model-value="onThemeChange"
        >
          <v-btn value="light" prepend-icon="mdi-white-balance-sunny">
            {{ $t('settings.themeLight') }}
          </v-btn>
          <v-btn value="dark" prepend-icon="mdi-weather-night">
            {{ $t('settings.themeDark') }}
          </v-btn>
          <v-btn value="system" prepend-icon="mdi-monitor">
            {{ $t('settings.themeSystem') }}
          </v-btn>
        </v-btn-toggle>
        <p v-if="themeMessage" :class="themeMessageType">{{ themeMessage }}</p>
      </v-card-text>
    </v-card>

    <v-card class="settings-card" max-width="42rem">
      <v-card-title>{{ $t('settings.changePassword') }}</v-card-title>
      <v-card-subtitle>{{ $t('settings.changePasswordSubtitle') }}</v-card-subtitle>
      <v-card-text>
        <p class="form-required-legend">
          <span class="vq-asterisk">*</span> {{ $t('common.requiredLegend') }}
        </p>
        <v-form ref="formRef" @submit.prevent="changePassword">
          <div class="form-field">
            <v-text-field
              v-model="form.currentPassword"
              :label="$t('settings.currentPassword')"
              :placeholder="$t('settings.currentPassword')"
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
              :label="$t('settings.newPassword')"
              :placeholder="$t('settings.newPassword')"
              :type="showNew ? 'text' : 'password'"
              :append-inner-icon="showNew ? 'mdi-eye-off' : 'mdi-eye'"
              autocomplete="new-password"
              hide-details="auto"
              required
              :rules="[rules.required, rules.minPasswordLength()]"
              @click:append-inner="showNew = !showNew"
            />
          </div>
          <div class="form-field">
            <v-text-field
              v-model="form.confirmPassword"
              :label="$t('settings.confirmPassword')"
              :placeholder="$t('settings.confirmPassword')"
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
            <v-btn color="primary" type="submit">{{ $t('settings.savePassword') }}</v-btn>
          </div>
          <p v-if="message" :class="messageType">{{ message }}</p>
        </v-form>
      </v-card-text>
    </v-card>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { apiJson } from '../api'
import { useAppVersion } from '../composables/useAppVersion'
import { themePreference, updateThemePreference } from '../composables/useThemePreference'
import type { ThemePreference } from '../utils/themePreference'
import { rules, validateForm } from '../utils/formRules.js'

const { t } = useI18n()
const { label } = useAppVersion()

const themeMessage = ref('')
const themeMessageType = ref('')

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

async function onThemeChange(value: ThemePreference | null) {
  if (!value) return
  themeMessage.value = ''
  try {
    await updateThemePreference(value)
    themeMessage.value = t('settings.themeUpdated')
    themeMessageType.value = 'success'
  } catch {
    themeMessage.value = t('settings.themeUpdateFailed')
    themeMessageType.value = 'error'
  }
}

async function changePassword() {
  if (!(await validateForm(formRef))) return
  try {
    await apiJson('/auth/change-password', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        current_password: form.value.currentPassword,
        new_password: form.value.newPassword,
      }),
    })
    form.value = {
      currentPassword: '',
      newPassword: '',
      confirmPassword: '',
    }
    message.value = t('settings.passwordUpdated')
    messageType.value = 'success'
  } catch {
    message.value = t('settings.passwordUpdateFailed')
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

.appearance-card {
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
