/** @type {import('tailwindcss').Config} */
const withAlpha = (variable) => `rgb(var(${variable}) / <alpha-value>)`;

export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: withAlpha('--brand'),
          deep: withAlpha('--brand-deep'),
          night: withAlpha('--brand-night'),
        },
        cream: '#F8F3EC',
        orbit: { DEFAULT: '#F5921E', soft: '#FFB861' },
        globe: { DEFAULT: '#1F6FE0', deep: '#0B2A6B' },
        gold: '#FFC83D',
        silver: '#D9DEE8',
        bronze: '#E08A4F',
        surface: {
          DEFAULT: withAlpha('--surface'),
          raised: withAlpha('--surface-raised'),
          sunken: withAlpha('--surface-sunken'),
        },
        ink: {
          DEFAULT: withAlpha('--ink'),
          soft: withAlpha('--ink-soft'),
          faint: withAlpha('--ink-faint'),
        },
        line: withAlpha('--line'),
      },
      fontFamily: {
        sans: ['"Saira Variable"', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        xl2: '1.25rem',
        blob: '2rem',
      },
      boxShadow: {
        card: '0 1px 0 rgb(var(--line) / 1), 0 8px 24px -12px rgb(20 8 12 / 0.25)',
        lift: '0 18px 40px -18px rgb(20 8 12 / 0.45)',
      },
      keyframes: {
        drift: {
          '0%, 100%': { transform: 'translate3d(0,0,0) rotate(0deg)' },
          '50%': { transform: 'translate3d(-2%,1.5%,0) rotate(-2deg)' },
        },
        orbit: { to: { transform: 'rotate(360deg)' } },
        shine: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        pulseRing: {
          '0%': { transform: 'scale(0.9)', opacity: '0.7' },
          '100%': { transform: 'scale(1.6)', opacity: '0' },
        },
      },
      animation: {
        drift: 'drift 18s ease-in-out infinite',
        'drift-slow': 'drift 28s ease-in-out infinite reverse',
        orbit: 'orbit 14s linear infinite',
        'orbit-reverse': 'orbit 20s linear infinite reverse',
        shine: 'shine 3.5s linear infinite',
        'pulse-ring': 'pulseRing 1.6s ease-out infinite',
      },
    },
  },
  plugins: [],
};
