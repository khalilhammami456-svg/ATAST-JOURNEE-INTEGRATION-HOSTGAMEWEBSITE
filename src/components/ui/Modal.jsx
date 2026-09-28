import { useEffect, useId, useRef } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { X } from 'lucide-react';

const WIDTHS = { sm: 'max-w-md', md: 'max-w-xl', lg: 'max-w-3xl', xl: 'max-w-5xl' };

const FOCUSABLE = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

export default function Modal({ open, onClose, title, description, size = 'md', children, footer, icon: Icon }) {
  const titleId = useId();
  const panelRef = useRef(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!open) return undefined;
    const previouslyFocused = document.activeElement;
    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.stopPropagation();
        onCloseRef.current();
      }
      if (event.key === 'Tab' && panelRef.current) {
        const focusables = [...panelRef.current.querySelectorAll(FOCUSABLE)].filter((el) => !el.disabled);
        if (focusables.length === 0) return;
        const first = focusables[0];
        const last = focusables.at(-1);
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener('keydown', onKeyDown);
    const focusTimer = setTimeout(() => {
      const autofocus =
        panelRef.current?.querySelector('[data-autofocus]') ??
        panelRef.current?.querySelector('input, select, textarea');
      (autofocus ?? panelRef.current)?.focus();
    }, 60);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      clearTimeout(focusTimer);
      document.body.style.overflow = '';
      previouslyFocused?.focus?.();
    };
  }, [open]);

  return createPortal(
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-end justify-center p-0 sm:items-center sm:p-6">
          <motion.div
            className="absolute inset-0 bg-[#14080C]/60 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            ref={panelRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            tabIndex={-1}
            className={`relative flex max-h-[92vh] w-full ${WIDTHS[size]} flex-col overflow-hidden rounded-t-3xl bg-surface-raised text-ink shadow-lift outline-none sm:rounded-3xl`}
            initial={{ opacity: 0, y: 40, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 30, scale: 0.97 }}
            transition={{ type: 'spring', stiffness: 380, damping: 32 }}
          >
            <div className="h-1.5 w-full bg-brand" />
            <header className="flex items-start gap-4 px-6 pb-2 pt-5">
              {Icon && (
                <span className="mt-0.5 grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-brand/10 text-brand">
                  <Icon size={22} strokeWidth={2.4} />
                </span>
              )}
              <div className="min-w-0 flex-1">
                <h2 id={titleId} className="text-2xl font-extrabold uppercase tracking-tight">
                  {title}
                </h2>
                {description && <p className="mt-1 text-ink-soft">{description}</p>}
              </div>
              <button
                type="button"
                onClick={onClose}
                className="grid h-10 w-10 place-items-center rounded-xl text-ink-soft hover:bg-ink/5 hover:text-ink"
                aria-label="Fermer"
              >
                <X size={22} />
              </button>
            </header>
            <div className="scrollbar-thin flex-1 overflow-y-auto px-6 py-4">{children}</div>
            {footer && (
              <footer className="flex flex-wrap items-center justify-end gap-3 border-t border-line bg-surface-sunken/60 px-6 py-4">
                {footer}
              </footer>
            )}
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body,
  );
}
