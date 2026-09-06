import packageLock from '../../package-lock.json'
import { describe, expect, it } from 'vitest'

type PackageLock = {
  packages: Record<string, { version?: string }>
}

const lock = packageLock as PackageLock

function parseSemver(version: string): [number, number, number] {
  const [major, minor, patch] = version.split('.').map((part) => Number(part))
  return [major, minor, patch]
}

function isAtLeast(version: string, minimum: string): boolean {
  const [major, minor, patch] = parseSemver(version)
  const [minMajor, minMinor, minPatch] = parseSemver(minimum)
  if (major !== minMajor) return major > minMajor
  if (minor !== minMinor) return minor > minMinor
  return patch >= minPatch
}

function versionsFor(packageName: string): string[] {
  return Object.entries(lock.packages)
    .filter(([name]) => name.endsWith(`/${packageName}`) || name === `node_modules/${packageName}`)
    .map(([, pkg]) => pkg.version)
    .filter((version): version is string => Boolean(version))
}

describe('package-lock security floors', () => {
  it('pins js-yaml to 4.3.1 or later', () => {
    const versions = versionsFor('js-yaml')
    expect(versions.length).toBeGreaterThan(0)
    for (const version of versions) {
      expect(isAtLeast(version, '4.3.1'), `js-yaml ${version} is below 4.3.1`).toBe(true)
    }
  })

  it('pins nanoid to 3.3.18 or later', () => {
    const versions = versionsFor('nanoid')
    expect(versions.length).toBeGreaterThan(0)
    for (const version of versions) {
      expect(isAtLeast(version, '3.3.18'), `nanoid ${version} is below 3.3.18`).toBe(true)
    }
  })

  it('pins postcss to 8.5.23 or later', () => {
    const versions = versionsFor('postcss')
    expect(versions.length).toBeGreaterThan(0)
    for (const version of versions) {
      expect(isAtLeast(version, '8.5.23'), `postcss ${version} is below 8.5.23`).toBe(true)
    }
  })
})
