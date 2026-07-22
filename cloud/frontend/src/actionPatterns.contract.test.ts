import { describe, expect, it } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, relative, resolve } from 'node:path'

const srcRoot = resolve(process.cwd(), 'src')

function listVueFiles(dir: string): string[] {
  const out: string[] = []
  for (const name of readdirSync(dir)) {
    const path = join(dir, name)
    if (statSync(path).isDirectory()) {
      if (name === 'node_modules') continue
      out.push(...listVueFiles(path))
    } else if (name.endsWith('.vue')) {
      out.push(path)
    }
  }
  return out
}

/**
 * Collect free-form `<v-btn>` opening tags, respecting quotes so `>` inside
 * attribute values (e.g. `v-if="a > 1"`) does not truncate the tag.
 */
function iterVBtnTags(source: string): string[] {
  const tags: string[] = []
  const lower = source.toLowerCase()
  let i = 0
  while (i < source.length) {
    const start = lower.indexOf('<v-btn', i)
    if (start < 0) break
    const afterName = start + '<v-btn'.length
    const next = source[afterName]
    // Skip v-btn-toggle and similar
    if (next && !/\s|\/|>/.test(next)) {
      i = afterName
      continue
    }
    let pos = afterName
    let inQuote: '"' | "'" | null = null
    while (pos < source.length) {
      const c = source[pos]
      if (inQuote) {
        if (c === inQuote) inQuote = null
      } else if (c === '"' || c === "'") {
        inQuote = c
      } else if (c === '>') {
        tags.push(source.slice(start, pos + 1))
        i = pos + 1
        break
      }
      pos += 1
    }
    if (pos >= source.length) break
  }
  return tags
}

function findForbiddenVBtnVariants(source: string): string[] {
  return iterVBtnTags(source)
    .filter((tag) => /\bvariant\s*=\s*["']text["']/.test(tag) || /\bvariant\s*=\s*["']flat["']/.test(tag))
    .map((tag) => tag.replace(/\s+/g, ' ').slice(0, 120))
}

describe('cloud admin action patterns contract', () => {
  it('keeps VBtn default variant outlined in main.ts', () => {
    const mainTs = readFileSync(join(srcRoot, 'main.ts'), 'utf8')
    expect(mainTs).toMatch(/VBtn:\s*\{\s*variant:\s*['"]outlined['"]/)
  })

  it('does not use text or flat variants on free-form v-btn', () => {
    const offenders: { file: string; tag: string }[] = []
    for (const file of listVueFiles(srcRoot)) {
      const hits = findForbiddenVBtnVariants(readFileSync(file, 'utf8'))
      for (const tag of hits) {
        offenders.push({ file: relative(srcRoot, file), tag })
      }
    }
    expect(offenders, JSON.stringify(offenders, null, 2)).toEqual([])
  })
})
