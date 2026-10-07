/** Admin: paid subscriptions (cotisations) — Excel/CSV import with preview, manual entry, history. */
import { h, replace, nextId } from '../components/dom.js';
import { icon } from '../components/icons.js';
import {
  load, emptyState, pageHead, pagination, searchBox, statusPill, rowPill, toast, confirmDialog, openModal, withBusy,
  field, showErrors, clearErrors, formData, quietly,
} from '../components/ui.js';
import { onLive } from '../app/router.js';
import { api } from '../services/api.js';
import { refreshAdminCounts } from '../layouts/admin.js';
import {
  IMPORT_ROW_STATUS, currentSeason, seasonOptions, formatAmount, formatDate, formatDateTime, formatDay, relative, plural,
} from '../services/format.js';

const ACCEPT = '.xlsx,.csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/csv';
const downloadHref = (kind, params = {}) => {
  const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v));
  return `/api/admin/downloads/${kind}${qs.size ? `?${qs}` : ''}`;
};

export function subscriptionsPage({ query }) {
  const state = { season: seasonOptions().includes(query.season) ? query.season : currentSeason(), status: 'AVAILABLE', q: '', page: 1, batchPage: 1 };

  const importSlot = h('div', {});
  const list = h('div', { id: 'sub-panel', role: 'tabpanel' });
  const history = h('div', {});
  const tabs = h('div', { class: 'tabs', role: 'tablist', 'aria-label': 'Statut des cotisations' });
  const listTitle = h('h2', { id: 'sub-title' }, `Cotisations ${state.season}`);
  const exportLink = h('a', { class: 'btn btn--secondary', href: '#' }, icon('download'), 'Exporter');

  const seasonSelect = h('select', { class: 'select', id: 'season-select', 'aria-label': 'Saison' },
    seasonOptions().map((s) => h('option', { value: s, selected: s === state.season }, `Saison ${s}`)));
  seasonSelect.addEventListener('change', () => {
    state.season = seasonSelect.value;
    state.page = 1;
    listTitle.textContent = `Cotisations ${state.season}`;
    paintExport();
    refreshList();
    resetImport();
  });
  function paintExport() {
    exportLink.setAttribute('href', downloadHref('subscriptions', { season: state.season }));
  }

  // ------------------------------------------------------------ import
  function resetImport() {
    replace(importSlot, dropArea());
  }

  function dropArea() {
    const id = nextId('file');
    const input = h('input', { class: 'file-input', id, type: 'file', accept: ACCEPT, 'aria-describedby': `${id}-hint` });
    const zone = h('label', { class: 'dropzone', for: id },
      icon('upload'),
      h('b', 'Choisir un fichier Excel (.xlsx) ou CSV'),
      h('span', { id: `${id}-hint`, class: 'small' }, 'ou le déposer ici. Rien n’est enregistré avant votre confirmation.'));
    input.addEventListener('change', () => input.files[0] && preview(input.files[0]));
    zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('is-over'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('is-over'));
    zone.addEventListener('drop', (e) => {
      e.preventDefault();
      zone.classList.remove('is-over');
      if (e.dataTransfer.files[0]) preview(e.dataTransfer.files[0]);
    });
    return h('div', {}, input, zone);
  }

  function send(file, dryRun) {
    const form = new FormData();
    form.append('season', state.season);
    form.append('dryRun', String(dryRun));
    form.append('file', file);
    return api('/admin/imports', { method: 'POST', form });
  }

  async function preview(file) {
    replace(importSlot, h('p', { class: 'muted', role: 'status' }, `Analyse de « ${file.name} »…`));
    let data;
    try {
      data = await send(file, true);
    } catch (err) {
      replace(importSlot, h('div', { class: 'alert alert--error', role: 'alert' }, icon('alert'), h('p', err.fields?.file || err.message)), dropArea());
      return;
    }
    renderPreview(file, data);
  }

  function renderPreview(file, data) {
    const { summary, rows } = data;
    const chips = Object.entries(summary.counts).filter(([, n]) => n > 0)
      .map(([status, n]) => h('span', { class: 'summary-chip' }, rowPill(status), ' ', h('b', String(n))));
    const confirm = h('button', { class: 'btn', type: 'button', disabled: summary.willImport === 0 },
      icon('check'), summary.willImport ? `Importer ${plural(summary.willImport, 'ligne', 'lignes')}` : 'Rien à importer');
    confirm.addEventListener('click', () => commit(file, summary, confirm));
    const cancel = h('button', { class: 'btn btn--secondary', type: 'button', onClick: resetImport }, 'Annuler');

    const auto = summary.counts.AUTO_ACCEPT;
    const notes = [];
    if (auto) notes.push(`${plural(auto, 'demande en attente sera acceptée', 'demandes en attente seront acceptées')} automatiquement.`);
    if (summary.counts.NEW) notes.push('Les nouvelles personnes seront acceptées automatiquement dès qu’elles s’inscrivent avec le même email et le même numéro de téléphone.');

    replace(importSlot,
      h('div', { class: 'row row--between' }, h('p', {}, h('b', file.name), h('span', { class: 'muted' }, ` — saison ${data.season}, ${plural(summary.total, 'ligne lue', 'lignes lues')}`))),
      h('div', { class: 'summary-chips', 'aria-label': 'Résultat de l’analyse' }, chips),
      notes.length ? h('div', { class: 'alert alert--info' }, icon('info'), h('p', notes.join(' '))) : null,
      h('div', { class: 'preview-scroll', style: { 'margin-top': '16px' }, tabindex: '0', role: 'region', 'aria-label': 'Aperçu des lignes du fichier' },
        h('table', { class: 'table' },
          h('caption', { class: 'sr-only' }, 'Aperçu de l’import'),
          h('thead', h('tr', ['Ligne', 'Personne', 'Téléphone', 'Montant', 'Payé le', 'Résultat'].map((t) => h('th', { scope: 'col' }, t)))),
          h('tbody', rows.map((r) => h('tr', {},
            h('td', { class: 'num' }, String(r.line)),
            h('td', {}, h('b', r.name || '—'), h('div', { class: 'small muted' }, r.email || '')),
            h('td', {}, r.phone || '—'),
            h('td', {}, r.amount ? formatAmount(r.amount) : '—'),
            h('td', {}, r.paidAt ? formatDay(r.paidAt, { day: 'numeric', month: 'short', year: 'numeric' }) : '—'),
            h('td', {}, rowPill(r.status), r.note ? h('div', { class: 'row-note' }, r.note) : null)))))),
      h('div', { class: 'row', style: { 'margin-top': '16px' } }, confirm, cancel));
    confirm.focus();
  }

  async function commit(file, summary, btn) {
    const ok = await confirmDialog({
      title: `Importer ${plural(summary.willImport, 'personne', 'personnes')} ?`,
      message: summary.counts.AUTO_ACCEPT
        ? `${plural(summary.counts.AUTO_ACCEPT, 'demande d’adhésion en attente sera acceptée', 'demandes d’adhésion en attente seront acceptées')} immédiatement et les comptes seront activés. Vous pourrez annuler l’import depuis l’historique tant que les personnes ne se sont pas inscrites.`
        : 'Les personnes ajoutées seront acceptées automatiquement dès qu’elles s’inscrivent. Vous pourrez annuler l’import depuis l’historique.',
      confirmLabel: 'Importer',
    });
    if (!ok) return;
    withBusy(btn, async () => {
      try {
        const done = await send(file, false);
        const c = done.summary.counts;
        replace(importSlot,
          h('div', { class: 'alert alert--success', role: 'status' }, icon('check'),
            h('p', {}, h('b', `${plural(done.summary.willImport, 'personne ajoutée', 'personnes ajoutées')}. `),
              c.AUTO_ACCEPT ? `${plural(c.AUTO_ACCEPT, 'demande acceptée', 'demandes acceptées')} automatiquement. ` : '',
              c.RENEWAL ? `${plural(c.RENEWAL, 'cotisation enregistrée', 'cotisations enregistrées')} pour des membres existants. ` : '',
              done.summary.total - done.summary.willImport ? `${plural(done.summary.total - done.summary.willImport, 'ligne ignorée', 'lignes ignorées')}.` : '')),
          h('div', { style: { 'margin-top': '16px' } }, h('button', { class: 'btn btn--secondary', type: 'button', onClick: resetImport }, 'Importer un autre fichier')));
        toast('Import terminé.');
        refreshAdminCounts();
        refreshList();
        refreshHistory();
      } catch (err) {
        toast(err.fields?.file || err.message, 'error');
      }
    });
  }

  // ------------------------------------------------------------ manual entry
  function addDialog() {
    const form = h('form', { class: 'form', novalidate: true },
      h('div', { class: 'cols-2' },
        field({ label: 'Nom complet', name: 'name', required: true, maxlength: 80, autocomplete: 'off' }),
        field({ label: 'Adresse email', name: 'email', type: 'email', required: true, autocomplete: 'off' })),
      h('div', { class: 'cols-2' },
        field({ label: 'Téléphone', name: 'phone', type: 'tel', required: true, hint: 'Doit être le même que celui de l’inscription.' }),
        field({ label: 'Montant (DT)', name: 'amount', optional: true, inputmode: 'decimal', hint: 'Exemple : 25 ou 25,500' })),
      h('div', { class: 'cols-2' },
        field({ label: 'Date de paiement', name: 'paidAt', type: 'date', optional: true }),
        field({ label: 'Référence du reçu', name: 'reference', optional: true, maxlength: 60 })));
    const submit = h('button', { class: 'btn', type: 'submit' }, 'Ajouter');
    const m = openModal({
      title: `Ajouter une cotisation — saison ${state.season}`,
      description: 'La personne sera acceptée automatiquement quand elle s’inscrira. Si elle est déjà membre, la cotisation est enregistrée sur son compte.',
      body: form,
      actions: [h('button', { class: 'btn btn--secondary', type: 'button', onClick: () => m.close() }, 'Annuler'), submit],
    });
    submit.addEventListener('click', () => form.requestSubmit());
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      clearErrors(form);
      withBusy(submit, async () => {
        try {
          const r = await api('/admin/subscriptions', { method: 'POST', body: { ...formData(form), season: state.season } });
          m.close();
          toast(r.result === 'RENEWAL' ? 'Cotisation enregistrée sur le compte du membre.' : r.result === 'AUTO_ACCEPT' ? 'Cotisation ajoutée et demande d’adhésion acceptée.' : 'Cotisation ajoutée à la liste.');
          refreshAdminCounts();
          refreshList();
        } catch (err) { showErrors(form, err); }
      });
    });
  }

  // ------------------------------------------------------------ list
  function paintTabs() {
    replace(tabs, [['AVAILABLE', 'En attente d’inscription'], ['CLAIMED', 'Membres inscrits'], ['REVOKED', 'Annulées'], ['', 'Toutes']].map(([v, l]) => h('button', {
      class: 'tab', role: 'tab', type: 'button', 'aria-selected': String(state.status === v), 'aria-controls': 'sub-panel',
      onClick: () => { state.status = v; state.page = 1; paintTabs(); refreshList(); },
    }, l)));
  }

  async function revoke(s, btn) {
    const ok = await confirmDialog({
      title: 'Retirer cette cotisation ?',
      message: `${s.name} (${s.email}) ne sera plus acceptée automatiquement à l’inscription. Sa demande, si elle existe, restera à valider à la main.`,
      confirmLabel: 'Retirer de la liste', danger: true,
    });
    if (!ok) return;
    withBusy(btn, async () => {
      try {
        await api(`/admin/subscriptions/${s.id}`, { method: 'DELETE' });
        toast('Cotisation retirée de la liste.');
        refreshList();
        refreshHistory();
      } catch (err) { toast(err.message, 'error'); }
    });
  }

  const refreshList = () => load(list, () => api('/admin/subscriptions', { query: { season: state.season, status: state.status, q: state.q, page: state.page } }), (data) => {
    if (!data.items.length) {
      return emptyState({
        title: state.q ? 'Aucune cotisation trouvée' : 'Aucune cotisation ici',
        text: state.q ? 'La recherche porte sur le nom et l’adresse email.' : `Importez la liste des personnes qui ont payé la saison ${state.season} pour les voir ici.`,
      });
    }
    return h('div', {},
      h('p', { class: 'small muted' }, plural(data.total, 'cotisation', 'cotisations')),
      h('div', { class: 'panel panel--flush' },
        h('div', { class: 'table-wrap' },
          h('table', { class: 'table table--stack' },
            h('caption', { class: 'sr-only' }, 'Cotisations'),
            h('thead', h('tr', ['Personne', 'Téléphone', 'Montant', 'Payé le', 'Statut'].map((t) => h('th', { scope: 'col' }, t)), h('th', { scope: 'col' }, h('span', { class: 'sr-only' }, 'Actions')))),
            h('tbody', data.items.map((s) => {
              const btn = h('button', { class: 'btn btn--danger-ghost btn--sm', type: 'button' }, 'Retirer');
              btn.addEventListener('click', () => revoke(s, btn));
              return h('tr', {},
                h('td', {}, s.memberId ? h('a', { class: 'cell-link', href: `/admin/members/${s.memberId}`, 'data-link': '' }, s.name) : h('b', s.name),
                  h('div', { class: 'small muted' }, s.email), s.reference ? h('div', { class: 'small muted' }, `Reçu ${s.reference}`) : null),
                h('td', { 'data-label': 'Téléphone' }, s.phone),
                h('td', { 'data-label': 'Montant' }, formatAmount(s.amount)),
                h('td', { 'data-label': 'Payé le' }, s.paidAt ? formatDay(s.paidAt, { day: 'numeric', month: 'short', year: 'numeric' }) : '—'),
                h('td', { 'data-label': 'Statut' }, statusPill('subscription', s.status), s.claimedAt ? h('div', { class: 'small muted' }, `Inscrit ${relative(s.claimedAt)}`) : null),
                h('td', {}, s.status === 'AVAILABLE' ? h('div', { class: 'actions' }, btn) : null));
            }))))),
      pagination(data, (p) => { state.page = p; refreshList(); }, ['cotisation', 'cotisations']));
  }, { skeleton: 'row', count: 4 });

  // ------------------------------------------------------------ history
  async function revert(b, btn) {
    const ok = await confirmDialog({
      title: `Annuler l’import « ${b.filename} » ?`,
      message: `${plural(b.stillAvailable, 'personne', 'personnes')} pas encore inscrite${b.stillAvailable > 1 ? 's' : ''} sera retirée de la liste. Les membres déjà inscrits grâce à cet import restent membres.`,
      confirmLabel: 'Annuler l’import', danger: true,
    });
    if (!ok) return;
    withBusy(btn, async () => {
      try {
        const r = await api(`/admin/imports/${b.id}`, { method: 'DELETE' });
        toast(`Import annulé : ${plural(r.revoked, 'personne retirée', 'personnes retirées')}.`);
        refreshList();
        refreshHistory();
      } catch (err) { toast(err.message, 'error'); }
    });
  }

  const refreshHistory = () => load(history, () => api('/admin/imports', { query: { page: state.batchPage, pageSize: 5 } }), (data) => {
    if (!data.items.length) return h('p', { class: 'muted' }, 'Aucun import pour le moment.');
    return h('div', {},
      h('div', { class: 'panel panel--flush' },
        h('div', { class: 'table-wrap' },
          h('table', { class: 'table table--stack' },
            h('caption', { class: 'sr-only' }, 'Historique des imports'),
            h('thead', h('tr', ['Fichier', 'Saison', 'Résultat', 'Date'].map((t) => h('th', { scope: 'col' }, t)), h('th', { scope: 'col' }, h('span', { class: 'sr-only' }, 'Actions')))),
            h('tbody', data.items.map((b) => {
              const btn = h('button', { class: 'btn btn--danger-ghost btn--sm', type: 'button' }, 'Annuler l’import');
              btn.addEventListener('click', () => revert(b, btn));
              return h('tr', {},
                h('td', {}, h('b', { class: 'nowrap' }, b.filename), h('div', { class: 'small muted' }, b.author ? `par ${b.author}` : '')),
                h('td', { 'data-label': 'Saison' }, b.season),
                h('td', { 'data-label': 'Résultat' }, `${b.rowsImported} ajoutée${b.rowsImported > 1 ? 's' : ''}, ${b.rowsSkipped} ignorée${b.rowsSkipped > 1 ? 's' : ''}`,
                  b.autoAccepted ? h('div', { class: 'small muted' }, `${plural(b.autoAccepted, 'acceptation automatique', 'acceptations automatiques')}`) : null),
                h('td', { 'data-label': 'Date' }, h('time', { datetime: b.createdAt, title: formatDateTime(b.createdAt) }, formatDate(b.createdAt))),
                h('td', {}, b.revertedAt ? h('span', { class: 'status status--REVOKED' }, 'Annulé')
                  : b.stillAvailable > 0 ? h('div', { class: 'actions' }, btn) : null));
            }))))),
      pagination(data, (p) => { state.batchPage = p; refreshHistory(); }, ['import', 'imports']));
  }, { skeleton: 'row', count: 2 });

  paintTabs();
  paintExport();
  resetImport();
  refreshList();
  refreshHistory();
  onLive(['subscriptions', 'requests', 'members'], () => quietly(() => { refreshList(); refreshHistory(); }), { container: list });

  return h('div', {},
    pageHead({
      title: 'Cotisations',
      lead: 'Importez la liste des personnes qui ont payé leur cotisation : elles seront acceptées automatiquement dès qu’elles s’inscrivent, sans attendre un administrateur.',
      actions: [
        h('a', { class: 'btn btn--secondary', href: downloadHref('template') }, icon('sheet'), 'Télécharger le modèle'),
        exportLink,
        h('button', { class: 'btn', type: 'button', onClick: addDialog }, icon('plus'), 'Ajouter une personne'),
      ],
    }),
    h('div', { class: 'toolbar' }, h('label', { class: 'sr-only', for: 'season-select' }, 'Saison'), seasonSelect),
    h('section', { class: 'panel', 'aria-labelledby': 'imp-title', style: { 'margin-bottom': '32px' } },
      h('h2', { id: 'imp-title', style: { 'margin-bottom': '8px' } }, 'Importer une liste'),
      h('ol', { class: 'import-steps' },
        h('li', 'Préparez un fichier Excel ou CSV avec les colonnes : Nom complet (ou Nom et Prénom), Email, Téléphone, et si vous le souhaitez Montant, Date de paiement, Référence.'),
        h('li', 'Choisissez le fichier : un aperçu ligne par ligne s’affiche, rien n’est encore enregistré.'),
        h('li', 'Vérifiez l’aperçu puis confirmez. Vous pouvez annuler un import depuis l’historique.')),
      importSlot),
    h('section', { 'aria-labelledby': 'sub-title', style: { 'margin-bottom': '32px' } },
      h('div', { class: 'section-head' }, listTitle),
      tabs,
      h('div', { class: 'toolbar' }, searchBox({ label: 'Rechercher une cotisation', placeholder: 'Rechercher par nom ou email', onSearch: (q) => { state.q = q; state.page = 1; refreshList(); } })),
      list),
    h('section', { 'aria-labelledby': 'hist-title' },
      h('div', { class: 'section-head' }, h('h2', { id: 'hist-title' }, 'Historique des imports')),
      history));
}

export { IMPORT_ROW_STATUS };
