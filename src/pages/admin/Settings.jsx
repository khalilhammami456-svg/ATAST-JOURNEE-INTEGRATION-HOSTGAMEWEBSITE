import { useRef, useState } from 'react';
import {
  Database,
  Download,
  FileJson,
  FileSpreadsheet,
  Palette,
  RotateCcw,
  Sparkles,
  Trash2,
  Upload,
} from 'lucide-react';
import PageHeader from '../../components/admin/PageHeader';
import Button from '../../components/ui/Button';
import Field from '../../components/ui/Field';
import ImageUpload from '../../components/ui/ImageUpload';
import { useConfirm } from '../../components/ui/ConfirmDialog';
import { useNotify } from '../../components/ui/Notification';
import { useAppState } from '../../store/hooks';
import { clearAllData, importData, loadDemoData, resetScores, updateSettings } from '../../store/actions';
import { exportCsv, exportJson, parseBackup } from '../../utils/exporters';
import { playSound } from '../../utils/sound';
import { isFirebaseConfigured } from '../../store/firebaseConfig';

const BRAND_PRESETS = ['#C4073D', '#1F6FE0', '#0B2A6B', '#F5921E', '#8B3DFF', '#12B886'];

function Toggle({ label, description, checked, onChange }) {
  return (
    <label className="flex cursor-pointer items-center justify-between gap-4 py-3">
      <span>
        <span className="block font-bold">{label}</span>
        {description && <span className="block text-sm text-ink-faint">{description}</span>}
      </span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative h-8 w-14 shrink-0 rounded-full transition ${checked ? 'bg-brand' : 'bg-line'}`}
      >
        <span
          className={`absolute top-1 h-6 w-6 rounded-full bg-white shadow transition-all ${checked ? 'left-7' : 'left-1'}`}
        />
      </button>
    </label>
  );
}

function Section({ icon: Icon, title, children }) {
  return (
    <section className="card p-6">
      <h2 className="mb-4 flex items-center gap-2 text-xl font-extrabold uppercase">
        <Icon size={22} className="text-brand" /> {title}
      </h2>
      {children}
    </section>
  );
}

export default function Settings() {
  const state = useAppState();
  const { settings } = state;
  const confirm = useConfirm();
  const notify = useNotify();
  const fileInput = useRef(null);
  const [yearDraft, setYearDraft] = useState(String(settings.year));
  const [yearError, setYearError] = useState('');

  const onImport = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    try {
      const data = parseBackup(await file.text());
      const ok = await confirm({
        title: 'Restaurer cette sauvegarde ?',
        message: `${data.teams.length} équipes et ${data.participants.length} participants vont REMPLACER toutes les données actuelles.`,
        confirmLabel: 'Restaurer',
        danger: true,
      });
      if (!ok) return;
      importData(data);
      notify('Sauvegarde restaurée.');
    } catch (error) {
      notify(error.message, { type: 'error' });
    }
  };

  const onResetScores = async () => {
    const ok = await confirm({
      title: 'Réinitialiser tous les scores ?',
      message:
        'Toutes les équipes repartent à 0 point et l’historique des scores est effacé. Les équipes, participants et mini-jeux sont conservés.',
      confirmLabel: 'Remettre à zéro',
      danger: true,
      typeToConfirm: 'ZERO',
    });
    if (ok) resetScores();
  };

  const onClearAll = async () => {
    const ok = await confirm({
      title: 'Effacer toutes les données ?',
      message:
        'Équipes, participants, mini-jeux et historique seront supprimés. Exportez une sauvegarde avant si besoin.',
      confirmLabel: 'Tout effacer',
      danger: true,
      typeToConfirm: 'EFFACER',
    });
    if (!ok) return;
    clearAllData();
    notify('Toutes les données ont été effacées.', { type: 'info' });
  };

  const onLoadDemo = async () => {
    const ok = await confirm({
      title: 'Charger les données de démonstration ?',
      message: '8 équipes fictives remplaceront les données actuelles.',
      confirmLabel: 'Charger la démo',
      danger: true,
    });
    if (!ok) return;
    loadDemoData();
    notify('Données de démonstration chargées.');
  };

  return (
    <>
      <PageHeader
        eyebrow="Configuration"
        title="Paramètres"
        description={
          isFirebaseConfigured
            ? 'Synchronisé automatiquement entre tous les appareils des animateurs.'
            : 'Tout est enregistré automatiquement sur cet ordinateur.'
        }
      />

      <div className="grid gap-6 xl:grid-cols-2">
        <Section icon={Palette} title="Événement & identité">
          <div className="space-y-5">
            <div className="grid gap-4 sm:grid-cols-[1fr_9rem]">
              <Field
                label="Nom de l'événement"
                value={settings.eventName}
                onChange={(event) => updateSettings({ eventName: event.target.value })}
                onBlur={(event) => !event.target.value.trim() && updateSettings({ eventName: "Journée d'Intégration" })}
              />
              <Field
                label="Année"
                type="number"
                value={yearDraft}
                error={yearError}
                onChange={(event) => {
                  setYearDraft(event.target.value);
                  const year = Number(event.target.value);
                  if (!Number.isInteger(year) || year < 2000 || year > 2100) {
                    setYearError('Année invalide.');
                    return;
                  }
                  setYearError('');
                  updateSettings({ year });
                }}
              />
            </div>
            <Field
              label="Organisateur (sous-titre)"
              value={settings.organizer}
              onChange={(event) => updateSettings({ organizer: event.target.value })}
            />
            <ImageUpload
              label="Logo de l'événement"
              value={settings.logo}
              onChange={(logo) => updateSettings({ logo })}
            />
            <fieldset>
              <legend className="label">Couleur principale</legend>
              <div className="flex flex-wrap items-center gap-2">
                {BRAND_PRESETS.map((color) => (
                  <button
                    key={color}
                    type="button"
                    onClick={() => updateSettings({ primaryColor: color })}
                    aria-pressed={settings.primaryColor.toLowerCase() === color.toLowerCase()}
                    aria-label={`Couleur ${color}`}
                    className={`h-11 w-11 rounded-xl transition hover:scale-110 ${
                      settings.primaryColor.toLowerCase() === color.toLowerCase()
                        ? 'ring-4 ring-ink/70 ring-offset-2 ring-offset-surface-raised'
                        : ''
                    }`}
                    style={{ backgroundColor: color }}
                  />
                ))}
                <input
                  type="color"
                  value={settings.primaryColor}
                  onChange={(event) => updateSettings({ primaryColor: event.target.value })}
                  className="h-11 w-16 cursor-pointer rounded-xl border-2 border-line bg-transparent"
                  aria-label="Couleur principale personnalisée"
                />
              </div>
              <p className="mt-2 text-sm text-ink-faint">Rouge ATAST par défaut : #C4073D.</p>
            </fieldset>
          </div>
        </Section>

        <Section icon={Sparkles} title="Affichage & effets">
          <div className="divide-y divide-line">
            <Toggle
              label="Mode sombre"
              description="Pour l'interface admin."
              checked={settings.darkMode}
              onChange={(darkMode) => updateSettings({ darkMode })}
            />
            <Toggle
              label="Animations"
              description="Compteurs, transitions, podium progressif."
              checked={settings.animations}
              onChange={(animations) => updateSettings({ animations })}
            />
            <Toggle
              label="Confettis"
              description="Au podium et lors d'un changement de leader."
              checked={settings.confetti}
              onChange={(confetti) => updateSettings({ confetti })}
            />
            <Toggle
              label="Son"
              description="Effets sonores discrets."
              checked={settings.sound}
              onChange={(sound) => {
                updateSettings({ sound });
                if (sound) playSound('gain');
              }}
            />
          </div>
        </Section>

        <Section icon={Database} title="Sauvegarde">
          <p className="mb-4 text-ink-soft">
            Exportez régulièrement : le fichier JSON permet de tout restaurer, même sur un autre ordinateur.
          </p>
          <div className="flex flex-wrap gap-3">
            <Button icon={FileJson} onClick={() => exportJson(state)}>
              Exporter (JSON)
            </Button>
            <Button variant="secondary" icon={FileSpreadsheet} onClick={() => exportCsv(state)}>
              Exporter (CSV)
            </Button>
            <Button variant="secondary" icon={Upload} onClick={() => fileInput.current?.click()}>
              Importer
            </Button>
            <input ref={fileInput} type="file" accept="application/json,.json" className="hidden" onChange={onImport} />
          </div>
          <p className="mt-3 flex items-center gap-1.5 text-sm text-ink-faint">
            <Download size={14} /> Le CSV produit 3 fichiers : classement, participants, historique.
          </p>
        </Section>

        <Section icon={Trash2} title="Zone sensible">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-surface-sunken/70 p-4">
              <div>
                <p className="font-bold">Réinitialiser les scores</p>
                <p className="text-sm text-ink-faint">Scores à 0, historique effacé.</p>
              </div>
              <Button variant="danger" size="sm" icon={RotateCcw} onClick={onResetScores}>
                Réinitialiser
              </Button>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-surface-sunken/70 p-4">
              <div>
                <p className="font-bold">Charger la démo</p>
                <p className="text-sm text-ink-faint">8 équipes fictives pour tester.</p>
              </div>
              <Button variant="secondary" size="sm" onClick={onLoadDemo}>
                Charger
              </Button>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-surface-sunken/70 p-4">
              <div>
                <p className="font-bold">Effacer toutes les données</p>
                <p className="text-sm text-ink-faint">Pour partir d'une page blanche le jour J.</p>
              </div>
              <Button variant="danger" size="sm" icon={Trash2} onClick={onClearAll}>
                Tout effacer
              </Button>
            </div>
          </div>
        </Section>
      </div>
    </>
  );
}
