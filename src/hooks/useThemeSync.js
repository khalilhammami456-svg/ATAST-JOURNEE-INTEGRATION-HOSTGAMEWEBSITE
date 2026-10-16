import { useEffect } from 'react';
import { useSettings } from '../store/hooks';
import { applyBrandColor } from '../utils/color';

/** Mirrors theme settings (brand color, dark mode, animations) onto <html>. */
export function useThemeSync() {
  const { primaryColor, darkMode, animations, eventName, year } = useSettings();

  useEffect(() => applyBrandColor(primaryColor), [primaryColor]);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode);
  }, [darkMode]);

  useEffect(() => {
    document.documentElement.classList.toggle('no-motion', !animations);
  }, [animations]);

  useEffect(() => {
    const title = [eventName, year].filter(Boolean).join(' ');
    document.title = title || 'ATAST Student Section Academy 7.0';
  }, [eventName, year]);
}
