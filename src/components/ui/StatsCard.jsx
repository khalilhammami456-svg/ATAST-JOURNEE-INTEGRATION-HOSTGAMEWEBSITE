export default function StatsCard({ icon: Icon, label, value, detail, tone = 'default', className = '' }) {
  const brand = tone === 'brand';
  return (
    <div
      className={`relative overflow-hidden rounded-xl2 p-5 ${
        brand ? 'bg-brand text-cream shadow-lift' : 'card'
      } ${className}`}
    >
      {brand && (
        <svg className="absolute -right-10 -top-10 h-40 w-40 text-cream/15" viewBox="0 0 100 100" aria-hidden="true">
          <path
            d="M5 60 C 30 60, 50 45, 55 5"
            stroke="currentColor"
            strokeWidth="9"
            fill="none"
            strokeLinecap="round"
          />
        </svg>
      )}
      <div className="relative flex items-center gap-2">
        {Icon && <Icon size={18} strokeWidth={2.6} className={brand ? 'text-cream/80' : 'text-brand'} />}
        <p className={`text-sm font-bold uppercase tracking-widest ${brand ? 'text-cream/80' : 'text-ink-soft'}`}>
          {label}
        </p>
      </div>
      <div className="relative mt-2 text-5xl font-extrabold leading-none tracking-tight">{value}</div>
      {detail && (
        <p className={`relative mt-2 text-sm font-medium ${brand ? 'text-cream/80' : 'text-ink-faint'}`}>{detail}</p>
      )}
    </div>
  );
}
