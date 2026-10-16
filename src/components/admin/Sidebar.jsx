import { NavLink } from 'react-router-dom';
import { ChevronsLeft, ChevronsRight, ExternalLink, Zap } from 'lucide-react';
import { useSettings } from '../../store/hooks';
import BrandMark from '../ui/BrandMark';
import { NAV_ITEMS } from './navItems';

export default function Sidebar({ collapsed, onToggle, onAddPoints }) {
  const { eventName, year } = useSettings();

  return (
    <aside
      className={`on-brand sticky top-0 hidden h-screen shrink-0 flex-col overflow-hidden bg-brand text-cream transition-[width] duration-300 lg:flex ${
        collapsed ? 'w-[5.5rem]' : 'w-72'
      }`}
    >
      <svg
        className="pointer-events-none absolute -bottom-10 -left-16 h-80 w-80 text-cream/10"
        viewBox="0 0 200 200"
        aria-hidden="true"
      >
        <path
          d="M10 190 C 40 120, 110 130, 140 70 C 160 30, 150 0, 150 -20"
          stroke="currentColor"
          strokeWidth="16"
          fill="none"
          strokeLinecap="round"
        />
        <path
          d="M-20 150 C 20 110, 60 100, 90 60"
          stroke="currentColor"
          strokeWidth="16"
          fill="none"
          strokeLinecap="round"
        />
      </svg>

      <NavLink to="/" className="relative flex items-center gap-3 px-5 pb-4 pt-6" title="Page d'accueil">
        <BrandMark className="h-12 w-12" />
        {!collapsed && (
          <span className="min-w-0 leading-tight">
            <span className="block text-base font-extrabold uppercase leading-tight">{eventName}</span>
            <span className="text-sm font-bold tracking-[0.25em] text-cream/70">{year}</span>
          </span>
        )}
      </NavLink>

      <div className="relative px-4 pb-3">
        <button
          type="button"
          onClick={onAddPoints}
          className={`flex h-14 w-full items-center justify-center gap-2 rounded-2xl bg-cream text-lg font-extrabold uppercase text-brand shadow-[0_5px_0_0_rgb(0_0_0/0.25)] transition hover:bg-white active:translate-y-[3px] active:shadow-[0_2px_0_0_rgb(0_0_0/0.25)]`}
          title="Ajouter des points"
        >
          <Zap size={22} strokeWidth={2.6} />
          {!collapsed && 'Points'}
        </button>
      </div>

      <nav className="relative flex-1 space-y-1 overflow-y-auto px-3 py-2" aria-label="Navigation administrateur">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end, external }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            target={external ? '_blank' : undefined}
            title={collapsed ? label : undefined}
            className={({ isActive }) =>
              `flex h-12 items-center gap-3 rounded-xl px-4 text-base font-bold uppercase tracking-wide transition ${
                isActive && !external
                  ? 'bg-cream/95 text-brand shadow-sm'
                  : 'text-cream/85 hover:bg-cream/10 hover:text-cream'
              } ${collapsed ? 'justify-center px-0' : ''}`
            }
          >
            <Icon size={21} strokeWidth={2.4} className="shrink-0" />
            {!collapsed && <span className="flex-1 truncate">{label}</span>}
            {!collapsed && external && <ExternalLink size={15} className="opacity-60" />}
          </NavLink>
        ))}
      </nav>

      <button
        type="button"
        onClick={onToggle}
        className="relative m-3 flex h-11 items-center justify-center gap-2 rounded-xl text-sm font-bold uppercase text-cream/70 hover:bg-cream/10 hover:text-cream"
        aria-label={collapsed ? 'Déplier la barre latérale' : 'Réduire la barre latérale'}
      >
        {collapsed ? <ChevronsRight size={20} /> : <ChevronsLeft size={20} />}
        {!collapsed && 'Réduire'}
      </button>
    </aside>
  );
}
