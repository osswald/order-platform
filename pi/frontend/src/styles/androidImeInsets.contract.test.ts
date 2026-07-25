/// <reference types="node" />
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), '../../../..')

function readRepo(...parts: string[]): string {
  return readFileSync(join(repoRoot, ...parts), 'utf8')
}

describe('android IME inset bridge (source contract)', () => {
  it('MainActivity forwards WindowInsetsCompat.Type.ime()', () => {
    const kt = readRepo('android/app/src/main/java/ch/vendiqo/app/MainActivity.kt')
    expect(kt).toMatch(/WindowInsetsCompat\.Type\.ime\(\)/)
    expect(kt).toMatch(/updateIme\(/)
  })

  it('AndroidInsetsBridge exposes IME separately from safe-bottom', () => {
    const kt = readRepo('android/app/src/main/java/ch/vendiqo/app/AndroidInsetsBridge.kt')
    expect(kt).toMatch(/getImeInsetsJson/)
    expect(kt).toMatch(/--ime-bottom/)
    expect(kt).toMatch(/vendiqo-android-insets/)
    expect(kt).toMatch(/--safe-bottom/)
  })

  it('activity uses adjustNothing so WebView is not resized by the IME', () => {
    const manifest = readRepo('android/app/src/main/AndroidManifest.xml')
    expect(manifest).toMatch(/android:windowSoftInputMode="adjustNothing"/)
  })
})
