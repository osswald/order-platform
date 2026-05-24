<template>
  <header class="header">
    <div class="header-left">
      <div class="logo">
        <span class="logo-icon">V</span>
        <span class="logo-text">Vendiqo</span>
      </div>
    </div>
    <div class="header-right">
      <div class="user-info">
        <Avatar icon="pi pi-user" shape="circle" />
        <span class="user-email">{{ userEmail }}</span>
        <Button label="Logout" icon="pi pi-sign-out" severity="secondary" outlined @click="logout" />
      </div>
    </div>
  </header>
</template>

<script setup>
import Avatar from 'primevue/avatar'
import Button from 'primevue/button'

defineProps({
  userEmail: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['logout'])

function logout() {
  emit('logout')
}
</script>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.85rem 1.5rem;
  background: var(--p-surface-card);
  color: var(--p-text-color);
  border-bottom: 1px solid var(--p-content-border-color);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-left {
  flex: 1;
}

.logo {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.logo-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  background: var(--p-primary-color);
  color: var(--p-primary-contrast-color);
  border-radius: 0.75rem;
  font-size: 1.2rem;
}

.logo-text {
  color: var(--p-text-color);
}

.header-right {
  flex: 1;
  display: flex;
  justify-content: flex-end;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.user-email {
  font-size: 0.95rem;
  color: var(--p-text-muted-color);
}
</style>
