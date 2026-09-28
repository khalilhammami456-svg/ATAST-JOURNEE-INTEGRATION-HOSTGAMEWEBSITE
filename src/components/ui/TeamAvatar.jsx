import { initials } from '../../utils/format';
import { readableTextOn } from '../../utils/color';
import { getAvatar } from '../../data/avatars';

const SIZES = {
  xs: 'h-8 w-8 text-xs rounded-lg',
  sm: 'h-10 w-10 text-sm rounded-xl',
  md: 'h-14 w-14 text-lg rounded-2xl',
  lg: 'h-20 w-20 text-2xl rounded-3xl',
  xl: 'h-28 w-28 text-4xl rounded-[2rem]',
  '2xl': 'h-40 w-40 text-6xl rounded-[2.5rem]',
};

/** Team badge: chosen avatar icon, else a legacy uploaded logo, else the team initials. */
export default function TeamAvatar({ team, size = 'md', className = '', ring = false }) {
  const color = team.color ?? '#C4073D';
  const avatar = getAvatar(team.avatar);
  const showLogo = !avatar && team.logo;
  const Icon = avatar?.icon;

  return (
    <span
      className={`relative grid shrink-0 place-items-center overflow-hidden font-extrabold uppercase tracking-tight ${SIZES[size]} ${className}`}
      style={{
        backgroundColor: showLogo ? '#fff' : color,
        backgroundImage: showLogo ? undefined : 'linear-gradient(145deg, rgba(255,255,255,0.28), rgba(0,0,0,0.12))',
        color: readableTextOn(color),
        boxShadow: ring ? `0 0 0 4px rgba(255,255,255,0.9), 0 0 32px 6px ${color}88` : undefined,
      }}
      aria-hidden="true"
    >
      {Icon ? (
        <Icon className="h-[58%] w-[58%]" strokeWidth={2.2} />
      ) : showLogo ? (
        <img src={team.logo} alt="" className="h-full w-full object-cover" />
      ) : (
        initials(team.name)
      )}
    </span>
  );
}
