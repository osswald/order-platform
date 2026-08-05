import { beforeEach, describe, expect, it, vi } from 'vitest'
import { absolutePublicUrl, publicOrigin } from './publicOrigin'

vi.mock('@/api/base', () => ({
  isAndroidApp: vi.fn(() => false),
  getApiBase: vi.fn(() => 'http://192.168.192.10'),
}))

import { getApiBase, isAndroidApp } from '@/api/base'

describe('publicOrigin / absolutePublicUrl', () => {
  beforeEach(() => {
    vi.mocked(isAndroidApp).mockReturnValue(false)
    vi.mocked(getApiBase).mockReturnValue('http://192.168.192.10')
    vi.stubGlobal('location', { origin: 'https://appassets.androidplatform.net' })
  })

  it('uses window.location.origin when not Android', () => {
    vi.stubGlobal('location', { origin: 'http://192.168.192.10' })
    expect(publicOrigin()).toBe('http://192.168.192.10')
    expect(absolutePublicUrl('/kitchen/grill?event=1')).toBe(
      'http://192.168.192.10/kitchen/grill?event=1',
    )
  })

  it('uses getApiBase on Android instead of appassets origin', () => {
    vi.mocked(isAndroidApp).mockReturnValue(true)
    vi.mocked(getApiBase).mockReturnValue('http://192.168.192.10')
    expect(publicOrigin()).toBe('http://192.168.192.10')
    expect(absolutePublicUrl('/kitchen/grill?event=3')).toBe(
      'http://192.168.192.10/kitchen/grill?event=3',
    )
    expect(absolutePublicUrl('/kitchen/grill?event=3')).not.toContain('appassets')
  })

  it('strips trailing slash from getApiBase', () => {
    vi.mocked(isAndroidApp).mockReturnValue(true)
    vi.mocked(getApiBase).mockReturnValue('http://10.0.0.5/')
    expect(publicOrigin()).toBe('http://10.0.0.5')
  })
})
