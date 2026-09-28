import { Check } from 'lucide-react';
import { TEAM_COLOR_PRESETS } from '../../utils/color';

export default function ColorPicker({ value, onChange, label = 'Couleur' }) {
  return (
    <fieldset>
      <legend className="label">{label}</legend>
      <div className="flex flex-wrap items-center gap-2">
        {TEAM_COLOR_PRESETS.map((color) => {
          const selected = value?.toLowerCase() === color.toLowerCase();
          return (
            <button
              key={color}
              type="button"
              onClick={() => onChange(color)}
              className={`grid h-10 w-10 place-items-center rounded-xl transition hover:scale-110 ${
                selected ? 'ring-4 ring-ink/80 ring-offset-2 ring-offset-surface-raised' : ''
              }`}
              style={{ backgroundColor: color }}
              aria-label={`Couleur ${color}`}
              aria-pressed={selected}
            >
              {selected && <Check size={18} strokeWidth={3.5} className="text-white drop-shadow" />}
            </button>
          );
        })}
        <label className="relative grid h-10 w-10 cursor-pointer place-items-center overflow-hidden rounded-xl border-2 border-dashed border-line text-xs font-bold text-ink-soft hover:border-brand">
          <span aria-hidden="true">+</span>
          <input
            type="color"
            value={value ?? '#C4073D'}
            onChange={(event) => onChange(event.target.value)}
            className="absolute inset-0 cursor-pointer opacity-0"
            aria-label="Couleur personnalisée"
          />
        </label>
      </div>
    </fieldset>
  );
}
