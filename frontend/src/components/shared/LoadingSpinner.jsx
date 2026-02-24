export default function LoadingSpinner({ className = '' }) {
  return (
    <div
      className={`inline-block h-6 w-6 animate-spin rounded-full border-2 border-border border-t-accent ${className}`}
      role="status"
      aria-label="Loading"
    />
  )
}
