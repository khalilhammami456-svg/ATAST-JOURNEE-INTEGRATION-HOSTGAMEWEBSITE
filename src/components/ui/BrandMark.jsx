import { useSettings } from '../../store/hooks';

export const DEFAULT_LOGO = `${import.meta.env.BASE_URL}brand/atast-club.png`;

/** Event logo on a cream tile — the uploaded one from Paramètres, or the ATAST Club globe. */
export default function BrandMark({ className = 'h-12 w-12', padding = 'p-1.5' }) {
  const { logo, eventName } = useSettings();
  return (
    <span className={`grid shrink-0 place-items-center overflow-hidden rounded-2xl bg-cream ${padding} ${className}`}>
      <img src={logo || DEFAULT_LOGO} alt={eventName} className="h-full w-full object-contain" />
    </span>
  );
}
