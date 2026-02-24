export default function EmptyState({ icon, title, description, actionLabel, onAction }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[180px] p-6 text-center">
      {icon && <div className="text-4xl text-muted mb-3">{icon}</div>}
      <h3 className="font-mono text-lg text-white mb-1">{title}</h3>
      {description && <p className="text-muted text-sm max-w-sm mb-4">{description}</p>}
      {actionLabel && onAction && (
        <button
          type="button"
          onClick={onAction}
          className="px-4 py-2 rounded bg-accent text-bg font-mono text-sm hover:opacity-90"
        >
          {actionLabel}
        </button>
      )}
    </div>
  )
}
