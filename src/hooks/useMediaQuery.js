import { useEffect, useState } from 'react';

export function useMediaQuery(query) {
  const [matches, setMatches] = useState(() => window.matchMedia(query).matches);
  useEffect(() => {
    const media = window.matchMedia(query);
    const onChange = () => setMatches(media.matches);
    onChange();
    media.addEventListener('change', onChange);
    return () => media.removeEventListener('change', onChange);
  }, [query]);
  return matches;
}

/** Phones and portrait tablets: the public screen switches to a scrollable layout. */
export const useIsCompactScreen = () => useMediaQuery('(max-width: 767px), (max-aspect-ratio: 4/5)');
