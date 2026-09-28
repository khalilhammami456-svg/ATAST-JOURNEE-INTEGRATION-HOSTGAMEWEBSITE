/**
 * Elliptical orbits borrowed from the ATAST Club globe logo.
 * Rendered behind champions and hero titles.
 */
export default function OrbitRings({ className = '', color = '#F5921E', spinning = true }) {
  return (
    <div className={`pointer-events-none ${className}`} aria-hidden="true">
      <svg viewBox="0 0 400 400" className={`absolute inset-0 h-full w-full ${spinning ? 'animate-orbit' : ''}`}>
        <ellipse
          cx="200"
          cy="200"
          rx="190"
          ry="70"
          fill="none"
          stroke={color}
          strokeWidth="7"
          transform="rotate(-24 200 200)"
        />
        <circle cx="30" cy="265" r="9" fill={color} transform="rotate(-24 200 200)" />
      </svg>
      <svg
        viewBox="0 0 400 400"
        className={`absolute inset-0 h-full w-full opacity-80 ${spinning ? 'animate-orbit-reverse' : ''}`}
      >
        <ellipse
          cx="200"
          cy="200"
          rx="180"
          ry="62"
          fill="none"
          stroke={color}
          strokeWidth="5"
          transform="rotate(32 200 200)"
        />
      </svg>
    </div>
  );
}
