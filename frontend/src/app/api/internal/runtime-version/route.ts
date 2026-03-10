import { NextResponse } from 'next/server'

function normalizeSha(value: string | undefined): string | null {
  const text = String(value || '').trim()
  return text ? text : null
}

export async function GET() {
  const deploySha =
    normalizeSha(process.env.VERCEL_GIT_COMMIT_SHA) ||
    normalizeSha(process.env.NEXT_PUBLIC_VERCEL_GIT_COMMIT_SHA) ||
    normalizeSha(process.env.GIT_COMMIT_SHA) ||
    null

  const appEnv = String(process.env.NEXT_PUBLIC_APP_ENV || 'development').trim().toLowerCase()
  const deploymentUrl =
    String(
      process.env.NEXT_PUBLIC_SITE_URL ||
        process.env.VERCEL_PROJECT_PRODUCTION_URL ||
        process.env.VERCEL_URL ||
        ''
    ).trim() || null

  return NextResponse.json({
    success: true,
    deploy_sha: deploySha,
    app_env: appEnv,
    deployment_url: deploymentUrl,
    source: process.env.VERCEL ? 'vercel' : 'unknown',
  })
}
