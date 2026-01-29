import { describe, expect, it } from 'vitest'
import config from '../../vitest.config'

describe('coverage config', () => {
  it('enforces 70% thresholds', () => {
    const thresholds = config.test?.coverage?.thresholds
    expect(thresholds?.lines).toBeGreaterThanOrEqual(70)
    expect(thresholds?.branches).toBeGreaterThanOrEqual(70)
    expect(thresholds?.functions).toBeGreaterThanOrEqual(70)
    expect(thresholds?.statements).toBeGreaterThanOrEqual(70)
  })

  it('exports html/json reporters', () => {
    const reporters = config.test?.coverage?.reporter ?? []
    expect(reporters).toEqual(expect.arrayContaining(['html', 'json']))
  })
})
