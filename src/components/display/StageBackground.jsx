/** Crimson stage background shared by the public screen and the home page. */
import Ribbons from '../ui/Ribbons';

export default function StageBackground({ intensity = 'soft', dramatic = false }) {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
      <div
        className="absolute inset-0 transition-colors duration-700"
        style={{
          background: dramatic
            ? 'radial-gradient(ellipse at 50% 30%, rgb(var(--brand)) 0%, rgb(var(--brand-deep)) 45%, rgb(var(--brand-night)) 100%)'
            : 'radial-gradient(ellipse at 30% 20%, rgb(var(--brand)) 0%, rgb(var(--brand)) 40%, rgb(var(--brand-deep)) 100%)',
        }}
      />
      {/* subtle dot grain for a printed, poster-like texture */}
      <div
        className="absolute inset-0 opacity-[0.07] mix-blend-overlay"
        style={{
          backgroundImage: 'radial-gradient(#fff 1px, transparent 1.2px)',
          backgroundSize: '6px 6px',
        }}
      />
      <Ribbons
        animated
        strokeWidth={intensity === 'strong' ? 44 : 34}
        spread={intensity === 'strong' ? 0.72 : 1}
        className={`absolute inset-0 h-full w-full ${intensity === 'strong' ? 'text-cream' : 'text-cream/[0.14]'}`}
      />
    </div>
  );
}
