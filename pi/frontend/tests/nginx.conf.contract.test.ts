import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const nginxConfPath = join(dirname(fileURLToPath(import.meta.url)), '..', 'nginx.conf')
const nginxConf = readFileSync(nginxConfPath, 'utf8')

describe('pi frontend nginx.conf', () => {
  it('resolves pi-backend lazily so OTA can probe the image without compose DNS', () => {
    expect(nginxConf).toMatch(/resolver\s+127\.0\.0\.11\b/)
    expect(nginxConf).toMatch(/set\s+\$backend\s+"pi-backend:8000"/)
    expect(nginxConf).not.toMatch(/proxy_pass\s+http:\/\/pi-backend:/)
    expect(nginxConf).toMatch(/proxy_pass\s+http:\/\/\$backend\/health;/)
    expect(nginxConf).toMatch(/proxy_pass\s+http:\/\/\$backend\/v1\/;/)
  })

  it('still serves the SPA from / and proxies API/health paths', () => {
    expect(nginxConf).toMatch(/location\s+\/health\s*\{/)
    expect(nginxConf).toMatch(/location\s+\/v1\/\s*\{/)
    expect(nginxConf).toMatch(/location\s+\/\s*\{/)
    expect(nginxConf).toMatch(/try_files\s+\$uri\s+\$uri\/\s+\/index\.html;/)
  })
})
