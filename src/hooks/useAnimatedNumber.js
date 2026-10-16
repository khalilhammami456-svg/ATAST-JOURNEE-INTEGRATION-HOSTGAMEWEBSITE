import { useEffect, useRef, useState } from 'react';
import { useSettings } from '../store/hooks';

const easeOutCubic = (t) => 1 - (1 - t) ** 3;

/** Counts from the previous value to the new one (180 → 181 → … → 220). */
export function useAnimatedNumber(value, duration = 900) {
  const { animations } = useSettings();
  const [displayed, setDisplayed] = useState(value);
  const displayedRef = useRef(value);

  useEffect(() => {
    const from = displayedRef.current;
    if (!animations || from === value) {
      displayedRef.current = value;
      setDisplayed(value);
      return undefined;
    }
    const distance = value - from;
    const effectiveDuration = Math.min(duration + Math.abs(distance) * 4, 2200);
    const start = performance.now();
    let frame;
    const tick = (now) => {
      const progress = Math.min(1, (now - start) / effectiveDuration);
      const next = Math.round(from + distance * easeOutCubic(progress));
      displayedRef.current = next;
      setDisplayed(next);
      if (progress < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [value, animations, duration]);

  return displayed;
}
