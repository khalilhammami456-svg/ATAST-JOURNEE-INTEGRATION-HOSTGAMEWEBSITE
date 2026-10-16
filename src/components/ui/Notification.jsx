import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { AlertTriangle, Check, Crown, Info, TrendingDown, X } from 'lucide-react';
import { onStorageError } from '../../store/store';

const NotificationContext = createContext(null);

const STYLES = {
  success: { icon: Check, accent: 'bg-[#12B886]' },
  gain: { icon: Check, accent: 'bg-[#12B886]' },
  loss: { icon: TrendingDown, accent: 'bg-orbit' },
  leader: { icon: Crown, accent: 'bg-gold' },
  error: { icon: AlertTriangle, accent: 'bg-brand' },
  info: { icon: Info, accent: 'bg-globe' },
};

let nextId = 0;

export function NotificationProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const timers = useRef(new Map());

  const dismiss = useCallback((id) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
    clearTimeout(timers.current.get(id));
    timers.current.delete(id);
  }, []);

  const notify = useCallback(
    (message, { type = 'success', duration = type === 'error' ? 5000 : 3200 } = {}) => {
      const id = ++nextId;
      setToasts((current) => [...current.slice(-3), { id, message, type }]);
      timers.current.set(
        id,
        setTimeout(() => dismiss(id), duration),
      );
      return id;
    },
    [dismiss],
  );

  useEffect(() => onStorageError((message) => notify(message, { type: 'error' })), [notify]);

  return (
    <NotificationContext.Provider value={notify}>
      {children}
      <div
        className="pointer-events-none fixed inset-x-0 bottom-4 z-[60] flex flex-col items-center gap-2 px-4 sm:inset-x-auto sm:right-6 sm:items-end"
        aria-live="polite"
        role="status"
      >
        <AnimatePresence initial={false}>
          {toasts.map(({ id, message, type }) => {
            const { icon: Icon, accent } = STYLES[type] ?? STYLES.info;
            return (
              <motion.div
                key={id}
                layout
                initial={{ opacity: 0, y: 24, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, x: 60, transition: { duration: 0.2 } }}
                className="pointer-events-auto flex w-full max-w-sm items-center gap-3 overflow-hidden rounded-2xl bg-[#1D0F14] py-3 pl-3 pr-2 text-cream shadow-lift"
              >
                <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-xl text-[#1D0F14] ${accent}`}>
                  <Icon size={19} strokeWidth={2.8} />
                </span>
                <p className="flex-1 font-semibold leading-snug">{message}</p>
                <button
                  type="button"
                  onClick={() => dismiss(id)}
                  className="grid h-8 w-8 place-items-center rounded-lg text-cream/60 hover:bg-white/10 hover:text-cream"
                  aria-label="Fermer la notification"
                >
                  <X size={16} />
                </button>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </NotificationContext.Provider>
  );
}

export const useNotify = () => useContext(NotificationContext);
