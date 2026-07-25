import { afterEach, describe, expect, it } from 'vitest'
import { getAndroidAppInfo } from './androidAppInfo'

describe('getAndroidAppInfo', () => {
  afterEach(() => {
    delete window.AndroidApp
  })

  it('returns unavailable when bridge is missing', () => {
    expect(getAndroidAppInfo()).toEqual({ status: 'unavailable' })
  })

  it('returns unavailable when getAppInfo is missing', () => {
    window.AndroidApp = {}
    expect(getAndroidAppInfo()).toEqual({ status: 'unavailable' })
  })

  it('parses string JSON from bridge', () => {
    window.AndroidApp = {
      getAppInfo: () => JSON.stringify({ ok: true, versionName: '1.5.10', versionCode: 10510 }),
    }
    expect(getAndroidAppInfo()).toEqual({
      status: 'ok',
      versionName: '1.5.10',
      versionCode: 10510,
    })
  })

  it('parses object results from bridge', () => {
    window.AndroidApp = {
      getAppInfo: () => ({ ok: true, versionName: '2.0.0', versionCode: 20000 }),
    }
    expect(getAndroidAppInfo()).toEqual({
      status: 'ok',
      versionName: '2.0.0',
      versionCode: 20000,
    })
  })

  it('returns unavailable when bridge reports ok: false', () => {
    window.AndroidApp = {
      getAppInfo: () => JSON.stringify({ ok: false, error: 'broken' }),
    }
    expect(getAndroidAppInfo()).toEqual({ status: 'unavailable' })
  })

  it('returns unavailable when bridge throws', () => {
    window.AndroidApp = {
      getAppInfo: () => {
        throw new Error('boom')
      },
    }
    expect(getAndroidAppInfo()).toEqual({ status: 'unavailable' })
  })

  it('returns unavailable when versionName is missing', () => {
    window.AndroidApp = {
      getAppInfo: () => JSON.stringify({ ok: true, versionCode: 1 }),
    }
    expect(getAndroidAppInfo()).toEqual({ status: 'unavailable' })
  })
})
