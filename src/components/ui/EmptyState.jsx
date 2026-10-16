import Ribbons from './Ribbons';

export default function EmptyState({ icon: Icon, title, message, action }) {
  return (
    <div className="relative overflow-hidden rounded-3xl border-2 border-dashed border-line bg-surface-raised px-6 py-14 text-center">
      <Ribbons className="pointer-events-none absolute inset-0 text-brand/[0.07]" />
      <div className="relative mx-auto flex max-w-md flex-col items-center">
        {Icon && (
          <span className="mb-5 grid h-20 w-20 place-items-center rounded-3xl bg-brand text-cream shadow-lift">
            <Icon size={38} strokeWidth={2.2} />
          </span>
        )}
        <h3 className="text-2xl font-extrabold uppercase tracking-tight">{title}</h3>
        {message && <p className="mt-2 text-lg text-ink-soft">{message}</p>}
        {action && <div className="mt-6">{action}</div>}
      </div>
    </div>
  );
}
