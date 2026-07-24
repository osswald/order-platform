import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useTheme } from 'vuetify'
import { apiJson, isAuthSessionActive } from '@/api'
import type { AuthMeResponse } from '@/types/api'
import {
  isThemePreference,
  readStoredThemePreference,
  resolveEffectiveTheme,
  systemPrefersDark,
  type EffectiveTheme,
  type ThemePreference,
  THEME_PREFERENCE_KEY,
  updateDomThemeClasses,
  updateThemeColorMeta,
} from '@/utils/themePreference'

export const themePreference = ref<ThemePreference>(readStoredThemePreference())

let vuetifyThemeChange: ((name: EffectiveTheme) => void) | null = null
let mediaQuery: MediaQueryList | null = null

function onSystemPreferenceChange() {
  if (themePreference.value !== 'system') return
  applyEffectiveTheme()
}

function attachSystemPreferenceListener() {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return
  mediaQuery?.removeEventListener('change', onSystemPreferenceChange)
  mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  mediaQuery.addEventListener('change', onSystemPreferenceChange)
}

function detachSystemPreferenceListener() {
  mediaQuery?.removeEventListener('change', onSystemPreferenceChange)
}

export function applyEffectiveTheme(prefersDark = systemPrefersDark()) {
  const effective = resolveEffectiveTheme(themePreference.value, prefersDark)
  vuetifyThemeChange?.(effective)
  updateDomThemeClasses(effective)
  updateThemeColorMeta(effective)
}

export function setThemePreference(next: ThemePreference, persistLocal = true) {
  themePreference.value = next
  if (persistLocal) {
    localStorage.setItem(THEME_PREFERENCE_KEY, next)
  }
  applyEffectiveTheme()
}

export function syncThemeFromAuthMe(data: AuthMeResponse) {
  if (isThemePreference(data.theme_preference)) {
    setThemePreference(data.theme_preference)
  }
}

export async function updateThemePreference(next: ThemePreference) {
  setThemePreference(next)
  if (!isAuthSessionActive()) return
  await apiJson<AuthMeResponse>('/auth/me', {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ theme_preference: next }),
  })
}

export function useThemePreference() {
  const theme = useTheme()
  vuetifyThemeChange = (name: EffectiveTheme) => {
    theme.change(name)
  }

  const effectiveTheme = computed(() =>
    resolveEffectiveTheme(themePreference.value, systemPrefersDark()),
  )

  onMounted(() => {
    applyEffectiveTheme()
    attachSystemPreferenceListener()
  })

  onUnmounted(() => {
    detachSystemPreferenceListener()
  })

  return {
    preference: themePreference,
    effectiveTheme,
    setThemePreference,
    updateThemePreference,
  }
}
