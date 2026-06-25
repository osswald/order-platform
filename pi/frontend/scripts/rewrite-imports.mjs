#!/usr/bin/env node
/**
 * Rewrite cross-directory relative imports to @/ alias.
 * Keeps same-directory ./ imports unchanged.
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const srcRoot = path.join(root, 'src')
const testsRoot = path.join(root, 'tests')

function walk(dir, acc = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) walk(full, acc)
    else if (/\.(ts|vue)$/.test(entry.name)) acc.push(full)
  }
  return acc
}

function resolveImport(fromFile, spec) {
  if (!spec.startsWith('.')) return spec
  const fromDir = path.dirname(fromFile)
  const resolved = path.normalize(path.join(fromDir, spec))
  const inSrc = resolved.startsWith(srcRoot + path.sep)
  const inTests = resolved.startsWith(testsRoot + path.sep)
  if (inSrc) {
    const rel = path.relative(srcRoot, resolved).replace(/\\/g, '/')
    return `@/${rel}`
  }
  if (inTests) {
    const rel = path.relative(testsRoot, resolved).replace(/\\/g, '/')
    return `@/../tests/${rel}`
  }
  return spec
}

function isSameDirImport(fromFile, spec) {
  if (!spec.startsWith('./')) return false
  const fromDir = path.dirname(fromFile)
  const resolved = path.normalize(path.join(fromDir, spec))
  return path.dirname(resolved) === fromDir
}

function transformFile(file) {
  let content = fs.readFileSync(file, 'utf8')
  const original = content
  content = content.replace(
    /from\s+['"](\.[^'"]+)['"]/g,
    (match, spec) => {
      if (isSameDirImport(file, spec)) return match
      const next = resolveImport(file, spec)
      return `from '${next}'`
    },
  )
  content = content.replace(
    /import\s+['"](\.[^'"]+)['"]/g,
    (match, spec) => {
      if (isSameDirImport(file, spec)) return match
      const next = resolveImport(file, spec)
      return `import '${next}'`
    },
  )
  if (content !== original) fs.writeFileSync(file, content)
}

for (const file of [...walk(srcRoot), ...walk(testsRoot)]) {
  transformFile(file)
}

console.log('Import rewrite complete')
