/** Sunset villa-inspired stage background matching the provided tropical fantasy reference. */
import Ribbons from '../ui/Ribbons';

export default function StageBackground({ intensity = 'soft', dramatic = false }) {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
      <div
        className="absolute inset-0 transition-colors duration-700"
        style={{
          background: dramatic
            ? 'radial-gradient(ellipse at 50% 28%, rgba(255,182,86,0.85) 0%, rgba(181,63,72,0.88) 23%, rgba(48,19,35,0.96) 56%, rgba(14,9,17,1) 100%)'
            : 'linear-gradient(180deg, rgba(14,18,35,0.6) 0%, rgba(54,26,35,0.45) 22%, rgba(123,50,49,0.62) 42%, rgba(243,141,80,0.82) 62%, rgba(57,23,18,0.94) 100%), radial-gradient(circle at 20% 15%, rgba(255,221,146,0.9) 0%, rgba(255,166,94,0.48) 20%, transparent 38%), radial-gradient(circle at 78% 18%, rgba(89,129,255,0.38) 0%, transparent 28%)',
        }}
      />

      <div
        className="absolute inset-0 opacity-90"
        style={{
          background:
            'radial-gradient(circle at 15% 75%, rgba(39,145,88,0.6) 0%, transparent 18%), radial-gradient(circle at 68% 78%, rgba(179,65,93,0.56) 0%, transparent 18%), radial-gradient(circle at 50% 100%, rgba(255,210,120,0.28) 0%, transparent 28%)',
        }}
      />

      <div
        className="absolute inset-0 opacity-[0.09] mix-blend-overlay"
        style={{
          backgroundImage: 'radial-gradient(#fff 1px, transparent 1.2px)',
          backgroundSize: '6px 6px',
        }}
      />

      <div className="absolute -left-12 top-20 h-64 w-64 rounded-full bg-[#8d4f32]/25 blur-3xl" />
      <div className="absolute -right-10 bottom-12 h-72 w-72 rounded-full bg-[#ffb255]/20 blur-3xl" />
      <div className="absolute bottom-0 left-1/2 h-56 w-[85%] -translate-x-1/2 rounded-t-[50%] bg-[radial-gradient(circle_at_center,rgba(255,218,142,0.3),transparent_60%)]" />

      <Ribbons
        animated
        strokeWidth={intensity === 'strong' ? 44 : 34}
        spread={intensity === 'strong' ? 0.72 : 1}
        className={`absolute inset-0 h-full w-full ${intensity === 'strong' ? 'text-amber-50/80' : 'text-cream/[0.14]'}`}
      />
    </div>
  );
}
