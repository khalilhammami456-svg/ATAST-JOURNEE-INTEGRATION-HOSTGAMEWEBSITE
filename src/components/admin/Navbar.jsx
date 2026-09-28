import { useEffect, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { Menu, X, Zap } from 'lucide-react';
import { useSettings } from '../../store/hooks';
import BrandMark from '../ui/BrandMark';
import { NAV_ITEMS } from './navItems';

/** Top bar + slide-in drawer used below the `lg` breakpoint (tablet / phone). */
export default function Navbar({ onAddPoints }) {
  const { eventName, year } = useSettings();
  const [open, setOpen] = useState(false);
  const location = useLocation();

  useEffect(() => setOpen(false), [location.pathname]);

  return (
    <>
      <header className="on-brand sticky top-0 z-30 flex h-16 items-center gap-3 bg-brand px-4 text-cream shadow-lift lg:hidden">
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="grid h-11 w-11 place-items-center rounded-xl hover:bg-cream/10"
          aria-label="Ouvrir le menu"
          aria-expanded={open}
        >
          <Menu size={24} />
        </button>
        <BrandMark className="h-10 w-10" padding="p-1" />
        <p className="min-w-0 flex-1 truncate text-lg font-extrabold uppercase">
          {eventName} <span className="text-cream/70">{year}</span>
        </p>
        <button
          type="button"
          onClick={onAddPoints}
          className="flex h-11 items-center gap-1.5 rounded-xl bg-cream px-4 font-extrabold uppercase text-brand"
        >
          <Zap size={18} /> Points
        </button>
      </header>

      <AnimatePresence>
        {open && (
          <div className="fixed inset-0 z-40 lg:hidden">
            <motion.div
              className="absolute inset-0 bg-[#14080C]/60"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setOpen(false)}
            />
            <motion.nav
              className="on-brand absolute inset-y-0 left-0 flex w-72 max-w-[85vw] flex-col bg-brand p-4 text-cream"
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'spring', stiffness: 400, damping: 40 }}
              aria-label="Navigation administrateur"
            >
              <div className="mb-4 flex items-center justify-between">
                <BrandMark className="h-11 w-11" />
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  className="grid h-11 w-11 place-items-center rounded-xl hover:bg-cream/10"
                  aria-label="Fermer le menu"
                >
                  <X size={24} />
                </button>
              </div>
              <div className="space-y-1">
                {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
                  <NavLink
                    key={to}
                    to={to}
                    end={end}
                    className={({ isActive }) =>
                      `flex h-12 items-center gap-3 rounded-xl px-4 font-bold uppercase ${
                        isActive ? 'bg-cream text-brand' : 'text-cream/85 hover:bg-cream/10'
                      }`
                    }
                  >
                    <Icon size={20} /> {label}
                  </NavLink>
                ))}
              </div>
              <button
                type="button"
                onClick={() => {
                  setOpen(false);
                  onAddPoints();
                }}
                className="mt-auto flex h-14 items-center justify-center gap-2 rounded-2xl bg-cream text-lg font-extrabold uppercase text-brand"
              >
                <Zap size={20} /> Ajouter des points
              </button>
            </motion.nav>
          </div>
        )}
      </AnimatePresence>
    </>
  );
}
