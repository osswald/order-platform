export type ThemePreference = 'light' | 'dark' | 'system'
export type EffectiveTheme = 'light' | 'dark'

export const THEME_PREFERENCE_KEY = 'theme_preference'

const THEME_COLOR_LIGHT = '#FFFFFF'
const THEME_COLOR_DARK = '#121212'

export function isThemePreference(value: unknown): value is ThemePreference {
  return value === 'light' || value === 'dark' || value === 'system'
}

export function readStoredThemePreference(): ThemePreference {
  const stored = localStorage.getItem(THEME_PREFERENCE_KEY)
  return isThemePreference(stored) ? stored : 'system'
}

export function systemPrefersDark(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return false
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

export function resolveEffectiveTheme(
  preference: ThemePreference,
  prefersDark = systemPrefersDark(),
): EffectiveTheme {
  if (preference === 'dark') return 'dark'
  if (preference === 'light') return 'light'
  return prefersDark ? 'dark' : 'light'
}

export function resolveInitialTheme(): EffectiveTheme {
  return resolveEffectiveTheme(readStoredThemePreference())
}

export function updateDomThemeClasses(theme: EffectiveTheme): void {
  if (typeof document === 'undefined') return
  document.documentElement.classList.toggle('v-theme--dark', theme === 'dark')
  document.documentElement.classList.toggle('v-theme--light', theme === 'light')
}

export function updateThemeColorMeta(theme: EffectiveTheme): void {
  if (typeof document === 'undefined') return
  const color = theme === 'dark' ? THEME_COLOR_DARK : THEME_COLOR_LIGHT
  let meta = document.querySelector('meta[name="theme-color"]')
  if (!meta) {
    meta = document.createElement('meta')
    meta.setAttribute('name', 'theme-color')
    document.head.appendChild(meta)
  }
  meta.setAttribute('content', color)
}
