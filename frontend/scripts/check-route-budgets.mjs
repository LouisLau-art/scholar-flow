#!/usr/bin/env node

import fs from 'node:fs'
import path from 'node:path'
import zlib from 'node:zlib'

const cwd = process.cwd()
const nextDir = path.resolve(cwd, '.next')
const configPath = process.env.ROUTE_BUDGET_CONFIG
  ? path.resolve(cwd, process.env.ROUTE_BUDGET_CONFIG)
  : path.resolve(cwd, 'scripts/route-budgets.json')

function readJson(filePath) {
  const raw = fs.readFileSync(filePath, 'utf8')
  return JSON.parse(raw)
}

function formatKb(bytes) {
  return (bytes / 1024).toFixed(1)
}

if (!fs.existsSync(nextDir)) {
  console.error('[route-budgets] Missing .next directory. Run `bun run build` first.')
  process.exit(2)
}

if (!fs.existsSync(configPath)) {
  console.error(`[route-budgets] Missing config: ${configPath}`)
  process.exit(2)
}

const config = readJson(configPath)
const routesConfig = config.routes || {}
const appBuildManifestCandidates = [
  path.join(nextDir, 'app-build-manifest.json'),
  path.join(nextDir, 'server', 'app-build-manifest.json'),
]
const appBuildManifestPath = appBuildManifestCandidates.find((candidate) => fs.existsSync(candidate))

if (!appBuildManifestPath) {
  console.warn(
    '[route-budgets] app-build-manifest.json not found in expected locations; skip route budget gate for this build format.',
  )
  process.exit(0)
}

const appPathRoutesManifestCandidates = [
  path.join(nextDir, 'app-path-routes-manifest.json'),
  path.join(nextDir, 'server', 'app-path-routes-manifest.json'),
]
const appPathRoutesManifestPath = appPathRoutesManifestCandidates.find((candidate) => fs.existsSync(candidate))

if (!appPathRoutesManifestPath) {
  console.warn(
    '[route-budgets] app-path-routes-manifest.json not found in expected locations; skip route budget gate for this build format.',
  )
  process.exit(0)
}

const appBuildManifest = readJson(appBuildManifestPath)
const appPathRoutesManifest = readJson(appPathRoutesManifestPath)
const pages = appBuildManifest.pages || {}

const results = []
let failed = false

for (const [publicRoute, budget] of Object.entries(routesConfig)) {
  const maxGzipKb = Number(budget?.maxGzipKb || 0)
  const routeKeys = Object.entries(appPathRoutesManifest)
    .filter(([, route]) => route === publicRoute)
    .map(([key]) => key)

  if (!routeKeys.length) {
    failed = true
    results.push({
      route: publicRoute,
      rawBytes: 0,
      gzipBytes: 0,
      budgetKb: maxGzipKb,
      status: 'MISSING_ROUTE',
    })
    continue
  }

  const assets = new Set()
  for (const key of routeKeys) {
    for (const asset of pages[key] || []) {
      if (String(asset).endsWith('.js')) assets.add(asset)
    }
  }

  let rawBytes = 0
  let gzipBytes = 0
  for (const asset of assets) {
    const filePath = path.join(nextDir, asset)
    if (!fs.existsSync(filePath)) continue
    const content = fs.readFileSync(filePath)
    rawBytes += content.length
    gzipBytes += zlib.gzipSync(content).length
  }

  const gzipKb = gzipBytes / 1024
  const pass = maxGzipKb > 0 ? gzipKb <= maxGzipKb : true
  if (!pass) failed = true

  results.push({
    route: publicRoute,
    rawBytes,
    gzipBytes,
    budgetKb: maxGzipKb,
    status: pass ? 'PASS' : 'OVER_BUDGET',
  })
}

const sorted = results.sort((a, b) => b.gzipBytes - a.gzipBytes)
console.log('[route-budgets] Route JS budget report (gzip)')
for (const row of sorted) {
  const budgetText = row.budgetKb > 0 ? `${row.budgetKb.toFixed(1)}KB` : 'n/a'
  console.log(
    `- ${row.status.padEnd(12)} ${row.route.padEnd(34)} gzip=${formatKb(row.gzipBytes)}KB raw=${formatKb(row.rawBytes)}KB budget=${budgetText}`
  )
}

if (failed) {
  console.error('[route-budgets] Budget gate failed.')
  process.exit(1)
}

console.log('[route-budgets] Budget gate passed.')
