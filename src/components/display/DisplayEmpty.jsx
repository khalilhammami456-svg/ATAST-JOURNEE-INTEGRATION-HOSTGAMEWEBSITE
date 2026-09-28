import { Users } from 'lucide-react';
import { useSettings } from '../../store/hooks';

export default function DisplayEmpty() {
  const { eventName, year } = useSettings();
  return (
    <div className="flex h-full flex-col items-center justify-center gap-[2vh] text-center text-cream">
      <Users className="h-[10vh] w-[10vh] opacity-80" strokeWidth={1.8} />
      <p className="display-title" style={{ fontSize: 'clamp(2rem, 7vh, 6rem)' }}>
        {eventName} {year}
      </p>
      <p className="font-semibold text-cream/80" style={{ fontSize: 'clamp(1rem, 3vh, 2rem)' }}>
        Les équipes arrivent bientôt…
      </p>
    </div>
  );
}
