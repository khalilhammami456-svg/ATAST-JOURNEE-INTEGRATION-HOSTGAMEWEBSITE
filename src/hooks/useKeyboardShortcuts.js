import { useEffect, useRef } from 'react';

const isTyping = (target) =>
  target instanceof HTMLElement &&
  (target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName));

/**
 * Single-key shortcuts (no modifier). Ignored while typing in a field
 * or when a dialog is open, so they never get in the way.
 */
export function useKeyboardShortcuts(bindings, enabled = true) {
  const bindingsRef = useRef(bindings);
  bindingsRef.current = bindings;

  useEffect(() => {
    if (!enabled) return undefined;
    const onKeyDown = (event) => {
      if (event.ctrlKey || event.metaKey || event.altKey || isTyping(event.target)) return;
      if (document.querySelector('[role="dialog"]')) return;
      const action = bindingsRef.current[event.key.toLowerCase()];
      if (action) {
        event.preventDefault();
        action(event);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [enabled]);
}
