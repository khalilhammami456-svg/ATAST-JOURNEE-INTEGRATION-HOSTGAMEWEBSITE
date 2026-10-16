import { forwardRef } from 'react';
import { Link } from 'react-router-dom';

const VARIANTS = {
  primary:
    'bg-[linear-gradient(135deg,#d85a45_0%,#ef9462_36%,#c64f3a_100%)] text-white shadow-[0_6px_0_0_#8a2d1d] hover:brightness-105 active:translate-y-[3px] active:shadow-[0_3px_0_0_#8a2d1d]',
  secondary:
    'border-2 border-[#e9c7a1] bg-[#fffaf4] text-brand shadow-[0_4px_0_0_rgba(168,80,52,0.12)] hover:border-[#d98a63] hover:bg-[#fff3ea] active:translate-y-px',
  ghost: 'text-ink-soft hover:bg-[#f4d8bc]/40 hover:text-brand',
  danger:
    'bg-[linear-gradient(135deg,#b01d2d_0%,#d64c4b_100%)] text-white shadow-[0_6px_0_0_#6f0a1c] hover:brightness-110 active:translate-y-[3px] active:shadow-[0_3px_0_0_#6f0a1c]',
  light:
    'bg-[#fff4eb] text-brand shadow-[0_6px_0_0_rgba(102,52,37,0.14)] hover:bg-white active:translate-y-[3px] active:shadow-[0_3px_0_0_rgba(102,52,37,0.14)]',
  outlineLight: 'border-2 border-[#fff4eb] bg-white/10 text-white hover:bg-[#fff4eb]/10 active:translate-y-px',
};

const SIZES = {
  sm: 'h-9 px-3 text-sm gap-1.5 rounded-lg',
  md: 'h-11 px-5 text-base gap-2 rounded-xl',
  lg: 'h-14 px-7 text-lg gap-2.5 rounded-xl',
  xl: 'h-16 px-9 text-xl gap-3 rounded-2xl',
  icon: 'h-11 w-11 rounded-xl',
  'icon-sm': 'h-9 w-9 rounded-lg',
};

const Button = forwardRef(function Button(
  {
    variant = 'primary',
    size = 'md',
    icon: Icon,
    iconRight: IconRight,
    className = '',
    children,
    type = 'button',
    to,
    ...props
  },
  ref,
) {
  const iconSize = size === 'xl' ? 24 : size === 'lg' ? 22 : size === 'sm' || size === 'icon-sm' ? 16 : 19;
  const classes = `inline-flex shrink-0 select-none items-center justify-center font-bold uppercase tracking-wide transition-all duration-150 disabled:pointer-events-none disabled:opacity-45 ${VARIANTS[variant]} ${SIZES[size]} ${className}`;
  const content = (
    <>
      {Icon && <Icon size={iconSize} strokeWidth={2.4} aria-hidden="true" />}
      {children}
      {IconRight && <IconRight size={iconSize} strokeWidth={2.4} aria-hidden="true" />}
    </>
  );

  if (to) {
    return (
      <Link ref={ref} to={to} className={classes} {...props}>
        {content}
      </Link>
    );
  }
  return (
    <button ref={ref} type={type} className={classes} {...props}>
      {content}
    </button>
  );
});

export default Button;
