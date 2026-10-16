import { useSettings } from '../../store/hooks';

export const DEFAULT_LOGO = `${import.meta.env.BASE_URL}brand/atast-emblem.png`;

/** Red orbit ATAST emblem used across the site. */
export default function BrandMark({ className = 'h-12 w-12', padding = 'p-0' }) {
  const { logo, eventName } = useSettings();
  return (
    <span className={`grid shrink-0 place-items-center overflow-hidden rounded-full bg-transparent ${padding} ${className}`}>
      <img src={logo || DEFAULT_LOGO} alt={eventName} className="h-full w-full object-contain" />
    </span>
  );
}
