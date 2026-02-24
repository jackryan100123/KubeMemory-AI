import { Component } from 'react'

export default class ErrorBoundary extends Component {
  state = { hasError: false, error: null }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[200px] p-6 bg-surface rounded-lg border border-border">
          <p className="text-accent-red font-mono text-lg mb-2">Something went wrong</p>
          <p className="text-muted text-sm text-center max-w-md">
            {this.state.error?.message || 'An unexpected error occurred.'}
          </p>
          <button
            type="button"
            onClick={() => this.setState({ hasError: false, error: null })}
            className="mt-4 px-4 py-2 rounded bg-accent text-bg font-mono text-sm hover:opacity-90"
          >
            Try again
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
