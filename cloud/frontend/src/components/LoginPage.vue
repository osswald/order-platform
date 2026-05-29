<template>
  <div class="login-container">
    <div class="login-wrapper">
      <div class="login-card">
        <div class="login-header">
          <div class="logo-large">
            <img src="/apple-touch-icon.png" alt="" class="logo-icon" width="64" height="64" />
          </div>
          <h1>Vendiqo</h1>
          <p class="tagline">Enterprise Resource Planning</p>
        </div>

        <form @submit.prevent="submit" class="login-form">
          <div class="form-group">
            <label for="email">E-Mail Adresse</label>
            <input
              id="email"
              v-model="email"
              type="email"
              placeholder="admin@example.com"
              required
              class="form-input"
            />
          </div>

          <div class="form-group">
            <label for="password">Passwort</label>
            <input
              id="password"
              v-model="password"
              type="password"
              placeholder="••••••••"
              required
              class="form-input"
            />
          </div>

          <button type="submit" class="submit-btn">
            <span v-if="!isLoading">Anmelden</span>
            <span v-else>Wird geladen...</span>
          </button>
        </form>

        <div v-if="message" :class="['message', messageType]">
          {{ message }}
        </div>

        <div class="login-footer">
          <p class="version">Vendiqo ERP {{ label }}</p>
        </div>
      </div>

      <div class="login-side">
        <div class="feature-list">
          <div class="feature">
            <span class="feature-icon">📊</span>
            <h3>Zentrale Verwaltung</h3>
            <p>Verwalten Sie Ihre gesamte Organisation an einem Ort</p>
          </div>
          <div class="feature">
            <span class="feature-icon">📦</span>
            <h3>Bestandsverwaltung</h3>
            <p>Echtzeit-Bestandsverfolgung und Optimierung</p>
          </div>
          <div class="feature">
            <span class="feature-icon">💰</span>
            <h3>Finanzmanagement</h3>
            <p>Umfassende Finanzberichte und Analysen</p>
          </div>
          <div class="feature">
            <span class="feature-icon">👥</span>
            <h3>Kundenbeziehungen</h3>
            <p>Effektive Verwaltung Ihrer Kundenbeziehungen</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { apiUrl } from '../api'
import { useAppVersion } from '../composables/useAppVersion'

const { label } = useAppVersion()

const route = useRoute()
const email = ref('')
const password = ref('')
const message = ref('')
const messageType = ref('')
const isLoading = ref(false)

async function submit() {
  message.value = ''
  isLoading.value = true

  try {
    const body = new URLSearchParams()
    body.append('username', email.value)
    body.append('password', password.value)

    const res = await fetch(apiUrl('/auth/token'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: body.toString(),
      credentials: 'include'
    })

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      message.value = err.detail || 'Anmeldung fehlgeschlagen'
      messageType.value = 'error'
      isLoading.value = false
      return
    }

    const data = await res.json()
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('user_email', email.value)
    localStorage.setItem('is_admin', data.is_admin ? 'true' : 'false')
    if (data.role) localStorage.setItem('user_role', data.role)
    if (data.hire_company_id != null) {
      localStorage.setItem('user_hire_company_id', String(data.hire_company_id))
      localStorage.setItem('active_hire_company_id', String(data.hire_company_id))
    } else {
      localStorage.removeItem('user_hire_company_id')
    }
    localStorage.setItem('is_tenant_admin', data.is_tenant_admin ? 'true' : 'false')
    if (data.user_id != null) {
      localStorage.setItem('user_id', String(data.user_id))
    }
    message.value = 'Anmeldung erfolgreich!'
    messageType.value = 'success'

    const redirect = route.query.redirect
    const target =
      typeof redirect === 'string' && redirect.startsWith('/') ? redirect : '/dashboard'
    setTimeout(() => {
      window.location.href = target
    }, 500)
  } catch (e) {
    message.value = 'Netzwerkfehler - bitte versuchen Sie es später erneut'
    messageType.value = 'error'
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, var(--p-surface-100) 0%, var(--p-surface-ground) 100%);
  padding: 1rem;
}

.login-wrapper {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
  width: 100%;
  max-width: 1100px;
  align-items: center;
}

.login-card {
  background: var(--p-surface-card);
  border: 1px solid var(--p-content-border-color);
  border-radius: 16px;
  padding: 3rem 2rem;
  box-shadow: var(--p-card-shadow);
}

.login-header {
  text-align: center;
  margin-bottom: 2rem;
}

.logo-large {
  display: flex;
  justify-content: center;
  margin-bottom: 1rem;
}

.logo-icon {
  width: 4rem;
  height: 4rem;
  border-radius: 12px;
  object-fit: cover;
}

.login-header h1 {
  margin: 1rem 0 0;
  font-size: 2rem;
  color: var(--p-text-color);
  font-weight: 700;
  letter-spacing: 1px;
}

.tagline {
  margin: 0.5rem 0 0;
  color: var(--p-text-muted-color);
  font-size: 0.95rem;
  font-weight: 500;
  letter-spacing: 0.5px;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
}

.form-group label {
  margin-bottom: 0.5rem;
  color: var(--p-text-color);
  font-weight: 600;
  font-size: 0.95rem;
}

.form-input {
  padding: 0.875rem 1rem;
  border: 1px solid var(--p-form-field-border-color);
  border-radius: var(--p-form-field-border-radius);
  font-size: 1rem;
  font-family: inherit;
  transition: all 0.3s ease;
  background: var(--p-form-field-background);
  color: var(--p-form-field-color);
}

.form-input:focus {
  outline: none;
  border-color: var(--p-form-field-focus-border-color);
  box-shadow: var(--p-form-field-focus-ring-shadow);
}

.form-input::placeholder {
  color: var(--p-form-field-placeholder-color);
}

.submit-btn {
  padding: 1rem;
  background: var(--p-primary-color);
  color: var(--p-primary-contrast-color);
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: 0.5px;
  cursor: pointer;
  transition: all 0.3s ease;
  text-transform: uppercase;
}

.submit-btn:hover {
  transform: translateY(-2px);
  filter: brightness(0.97);
}

.submit-btn:active {
  transform: translateY(0);
}

.message {
  padding: 1rem;
  border-radius: 8px;
  text-align: center;
  font-weight: 600;
  margin-bottom: 1rem;
}

.message.success {
  background: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.message.error {
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.login-footer {
  text-align: center;
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--p-content-border-color);
}

.version {
  margin: 0;
  color: var(--p-text-muted-color);
  font-size: 0.85rem;
  opacity: 0.6;
}

.login-side {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.feature-list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.feature {
  background: var(--p-surface-card);
  padding: 1.5rem;
  border-radius: 12px;
  border: 1px solid var(--p-content-border-color);
  color: var(--p-text-color);
  box-shadow: var(--p-card-shadow);
}

.feature-icon {
  display: block;
  font-size: 2rem;
  margin-bottom: 0.75rem;
}

.feature h3 {
  margin: 0 0 0.5rem;
  font-size: 1.1rem;
  font-weight: 700;
}

.feature p {
  margin: 0;
  font-size: 0.95rem;
  color: var(--p-text-muted-color);
}

@media (max-width: 768px) {
  .login-wrapper {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .login-card {
    padding: 2rem 1.5rem;
  }

  .login-side {
    display: none;
  }

  .login-header h1 {
    font-size: 1.5rem;
  }

  .logo-icon {
    width: 3rem;
    height: 3rem;
  }
}
</style>
