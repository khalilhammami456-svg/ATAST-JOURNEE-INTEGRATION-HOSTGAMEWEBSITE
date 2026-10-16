import { ExternalLink, Gamepad2, LayoutGrid, ListOrdered, Radio, Trophy } from 'lucide-react';
import PageHeader from '../../components/admin/PageHeader';
import Button from '../../components/ui/Button';
import { useAppState } from '../../store/hooks';
import { setDisplayView, startPodiumCeremony } from '../../store/actions';
import { isFirebaseConfigured } from '../../store/firebaseConfig';

const VIEWS = [
  { id: 'podium', label: 'Podium', icon: Trophy, text: 'Cérémonie : 3e, 2e puis le champion, avec confettis.' },
  { id: 'leaderboard', label: 'Classement', icon: ListOrdered, text: 'Toutes les équipes, mises à jour en direct.' },
  { id: 'teams', label: 'Équipes', icon: LayoutGrid, text: 'Une carte par équipe avec score et rang.' },
  {
    id: 'games',
    label: 'Mini-jeux',
    icon: Gamepad2,
    text: 'La liste des mini-jeux disponibles, pour que les participants choisissent eux-mêmes.',
  },
];

const SHORTCUTS = [
  ['P', 'Podium'],
  ['L', 'Classement'],
  ['E', 'Équipes'],
  ['G', 'Mini-jeux'],
  ['F', 'Plein écran'],
  ['R', 'Rejouer le podium'],
  ['Échap', 'Quitter le plein écran'],
];

export default function ScreenControl() {
  const { display } = useAppState();

  const selectView = (view) => (view === 'podium' ? startPodiumCeremony() : setDisplayView(view));

  return (
    <>
      <PageHeader
        eyebrow="Mode live"
        title="Mode écran"
        description="Ouvrez l'écran public dans une nouvelle fenêtre, glissez-la sur le projecteur et passez-la en plein écran (touche F). Tout ce que vous modifiez ici s'y affiche instantanément."
        actions={
          <Button size="lg" icon={ExternalLink} onClick={() => window.open(`${import.meta.env.BASE_URL}display`, 'journee-integration-display')}>
            Ouvrir l'écran public
          </Button>
        }
      />

      <section aria-labelledby="remote-title">
        <h2 id="remote-title" className="mb-4 flex items-center gap-2 text-2xl font-extrabold uppercase">
          <Radio size={22} className="text-brand" /> Télécommande
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {VIEWS.map(({ id, label, icon: Icon, text }) => {
            const active = display.view === id;
            return (
              <button
                key={id}
                type="button"
                onClick={() => selectView(id)}
                aria-pressed={active}
                className={`group relative overflow-hidden rounded-3xl p-6 text-left transition hover:-translate-y-1 ${
                  active ? 'on-brand bg-brand text-cream shadow-lift' : 'card hover:shadow-lift'
                }`}
              >
                {active && (
                  <span className="absolute right-4 top-4 flex items-center gap-1.5 rounded-full bg-cream px-2.5 py-1 text-xs font-extrabold uppercase text-brand">
                    <span className="h-2 w-2 animate-pulse rounded-full bg-brand" /> À l'écran
                  </span>
                )}
                <Icon size={40} strokeWidth={2.2} className={active ? 'text-cream' : 'text-brand'} />
                <p className="mt-4 text-3xl font-extrabold uppercase">{label}</p>
                <p className={`mt-1 ${active ? 'text-cream/80' : 'text-ink-soft'}`}>{text}</p>
                {id === 'podium' && (
                  <p className={`mt-3 text-sm font-bold uppercase ${active ? 'text-cream' : 'text-brand'}`}>
                    {active ? '↻ Cliquer pour rejouer la cérémonie' : '▶ Lance la cérémonie'}
                  </p>
                )}
              </button>
            );
          })}
        </div>
      </section>

      <div className="mt-10 grid gap-6 lg:grid-cols-2">
        <section className="card p-6" aria-labelledby="shortcuts-title">
          <h2 id="shortcuts-title" className="mb-4 text-lg font-extrabold uppercase">
            Raccourcis clavier (sur l'écran public)
          </h2>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-3">
            {SHORTCUTS.map(([key, label]) => (
              <div key={key} className="flex items-center gap-3">
                <dt>
                  <kbd className="inline-grid h-9 min-w-[2.25rem] place-items-center rounded-lg border-2 border-b-4 border-line bg-surface-sunken px-2 font-extrabold">
                    {key}
                  </kbd>
                </dt>
                <dd className="font-semibold text-ink-soft">{label}</dd>
              </div>
            ))}
          </dl>
        </section>
        <section className="card p-6" aria-labelledby="tips-title">
          <h2 id="tips-title" className="mb-4 text-lg font-extrabold uppercase">
            Bon à savoir
          </h2>
          <ul className="list-disc space-y-2 pl-5 text-ink-soft">
            {isFirebaseConfigured ? (
              <>
                <li>La synchronisation est activée : chaque animateur peut ouvrir l'admin sur son propre téléphone ou ordinateur, les scores se mettent à jour partout en direct.</li>
                <li>Une connexion Internet est nécessaire sur chaque appareil pour envoyer et recevoir les changements.</li>
              </>
            ) : (
              <>
                <li>L'écran public et l'admin doivent être ouverts dans le même navigateur, sur le même ordinateur.</li>
                <li>Aucune connexion Internet n'est nécessaire : tout est enregistré sur cet ordinateur.</li>
              </>
            )}
            <li>L'écran public n'affiche aucun bouton d'administration.</li>
            <li>Pensez à exporter une sauvegarde JSON dans Paramètres avant et après l'événement.</li>
          </ul>
        </section>
      </div>
    </>
  );
}
