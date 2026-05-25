<template>
  <header class="header" :class="{ 'header--compact': isMobile }">
    <div class="header-left">
      <Button
        v-if="isMobile"
        type="button"
        icon="pi pi-bars"
        severity="secondary"
        text
        rounded
        aria-label="Menü"
        class="menu-toggle"
        @click="toggleNav"
      />
      <div class="logo">
        <img src="/apple-touch-icon.png" alt="" class="logo-icon" width="36" height="36" />
        <span class="logo-text">Vendiqo</span>
      </div>
    </div>
    <div class="header-right">
      <div class="user-info">
        <Avatar icon="pi pi-user" shape="circle" />
        <span class="user-email">{{ userEmail }}</span>
        <Button
          :label="logoutLabel"
          icon="pi pi-sign-out"
          severity="secondary"
          outlined
          class="logout-button"
          @click="logout"
        />
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import Avatar from 'primevue/avatar'
import Button from 'primevue/button'

const props = defineProps({
  userEmail: {
    type: String,
    default: '',
  },
  isMobile: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['logout', 'toggle-nav'])

const logoutLabel = computed(() => (props.isMobile ? undefined : 'Logout'))

function logout() {
  emit('logout')
}

function toggleNav() {
  emit('toggle-nav')
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
  gap: 0.5rem;
}

.header-left {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.25rem;
  min-width: 0;
}

.menu-toggle {
  flex-shrink: 0;
}

.logo {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: 0.5px;
  min-width: 0;
}

.logo-icon {
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 0.75rem;
  object-fit: cover;
  flex-shrink: 0;
}

.logo-text {
  color: var(--p-text-color);
}

.header-right {
  flex-shrink: 0;
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
  max-width: 12rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header--compact .user-email {
  display: none;
}

.header--compact .logout-button :deep(.p-button-label) {
  display: none;
}

@media (max-width: 768px) {
  .header {
    padding: 0.75rem 1rem;
  }

  .logo {
    font-size: 1.25rem;
  }

  .user-email {
    display: none;
  }

  .logout-button :deep(.p-button-label) {
    display: none;
  }

  .user-info {
    gap: 0.5rem;
  }
}
</style>
