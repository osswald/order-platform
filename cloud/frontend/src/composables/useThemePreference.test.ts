import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, ref } from 'vue'
import { mount } from '@vue/test-utils'

const themeChange = vi.fn()
const themeGlobalName = ref('light')

vi.mock('vuetify', () => ({
  useTheme: () => ({
    change: themeChange,
    global: { name: themeGlobalName },
  }),
}))

vi.mock('../api', () => ({
  apiJson: vi.fn(),
}))

import { apiJson } from '../api'
import {
  setThemePreference,
  syncThemeFromAuthMe,
  themePreference,
  updateThemePreference,
  useThemePreference,
} from './useThemePreference'
import { THEME_PREFERENCE_KEY } from '../utils/themePreference'

function mountThemePreference() {
  return mount(
    defineComponent({
      template: '<div />',
      setup() {
        useThemePreference()
      },
    }),
  )
}

describe('useThemePreference', () => {
  beforeEach(() => {
    localStorage.clear()
    themePreference.value = 'system'
    themeChange.mockClear()
    vi.mocked(apiJson).mockReset()
    document.documentElement.className = ''
    mountThemePreference()
  })

  it('maps system preference to dark when media query matches dark', () => {
    vi.spyOn(window, 'matchMedia').mockReturnValue({
      matches: true,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    } as unknown as MediaQueryList)

    setThemePreference('system')

    expect(themeChange).toHaveBeenCalledWith('dark')
    expect(document.documentElement.classList.contains('v-theme--dark')).toBe(true)
  })

  it('persists preference to localStorage', () => {
    vi.spyOn(window, 'matchMedia').mockReturnValue({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    } as unknown as MediaQueryList)

    setThemePreference('light')

    expect(localStorage.getItem(THEME_PREFERENCE_KEY)).toBe('light')
    expect(themeChange).toHaveBeenCalledWith('light')
  })

  it('calls PATCH /auth/me when updating preference while authenticated', async () => {
    vi.spyOn(window, 'matchMedia').mockReturnValue({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    } as unknown as MediaQueryList)
    localStorage.setItem('access_token', 'token')
    vi.mocked(apiJson).mockResolvedValue({ theme_preference: 'dark' })

    await updateThemePreference('dark')

    expect(apiJson).toHaveBeenCalledWith('/auth/me', {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ theme_preference: 'dark' }),
    })
    expect(localStorage.getItem(THEME_PREFERENCE_KEY)).toBe('dark')
  })

  it('syncs preference from auth me response', () => {
    vi.spyOn(window, 'matchMedia').mockReturnValue({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    } as unknown as MediaQueryList)

    syncThemeFromAuthMe({
      id: 1,
      email: 'user@example.com',
      is_admin: false,
      role: 'member',
      is_tenant_admin: false,
      is_organisation_admin: false,
      hire_companies: [],
      theme_preference: 'dark',
    })

    expect(themePreference.value).toBe('dark')
    expect(localStorage.getItem(THEME_PREFERENCE_KEY)).toBe('dark')
  })

  it('exposes preference through composable hook', () => {
    const { preference } = useThemePreference()
    expect(preference.value).toBe('system')
  })
})
