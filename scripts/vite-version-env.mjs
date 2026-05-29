import { execSync } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const COMMIT_TIME_FORMAT = '%Y%m%d%H%M'

function readVersionFile() {
  const versionPath = resolve(repoRoot, 'VERSION')
  if (!existsSync(versionPath)) return '0.0.0-dev'
  return readFileSync(versionPath, 'utf8').trim()
}

function readCommitTime() {
  if (process.env.VITE_BUILD_TIME) return process.env.VITE_BUILD_TIME
  try {
    return execSync(`git log -1 --format=%cd --date=format:${COMMIT_TIME_FORMAT}`, {
      cwd: repoRoot,
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
    }).trim()
  } catch {
    return 'dev'
  }
}

export function getAppVersionEnv() {
  return {
    VITE_APP_VERSION: process.env.VITE_APP_VERSION || readVersionFile(),
    VITE_BUILD_TIME: readCommitTime(),
  }
}

/** Inject version env vars for Vite (import.meta.env.VITE_*). */
export function applyAppVersionEnv() {
  Object.assign(process.env, getAppVersionEnv())
}
