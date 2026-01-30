'use client'

import React, { Component, ErrorInfo, ReactNode } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

interface Props {
  children?: ReactNode
}

interface State {
  hasError: boolean
}

export default class ErrorBoundary extends Component<Props, State> {
  /**
   * 全局错误边界组件
   * 遵循章程：防止页面崩溃，实现优雅降级
   */
  public state: State = {
    hasError: false
  }

  public static getDerivedStateFromError(_: Error): State {
    return { hasError: true }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo)
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 p-4 text-center">
          <div className="rounded-full bg-red-50 p-4 mb-6">
            <AlertTriangle className="h-12 w-12 text-red-600" />
          </div>
          <h1 className="font-serif text-2xl font-bold text-slate-900">Something went wrong</h1>
          <p className="mt-2 text-slate-600 max-w-md">
            We encountered an unexpected error. Please try refreshing the page or contact support if the issue persists.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="mt-8 flex items-center gap-2 rounded-md bg-slate-900 px-6 py-2 text-white hover:bg-slate-800"
          >
            <RefreshCw className="h-4 w-4" /> Refresh Page
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
