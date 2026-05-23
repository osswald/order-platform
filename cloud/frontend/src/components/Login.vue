<template>
  <section>
    <h2>Login</h2>
    <form @submit.prevent="submit">
      <div>
        <label for="email">E-Mail</label>
        <input id="email" v-model="email" type="email" required />
      </div>
      <div>
        <label for="password">Passwort</label>
        <input id="password" v-model="password" type="password" required />
      </div>
      <button type="submit">Anmelden</button>
    </form>
    <p v-if="message">{{ message }}</p>
    <div v-if="loggedIn">
      <p>Angemeldet als {{ userEmail }}</p>
      <button @click="logout">Logout</button>
      <button @click="refresh">Refresh Access Token</button>
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import { apiUrl } from '../api'

const email = ref('')
const password = ref('')
const message = ref('')
const loggedIn = ref(false)
const userEmail = ref('')

function setAccessToken(token) {
  localStorage.setItem('access_token', token)
}

function clearAccessToken() {
  localStorage.removeItem('access_token')
}

async function submit() {
  message.value = ''
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
      credentials: 'include' // to receive refresh cookie
    })

    if (!res.ok) {
      const err = await res.json().catch(()=>({detail: res.statusText}))
      message.value = err.detail || 'Login fehlgeschlagen'
      return
    }

    const data = await res.json()
    setAccessToken(data.access_token)
    userEmail.value = email.value
    loggedIn.value = true
    message.value = 'Erfolgreich angemeldet'
  } catch (e) {
    message.value = 'Netzwerkfehler'
  }
}

async function refresh() {
  try {
    const res = await fetch(apiUrl('/auth/refresh'), {
      method: 'POST',
      credentials: 'include'
    })
    if (!res.ok) {
      message.value = 'Refresh fehlgeschlagen'
      return
    }
    const data = await res.json()
    setAccessToken(data.access_token)
    message.value = 'Access Token erneuert'
  } catch (e) {
    message.value = 'Netzwerkfehler'
  }
}

async function logout() {
  try {
    await fetch(apiUrl('/auth/logout'), { method: 'POST', credentials: 'include' })
  } catch (e) {
    // ignore
  }
  clearAccessToken()
  loggedIn.value = false
  userEmail.value = ''
  message.value = 'Abgemeldet'
}

// initialize
if (localStorage.getItem('access_token')) {
  loggedIn.value = true
  userEmail.value = ''
}

</script>

<style scoped>
section {
  background: #fff;
  padding: 1rem;
  border-radius: 8px;
  max-width: 420px;
}
label { display:block; margin-top:0.5rem }
input { width:100%; padding:0.5rem; margin-top:0.25rem }
button { margin-top: 1rem }
</style>
