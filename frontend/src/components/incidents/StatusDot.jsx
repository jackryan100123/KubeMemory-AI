import { clsx } from 'clsx'

export default function StatusDot({ status }) {
  const isOpen = status === 'open' || status === 'investigating'
  return (
    <span
      className={clsx(
        'inline-block h-2 w-2 rounded-full',
        isOpen ? 'animate-pulse bg-accent' : 'bg-muted'
      )}
      title={status}
      aria-hidden
    />
  )
}
