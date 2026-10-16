import { House } from 'lucide-react';
import StageBackground from '../components/display/StageBackground';
import Button from '../components/ui/Button';

export default function NotFound() {
  return (
    <div className="on-brand relative grid min-h-screen place-items-center overflow-hidden px-6 text-center text-cream">
      <StageBackground />
      <div className="relative">
        <p className="display-title text-[8rem] leading-none">404</p>
        <p className="mt-2 text-xl font-semibold text-cream/85">Cette page n'existe pas.</p>
        <Button variant="light" size="lg" icon={House} to="/" className="mt-8">
          Accueil
        </Button>
      </div>
    </div>
  );
}
