import { useEffect, useRef, useState } from 'react';
import { useAnimatedNumber } from '../../hooks/useAnimatedNumber';
import { formatPoints } from '../../utils/format';

/** Animated counter that also flashes green/orange when the value goes up/down. */
export default function AnimatedNumber({ value, className = '', flash = true }) {
  const displayed = useAnimatedNumber(value);
  const previous = useRef(value);
  const [direction, setDirection] = useState(null);

  useEffect(() => {
    if (value === previous.current) return undefined;
    setDirection(value > previous.current ? 'up' : 'down');
    previous.current = value;
    const timer = setTimeout(() => setDirection(null), 1100);
    return () => clearTimeout(timer);
  }, [value]);

  const flashClass = !flash || !direction ? '' : direction === 'up' ? 'text-[#12B886]' : 'text-orbit';

  return (
    <span className={`tabular inline-block transition-colors duration-500 ${flashClass} ${className}`}>
      {formatPoints(displayed)}
    </span>
  );
}
