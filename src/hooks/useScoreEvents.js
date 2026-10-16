import { useEffect, useRef } from 'react';
import { useAppState } from '../store/hooks';

/** Calls `handler(event)` each time a new score event is published (from any tab). */
export function useScoreEvents(handler) {
  const { lastEvent } = useAppState();
  const seenId = useRef(lastEvent?.id ?? null);
  const handlerRef = useRef(handler);
  handlerRef.current = handler;

  useEffect(() => {
    if (!lastEvent || lastEvent.id === seenId.current) return;
    seenId.current = lastEvent.id;
    // Ignore stale events replayed when a tab opens long after the change.
    if (Date.now() - lastEvent.at > 10_000) return;
    handlerRef.current(lastEvent);
  }, [lastEvent]);
}
