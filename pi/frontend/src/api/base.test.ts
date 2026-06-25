import { beforeEach, describe, expect, it, vi } from 'vitest'
import { buildApiUrl, getApiBase, isAndroidApp, setApiBase } from '@/api/base'

describe('api base helpers', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.unstubAllEnvs()
  })

  it('detects android app from env', () => {
    vi.stubEnv('VITE_ANDROID_APP', 'true')
    expect(isAndroidApp()).toBe(true)
  })

  it('stores and reads custom api base', () => {
    setApiBase('http://192.168.1.10:8001')
    expect(getApiBase()).toBe('http://192.168.1.10:8001')
    setApiBase('')
    expect(getApiBase()).toMatch(/^https?:\/\//)
  })

  it('buildApiUrl joins base and path', () => {
    expect(buildApiUrl('http://127.0.0.1:8001', '/v1/bundle')).toBe('http://127.0.0.1:8001/v1/bundle')
    expect(buildApiUrl('http://127.0.0.1:8001', 'v1/meta')).toBe('http://127.0.0.1:8001/v1/meta')
  })
})
