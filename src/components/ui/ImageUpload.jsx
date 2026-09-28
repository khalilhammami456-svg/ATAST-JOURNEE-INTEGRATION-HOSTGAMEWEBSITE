import { useRef, useState } from 'react';
import { ImagePlus, Trash2 } from 'lucide-react';
import { readImageAsDataUrl } from '../../utils/image';

export default function ImageUpload({ value, onChange, label = 'Logo', size = 256 }) {
  const inputRef = useRef(null);
  const [error, setError] = useState('');

  const onFile = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    try {
      setError('');
      onChange(await readImageAsDataUrl(file, size));
    } catch (uploadError) {
      setError(uploadError.message);
    }
  };

  return (
    <div>
      <span className="label">{label}</span>
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="grid h-20 w-20 shrink-0 place-items-center overflow-hidden rounded-2xl border-2 border-dashed border-line bg-surface-sunken text-ink-faint transition hover:border-brand hover:text-brand"
          aria-label={value ? `Changer ${label.toLowerCase()}` : `Importer ${label.toLowerCase()}`}
        >
          {value ? <img src={value} alt="" className="h-full w-full object-contain" /> : <ImagePlus size={28} />}
        </button>
        <div className="text-sm text-ink-soft">
          <p>PNG, JPG ou SVG — redimensionné automatiquement.</p>
          {value && (
            <button
              type="button"
              onClick={() => onChange(null)}
              className="mt-1 inline-flex items-center gap-1 font-bold text-brand hover:underline"
            >
              <Trash2 size={14} /> Retirer
            </button>
          )}
        </div>
        <input ref={inputRef} type="file" accept="image/*" className="hidden" onChange={onFile} />
      </div>
      {error && (
        <p className="mt-1.5 text-sm font-semibold text-brand" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
