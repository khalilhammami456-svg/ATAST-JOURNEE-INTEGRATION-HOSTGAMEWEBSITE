import { forwardRef } from 'react';
import { Link } from 'react-router-dom';

const VARIANTS = {
  primary:
    'bg-brand text-cream shadow-[0_6px_0_0_rgb(var(--brand-deep))] hover:brightness-110 active:translate-y-[3px] active:shadow-[0_3px_0_0_rgb(var(--brand-deep))]',
  secondary:
    'bg-surface-raised text-ink border-2 border-line hover:border-brand/50 hover:text-brand active:translate-y-px',
  ghost: 'text-ink-soft hover:bg-ink/5 hover:text-ink',
  danger:
    'bg-[#B3122E] text-white shadow-[0_6px_0_0_#6f0a1c] hover:brightness-110 active:translate-y-[3px] active:shadow-[0_3px_0_0_#6f0a1c]',
  light:
    'bg-cream text-brand shadow-[0_6px_0_0_rgb(0_0_0/0.25)] hover:bg-white active:translate-y-[3px] active:shadow-[0_3px_0_0_rgb(0_0_0/0.25)]',
  outlineLight: 'border-2 border-cream/70 text-cream hover:bg-cream/10 active:translate-y-px',
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
