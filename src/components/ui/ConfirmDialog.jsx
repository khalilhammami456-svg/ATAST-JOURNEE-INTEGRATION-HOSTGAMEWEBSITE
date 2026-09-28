import { createContext, useCallback, useContext, useRef, useState } from 'react';
import { AlertTriangle } from 'lucide-react';
import Modal from './Modal';
import Button from './Button';

const ConfirmContext = createContext(null);

/**
 * Promise-based confirmation dialog:
 *   const confirm = useConfirm();
 *   if (await confirm({ title, message, confirmLabel, danger: true })) { ... }
 * `typeToConfirm` forces the user to type a word for very destructive actions.
 */
export function ConfirmProvider({ children }) {
  const [request, setRequest] = useState(null);
  const [typed, setTyped] = useState('');
  const resolver = useRef(null);

  const confirm = useCallback((options) => {
    setTyped('');
    setRequest(options);
    return new Promise((resolve) => {
      resolver.current = resolve;
    });
  }, []);

  const close = useCallback((result) => {
    resolver.current?.(result);
    resolver.current = null;
    setRequest(null);
  }, []);

  const needsTyping = Boolean(request?.typeToConfirm);
  const canConfirm = !needsTyping || typed.trim().toUpperCase() === request.typeToConfirm;

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      <Modal
        open={Boolean(request)}
        onClose={() => close(false)}
        title={request?.title ?? ''}
        icon={request?.danger ? AlertTriangle : undefined}
        size="sm"
        footer={
          <>
            <Button variant="secondary" onClick={() => close(false)} data-autofocus={!needsTyping || undefined}>
              {request?.cancelLabel ?? 'Annuler'}
            </Button>
            <Button variant={request?.danger ? 'danger' : 'primary'} disabled={!canConfirm} onClick={() => close(true)}>
              {request?.confirmLabel ?? 'Confirmer'}
            </Button>
          </>
        }
      >
        <div className="space-y-4 text-lg leading-relaxed text-ink-soft">
          {typeof request?.message === 'string' ? <p>{request.message}</p> : request?.message}
          {needsTyping && (
            <label className="block">
              <span className="label">
                Tapez <strong className="text-brand">{request.typeToConfirm}</strong> pour confirmer
              </span>
              <input
                className="field uppercase"
                value={typed}
                onChange={(event) => setTyped(event.target.value)}
                onKeyDown={(event) => event.key === 'Enter' && canConfirm && close(true)}
                autoComplete="off"
                data-autofocus
              />
            </label>
          )}
        </div>
      </Modal>
    </ConfirmContext.Provider>
  );
}

export const useConfirm = () => useContext(ConfirmContext);
