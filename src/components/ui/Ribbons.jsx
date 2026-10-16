import { motion } from 'framer-motion';

/**
 * The flowing white ribbons from the ATAST Student Section identity:
 * one sweeping out of the top-left corner, one out of the bottom-right.
 * Uses currentColor so it can be tinted by the parent.
 */
export default function Ribbons({ className = '', strokeWidth = 34, animated = false, spread = 1 }) {
  const drawIn = animated
    ? {
        initial: { pathLength: 0 },
        animate: { pathLength: 1 },
        transition: { duration: 1.8, ease: [0.65, 0, 0.35, 1] },
      }
    : {};

  return (
    <svg
      className={className}
      viewBox="0 0 1600 900"
      preserveAspectRatio="xMidYMid slice"
      fill="none"
      aria-hidden="true"
    >
      <g transform={`scale(${spread})`}>
        <g className={animated ? 'origin-top-left animate-drift' : undefined}>
          <motion.path
            d="M-60 150 C 120 150, 250 120, 330 20 C 380 -40, 390 -80, 380 -120"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            {...drawIn}
          />
          <motion.path
            d="M-60 390 C 160 380, 300 330, 420 250 C 540 170, 560 60, 520 -40 C 500 -90, 480 -120, 470 -150"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            {...drawIn}
          />
        </g>
      </g>
      <g transform={`translate(${1600 * (1 - spread)} ${900 * (1 - spread)}) scale(${spread})`}>
        <g className={animated ? 'origin-bottom-right animate-drift-slow' : undefined}>
          <motion.path
            d="M1680 560 C 1500 560, 1340 610, 1250 720 C 1190 800, 1180 880, 1200 1000"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            {...drawIn}
          />
          <motion.path
            d="M1680 790 C 1560 780, 1470 810, 1420 880 C 1400 910, 1395 950, 1400 1000"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            {...drawIn}
          />
        </g>
      </g>
    </svg>
  );
}
