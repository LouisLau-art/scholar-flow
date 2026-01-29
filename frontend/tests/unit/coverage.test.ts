import { describe, expect, it } from 'vitest'
import fs from 'fs'
import path from 'path'

const configPath = path.resolve(__dirname, '../../vitest.config.ts')

describe('coverage config', () => {
  it('enforces 70% thresholds', () => {
    const configText = fs.readFileSync(configPath, 'utf8')
    expect(configText).toMatch(/lines:\s*70/)
    expect(configText).toMatch(/branches:\s*70/)
    expect(configText).toMatch(/functions:\s*70/)
    expect(configText).toMatch(/statements:\s*70/)
  })

  it('exports html/json reporters', () => {
    const configText = fs.readFileSync(configPath, 'utf8')
    expect(configText).toMatch(/reporter:\s*\['text',\s*'json',\s*'html'\]/)
  })
})
