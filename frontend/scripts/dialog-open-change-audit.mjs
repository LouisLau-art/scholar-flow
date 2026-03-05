#!/usr/bin/env node

import fs from 'node:fs'
import path from 'node:path'

const rootDir = process.cwd()
const srcDir = path.join(rootDir, 'src')

const SOURCE_EXTENSIONS = new Set(['.ts', '.tsx', '.js', '.jsx'])

const riskyPattern = /onOpenChange=\{\s*\([^)]*\)\s*=>[\s\S]{0,240}?set[A-Za-z0-9_]*\(\s*true\s*\)/g
const directSetterPattern = /onOpenChange=\{set[A-Za-z0-9_]+\}/g

function collectSourceFiles(dir, output = []) {
  const entries = fs.readdirSync(dir, { withFileTypes: true })
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      collectSourceFiles(fullPath, output)
      continue
    }
    if (!SOURCE_EXTENSIONS.has(path.extname(entry.name))) continue
    output.push(fullPath)
  }
  return output
}

function lineNumberAt(content, index) {
  return content.slice(0, index).split('\n').length
}

const files = collectSourceFiles(srcDir)
const riskyMatches = []
let directSetterCount = 0

for (const filePath of files) {
  const content = fs.readFileSync(filePath, 'utf8')

  const risky = [...content.matchAll(riskyPattern)]
  for (const match of risky) {
    const idx = match.index ?? 0
    const line = lineNumberAt(content, idx)
    riskyMatches.push({
      file: path.relative(rootDir, filePath),
      line,
      snippet: match[0].replace(/\s+/g, ' ').slice(0, 180),
    })
  }

  directSetterCount += [...content.matchAll(directSetterPattern)].length
}

console.log('Dialog onOpenChange Audit')
console.log('==========================')

if (riskyMatches.length > 0) {
  console.error('Found risky onOpenChange reopen patterns:')
  for (const match of riskyMatches) {
    console.error(`- ${match.file}:${match.line}`)
    console.error(`  ${match.snippet}`)
  }
  console.error('\nFix guideline: keep onOpenChange close-only (nextOpen=false -> close).')
  process.exit(1)
}

console.log(`Direct setter usage count (manual review recommended): ${directSetterCount}`)
console.log('Dialog onOpenChange audit passed.')
