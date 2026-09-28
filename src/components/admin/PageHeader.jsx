export default function PageHeader({ eyebrow, title, description, actions, children }) {
  return (
    <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        {eyebrow && <p className="mb-1 text-sm font-bold uppercase tracking-[0.3em] text-brand">{eyebrow}</p>}
        <h1 className="display-title text-4xl sm:text-5xl">{title}</h1>
        {description && <p className="mt-2 max-w-2xl text-lg text-ink-soft">{description}</p>}
        {children}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-3">{actions}</div>}
    </header>
  );
}
