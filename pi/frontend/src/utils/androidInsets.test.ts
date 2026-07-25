import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  ANDROID_INSETS_EVENT,
  applyAndroidSafeAreaInsets,
  readAndroidImeBottomInset,
} from './androidInsets'

describe('androidInsets', () => {
  afterEach(() => {
    delete window.AndroidInsets
    document.documentElement.style.removeProperty('--safe-top')
    document.documentElement.style.removeProperty('--safe-bottom')
    document.documentElement.style.removeProperty('--safe-left')
    document.documentElement.style.removeProperty('--safe-right')
    document.documentElement.style.removeProperty('--ime-bottom')
  })

  it('applies system bar and ime CSS variables from the bridge', () => {
    window.AndroidInsets = {
      getSystemBarInsetsJson: () =>
        JSON.stringify({ top: 24, bottom: 16, left: 0, right: 0 }),
      getImeInsetsJson: () => JSON.stringify({ bottom: 320 }),
    }
    const dispatch = vi.spyOn(window, 'dispatchEvent')
    applyAndroidSafeAreaInsets()
    const root = document.documentElement.style
    expect(root.getPropertyValue('--safe-top')).toBe('24px')
    expect(root.getPropertyValue('--safe-bottom')).toBe('16px')
    expect(root.getPropertyValue('--ime-bottom')).toBe('320px')
    expect(dispatch).toHaveBeenCalledWith(expect.any(Event))
    expect((dispatch.mock.calls[0][0] as Event).type).toBe(ANDROID_INSETS_EVENT)
  })

  it('readAndroidImeBottomInset prefers bridge then CSS var', () => {
    window.AndroidInsets = {
      getImeInsetsJson: () => JSON.stringify({ bottom: 280 }),
    }
    expect(readAndroidImeBottomInset()).toBe(280)
    delete window.AndroidInsets
    document.documentElement.style.setProperty('--ime-bottom', '120px')
    expect(readAndroidImeBottomInset()).toBe(120)
  })

  it('readAndroidImeBottomInset returns 0 when unavailable', () => {
    expect(readAndroidImeBottomInset()).toBe(0)
  })
})
