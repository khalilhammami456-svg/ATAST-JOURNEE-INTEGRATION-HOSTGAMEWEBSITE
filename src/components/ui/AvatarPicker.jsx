import { useEffect, useState } from 'react';
import { Check, Shuffle, Type } from 'lucide-react';
import { AVATAR_CATEGORIES, getAvatar, randomAvatarId } from '../../data/avatars';
import { readableTextOn } from '../../utils/color';
import { initials } from '../../utils/format';

const categoryOf = (avatarId) =>
  AVATAR_CATEGORIES.find((category) => category.avatars.some((avatar) => avatar.id === avatarId))?.id;

/**
 * Grid of built-in avatars, previewed in the team's color.
 * `value` is an avatar id, or null for "initiales".
 */
export default function AvatarPicker({ value, onChange, color = '#C4073D', teamName = '', takenIds = [] }) {
  const [categoryId, setCategoryId] = useState(() => categoryOf(value) ?? AVATAR_CATEGORIES[0].id);

  // Follow the selected avatar when it changes from outside (form reset, editing another team).
  useEffect(() => {
    const home = categoryOf(value);
    if (home) setCategoryId(home);
  }, [value]);
  const category = AVATAR_CATEGORIES.find((item) => item.id === categoryId);
  const textColor = readableTextOn(color);
  const selected = getAvatar(value);

  const pickRandom = () => onChange(randomAvatarId([...takenIds, value]));

  const tileClass = (active) =>
    `relative grid aspect-square place-items-center rounded-2xl transition hover:scale-105 focus-visible:scale-105 ${
      active ? 'ring-4 ring-ink/80 ring-offset-2 ring-offset-surface-raised' : 'opacity-90 hover:opacity-100'
    }`;
  const tileStyle = { backgroundColor: color, color: textColor };

  return (
    <fieldset>
      <div className="mb-1.5 flex items-center justify-between gap-3">
        <legend className="label !mb-0">
          Avatar
          {selected && <span className="ml-2 normal-case tracking-normal text-ink-faint">· {selected.label}</span>}
        </legend>
        <button
          type="button"
          onClick={pickRandom}
          className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-sm font-bold uppercase text-brand hover:bg-brand/10"
        >
          <Shuffle size={15} /> Au hasard
        </button>
      </div>

      <div
        className="scrollbar-thin -mx-1 mb-3 flex gap-1.5 overflow-x-auto px-1 pb-1"
        role="tablist"
        aria-label="Catégories d'avatars"
      >
        {AVATAR_CATEGORIES.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={item.id === categoryId}
            onClick={() => setCategoryId(item.id)}
            className={`shrink-0 rounded-full px-3.5 py-1.5 text-sm font-bold transition ${
              item.id === categoryId ? 'bg-ink text-surface' : 'bg-surface-sunken text-ink-soft hover:text-ink'
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div
        className="grid grid-cols-6 gap-2 sm:grid-cols-8"
        role="radiogroup"
        aria-label={`Avatars : ${category.label}`}
      >
        <button
          type="button"
          role="radio"
          aria-checked={!value}
          aria-label="Initiales de l'équipe"
          title="Initiales"
          onClick={() => onChange(null)}
          className={`${tileClass(!value)} text-lg font-extrabold`}
          style={tileStyle}
        >
          {teamName.trim() ? initials(teamName) : <Type size={22} />}
          {!value && <SelectedMark />}
        </button>
        {category.avatars.map(({ id, label, icon: Icon }) => {
          const active = value === id;
          const taken = takenIds.includes(id) && !active;
          return (
            <button
              key={id}
              type="button"
              role="radio"
              aria-checked={active}
              aria-label={`${label}${taken ? ' (déjà utilisé)' : ''}`}
              title={taken ? `${label} — déjà utilisé par une autre équipe` : label}
              onClick={() => onChange(id)}
              className={`${tileClass(active)} ${taken ? 'opacity-40' : ''}`}
              style={{
                ...tileStyle,
                backgroundImage: 'linear-gradient(145deg, rgba(255,255,255,0.28), rgba(0,0,0,0.12))',
              }}
            >
              <Icon className="h-[55%] w-[55%]" strokeWidth={2.2} />
              {active && <SelectedMark />}
            </button>
          );
        })}
      </div>
      <p className="mt-2 text-sm text-ink-faint">
        L'avatar prend la couleur de l'équipe. Les avatars grisés sont déjà pris par une autre équipe.
      </p>
    </fieldset>
  );
}

function SelectedMark() {
  return (
    <span className="absolute -right-1.5 -top-1.5 grid h-6 w-6 place-items-center rounded-full bg-ink text-surface shadow">
      <Check size={14} strokeWidth={3.5} />
    </span>
  );
}
