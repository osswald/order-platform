<template>
  <header class="header" :class="{ 'header--compact': isMobile }">
    <div class="header-left">
      <v-btn
        v-if="isMobile"
        icon="mdi-menu"
        variant="text"
        :aria-label="$t('common.menu')"
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
        <v-avatar icon="mdi-account" size="36" />
        <span class="user-email">{{ userEmail }}</span>
        <v-btn
          :prepend-icon="isMobile ? 'mdi-logout' : undefined"
          :icon="isMobile ? 'mdi-logout' : undefined"
          variant="outlined"
          @click="logout"
        >
          <span v-if="!isMobile">{{ $t('common.logout') }}</span>
        </v-btn>
      </div>
    </div>
  </header>
</template>

<script setup>
defineProps({
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
  background: rgb(var(--v-theme-surface));
  border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
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

.header-right {
  flex-shrink: 0;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.user-email {
  font-size: 0.95rem;
  opacity: 0.7;
  max-width: 12rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header--compact .user-email {
  display: none;
}

@media (max-width: 768px) {
  .header {
    padding: 0.75rem 1rem;
  }

  .logo {
    font-size: 1.25rem;
  }
}
</style>
