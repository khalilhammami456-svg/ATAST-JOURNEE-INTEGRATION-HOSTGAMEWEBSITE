/** Admin event management: library, create/edit form, participants (FR-07..FR-13). */
import { h, replace, nextId } from '../components/dom.js';
import { icon } from '../components/icons.js';
import { eventCover } from '../components/brand.js';
import {
  load, emptyState, pageHead, avatar, pagination, searchBox, typeBadge, pointsChip, statusPill, toast, confirmDialog,
  withBusy, field, showErrors, clearErrors, formData, debounce, quietly,
} from '../components/ui.js';
import { api } from '../services/api.js';
import { navigate, onLive } from '../app/router.js';
import {
  EVENT_TYPES, TYPE_LABELS, TYPE_POINTS, EVENT_STATUS, formatDay, formatTime, formatPrice, plural,
} from '../services/format.js';

// ---------------------------------------------------------------- Library
export function adminEventsPage() {
  const state = { q: '', type: '', status: '', when: '', page: 1 };
  const results = h('div', {});
  const refresh = () => load(results, () => api('/admin/events', { query: state }), (data) => {
    if (!data.items.length) {
      const filtered = state.q || state.type || state.status || state.when;
      return emptyState(filtered
        ? { title: 'Aucun événement ne correspond', text: 'Modifiez la recherche ou les filtres.' }
        : { title: 'Aucun événement enregistré', text: 'Créez le premier événement du club. Il restera en brouillon tant que vous ne le publiez pas.', action: h('a', { class: 'btn', href: '/admin/events/new', 'data-link': '' }, icon('plus'), 'Créer un événement') });
    }
    return h('div', {},
      h('p', { class: 'small muted' }, plural(data.total, 'événement', 'événements')),
      h('div', { class: 'panel panel--flush' },
        h('div', { class: 'table-wrap' },
          h('table', { class: 'table table--stack' },
            h('caption', { class: 'sr-only' }, 'Bibliothèque des événements'),
            h('thead', h('tr', ...['Date', 'Événement', 'Type', 'Statut', 'Tarif', 'Participants'].map((t) => h('th', { scope: 'col' }, t)), h('th', { scope: 'col' }, h('span', { class: 'sr-only' }, 'Actions')))),
            h('tbody', data.items.map((e) => h('tr', {},
              h('td', { 'data-label': 'Date', class: 'nowrap' }, formatDay(e.date, { day: 'numeric', month: 'short', year: 'numeric' }), h('div', { class: 'small muted' }, formatTime(e.time))),
              h('td', {}, h('a', { class: 'cell-link', href: `/admin/events/${e.id}`, 'data-link': '' }, e.title), h('div', { class: 'small muted' }, e.location)),
              h('td', { 'data-label': 'Type' }, typeBadge(e.type, { short: true })),
              h('td', { 'data-label': 'Statut' }, statusPill('event', e.status)),
              h('td', { 'data-label': 'Tarif', class: 'nowrap' }, formatPrice(e)),
              h('td', { 'data-label': 'Participants' }, h('span', { class: 'num' }, String(e.validatedCount)), e.registeredCount ? h('span', { class: 'small muted' }, ` + ${e.registeredCount} inscrit${e.registeredCount > 1 ? 's' : ''}`) : null),
              h('td', {}, h('div', { class: 'actions' },
                h('a', { class: 'btn btn--ghost btn--sm', href: `/admin/events/${e.id}/edit`, 'data-link': '', 'aria-label': `Modifier ${e.title}` }, icon('edit'), 'Modifier'),
                h('a', { class: 'btn btn--secondary btn--sm', href: `/admin/events/${e.id}`, 'data-link': '' }, 'Gérer'))))))))),
      pagination(data, (p) => { state.page = p; refresh(); }, ['événement', 'événements']));
  }, { skeleton: 'row', count: 6 });

  const sel = (label, key, options) => h('select', {
    class: 'select', 'aria-label': label, onChange: (e) => { state[key] = e.target.value; state.page = 1; refresh(); },
  }, options.map(([v, l]) => h('option', { value: v }, l)));

  refresh();
  onLive(['events'], () => quietly(refresh), { container: results });
  return h('div', {},
    pageHead({
      title: 'Événements',
      lead: 'Créez, publiez et archivez les événements. Ouvrez un événement pour valider les participations.',
      actions: h('a', { class: 'btn', href: '/admin/events/new', 'data-link': '' }, icon('plus'), 'Créer un événement'),
    }),
    h('div', { class: 'toolbar' },
      searchBox({ label: 'Rechercher un événement', placeholder: 'Rechercher par titre ou lieu', onSearch: (q) => { state.q = q; state.page = 1; refresh(); } }),
      sel('Filtrer par type', 'type', [['', 'Tous les types'], ...EVENT_TYPES.map((t) => [t, TYPE_LABELS[t]])]),
      sel('Filtrer par statut', 'status', [['', 'En cours (hors archives)'], ...Object.entries(EVENT_STATUS), ['ALL', 'Tous, archives comprises']]),
      sel('Filtrer par période', 'when', [['', 'Toutes les dates'], ['upcoming', 'À venir'], ['past', 'Passés']])),
    results);
}

// ---------------------------------------------------------------- Create / edit form
export async function eventFormPage({ params, setTitle }) {
  const editing = Boolean(params.id);
  const ev = editing ? await api(`/admin/events/${params.id}`) : null;
  if (editing) setTitle(`Modifier « ${ev.title} »`);

  const v = ev || { type: 'SMALL', isFree: true, currency: 'TND', status: 'DRAFT', date: '', time: '14:00' };
  let pendingFile = null;
  let removeImage = false;

  // Type picker shows the points of each type (FR-08)
  const typeName = nextId('type');
  const typeSet = h('fieldset', { class: 'field' },
    h('legend', 'Type d’événement'),
    h('div', { class: 'hint', id: `${typeName}-hint` }, 'Le type fixe automatiquement les points gagnés par chaque participant validé.'),
    h('div', { class: 'type-picker', role: 'radiogroup', 'aria-describedby': `${typeName}-hint` },
      EVENT_TYPES.map((t) => h('label', { class: 'type-option' },
        h('input', { type: 'radio', name: 'type', value: t, checked: v.type === t, required: true }),
        h('span', {}, h('small', TYPE_LABELS[t]), h('b', `${TYPE_POINTS[t]} pts`))))),
    h('div', { class: 'field-error', id: `${typeName}-err` }));

  // Free / paid (FR-09)
  const priceField = field({ label: 'Prix', name: 'price', value: v.price || '', inputmode: 'decimal', hint: 'Montant par participant, par exemple 15 ou 12,500.' });
  const currencyField = field({ label: 'Devise', name: 'currency', value: v.currency, options: [['TND', 'Dinar tunisien (TND)'], ['EUR', 'Euro (EUR)'], ['USD', 'Dollar (USD)']] });
  const priceRow = h('div', { class: 'form-grid form-grid--2' }, priceField, currencyField);
  const freeSet = h('fieldset', { class: 'field' },
    h('legend', 'Tarif'),
    h('div', { class: 'segmented', role: 'radiogroup' },
      [['true', 'Gratuit'], ['false', 'Payant']].map(([val, l]) => h('label', {},
        h('input', { type: 'radio', name: 'isFree', value: val, checked: String(v.isFree) === val, onChange: syncPrice }),
        h('span', l)))),
    h('div', { class: 'field-error' }));
  function syncPrice() {
    const paid = freeSet.querySelector('input:checked')?.value === 'false';
    priceRow.hidden = !paid;
    priceField.control.required = paid;
  }

  // Image
  const imgId = nextId('img');
  const fileInput = h('input', { id: imgId, class: 'file-input', type: 'file', accept: 'image/jpeg,image/png,image/webp' });
  const imgSlot = h('div', {});
  function paintImage() {
    let preview;
    if (pendingFile) preview = h('img', { class: 'image-preview', src: URL.createObjectURL(pendingFile), alt: 'Aperçu de la nouvelle image' });
    else if (ev?.imageUrl && !removeImage) preview = h('img', { class: 'image-preview', src: ev.imageUrl, alt: 'Image actuelle de l’événement' });
    else preview = h('div', { class: 'image-drop' }, icon('image'), h('span', 'Aucune image. Une illustration aux couleurs du type d’événement sera affichée.'));
    const hasImage = pendingFile || (ev?.imageUrl && !removeImage);
    replace(imgSlot, preview, h('div', { class: 'row', style: { 'margin-top': '12px' } },
      fileInput,
      h('label', { for: imgId, class: 'btn btn--secondary btn--sm' }, icon('upload'), hasImage ? 'Remplacer l’image' : 'Choisir une image'),
      hasImage ? h('button', { class: 'btn btn--danger-ghost btn--sm', type: 'button', onClick: () => { pendingFile = null; removeImage = true; paintImage(); } }, 'Retirer l’image') : null),
    h('div', { class: 'field-error', id: `${imgId}-err` }));
  }
  fileInput.addEventListener('change', () => {
    const f = fileInput.files[0];
    fileInput.value = '';
    if (!f) return;
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(f.type)) return toast('Formats acceptés : JPEG, PNG ou WebP.', 'error');
    if (f.size > 2 * 1024 * 1024) return toast('L’image ne doit pas dépasser 2 Mo.', 'error');
    pendingFile = f;
    removeImage = false;
    paintImage();
  });
  paintImage();

  const statusOptions = Object.entries(EVENT_STATUS).filter(([s]) => editing || s !== 'ARCHIVED');
  const submit = h('button', { class: 'btn', type: 'submit' }, editing ? 'Enregistrer les modifications' : 'Créer l’événement');
  const form = h('form', { class: 'form', novalidate: true },
    h('div', { class: 'form-section' },
      h('h2', 'Description'),
      h('div', { class: 'form-grid' },
        field({ label: 'Titre', name: 'title', value: v.title || '', required: true, maxlength: 120 }),
        typeSet,
        field({ label: 'Description', name: 'description', value: v.description || '', multiline: true, optional: true, maxlength: 5000, rows: 6 }))),
    h('div', { class: 'form-section' },
      h('h2', 'Date et lieu'),
      h('div', { class: 'form-grid form-grid--2' },
        field({ label: 'Date', name: 'date', type: 'date', value: v.date, required: true }),
        field({ label: 'Heure', name: 'time', type: 'time', value: v.time, required: true }),
        field({ label: 'Lieu', name: 'location', value: v.location || '', required: true, maxlength: 200, span: true, placeholder: 'Ex. Amphithéâtre A, ISIMM' }))),
    h('div', { class: 'form-section' },
      h('h2', 'Tarif et informations pratiques'),
      h('div', { class: 'form-grid' },
        freeSet, priceRow,
        field({ label: 'Informations complémentaires', name: 'additionalInfo', value: v.additionalInfo || '', multiline: true, optional: true, maxlength: 2000, rows: 3, hint: 'Matériel à apporter, transport, repas inclus…' }))),
    h('div', { class: 'form-section' },
      h('h2', 'Image et publication'),
      h('div', { class: 'form-grid' },
        h('div', { class: 'field' }, h('span', { class: 'label' }, 'Image', h('span', { class: 'optional' }, ' (facultatif)')), h('div', { class: 'hint' }, 'JPEG, PNG ou WebP, 2 Mo maximum.'), imgSlot),
        field({ label: 'Statut', name: 'status', value: v.status, options: statusOptions, hint: 'Les membres voient uniquement les événements publiés ou terminés.' }))),
    h('div', { class: 'form-actions' },
      h('a', { class: 'btn btn--secondary', href: editing ? `/admin/events/${ev.id}` : '/admin/events', 'data-link': '' }, 'Annuler'),
      submit));
  syncPrice();

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = formData(form);
    const f = {};
    if (!data.title || data.title.trim().length < 3) f.title = 'Le titre doit contenir au moins 3 caractères.';
    if (!data.type) f.type = 'Choisissez un type d’événement.';
    if (!data.date) f.date = 'La date est obligatoire.';
    if (!data.time) f.time = 'L’heure est obligatoire.';
    if (!data.location || data.location.trim().length < 2) f.location = 'Le lieu est obligatoire.';
    if (data.isFree === 'false') {
      const n = Number(String(data.price || '').replace(',', '.'));
      if (!data.price) f.price = 'Un événement payant doit avoir un prix.';
      else if (!Number.isFinite(n) || n <= 0) f.price = 'Le prix doit être un nombre supérieur à zéro.';
    }
    if (Object.keys(f).length) return showErrors(form, { fields: f });
    clearErrors(form);
    const body = { ...data, isFree: data.isFree === 'true', price: data.isFree === 'true' ? null : String(data.price).replace(',', '.').trim() };

    if (editing && ev.type !== body.type && ev.validatedCount > 0) {
      const ok = await confirmDialog({
        title: 'Changer le type de l’événement ?',
        message: `${plural(ev.validatedCount, 'participation validée', 'participations validées')} passeront de ${TYPE_POINTS[ev.type]} à ${TYPE_POINTS[body.type]} points. Les scores des membres concernés seront recalculés.`,
        confirmLabel: 'Changer et recalculer',
      });
      if (!ok) return;
    }
    withBusy(submit, async () => {
      try {
        const saved = editing
          ? await api(`/admin/events/${ev.id}`, { method: 'PUT', body })
          : await api('/admin/events', { method: 'POST', body });
        let imageWarning = null;
        try {
          if (pendingFile) {
            const fd = new FormData();
            fd.append('file', pendingFile);
            await api(`/admin/events/${saved.id}/image`, { method: 'POST', form: fd });
          } else if (removeImage && ev?.imageUrl) {
            await api(`/admin/events/${saved.id}/image`, { method: 'DELETE' });
          }
        } catch (imgErr) {
          imageWarning = imgErr.fields?.file || imgErr.message;
        }
        if (imageWarning) toast(`Événement enregistré, mais l’image n’a pas été acceptée : ${imageWarning}`, 'error');
        else toast(editing ? (saved.recalculatedParticipations ? `Événement enregistré. ${plural(saved.recalculatedParticipations, 'participation recalculée', 'participations recalculées')}.` : 'Événement enregistré.') : 'Événement créé.');
        navigate(`/admin/events/${saved.id}`);
      } catch (err) { showErrors(form, err); }
    });
  });

  return h('div', {},
    pageHead({
      title: editing ? 'Modifier l’événement' : 'Créer un événement',
      lead: editing ? 'Les participations déjà enregistrées sont conservées.' : 'Enregistrez-le en brouillon pour le préparer, ou publiez-le directement.',
      back: { href: editing ? `/admin/events/${ev.id}` : '/admin/events', label: editing ? ev.title : 'Événements' },
    }),
    h('section', { class: 'panel form-panel' }, form));
}

// ---------------------------------------------------------------- Detail + participants (FR-13)
export async function adminEventDetailPage({ params, setTitle }) {
  let ev = await api(`/admin/events/${params.id}`);
  setTitle(ev.title);
  const head = h('div', {});
  const people = h('div', {});

  function paintHead() {
    const publishBtn = ev.status === 'DRAFT'
      ? h('button', { class: 'btn', type: 'button', onClick: publish }, icon('send'), 'Publier')
      : null;
    const archiveBtn = ev.status !== 'ARCHIVED'
      ? h('button', { class: 'btn btn--danger-ghost', type: 'button', onClick: archive }, icon('archive'), 'Archiver')
      : null;
    replace(head,
      pageHead({
        title: ev.title,
        back: { href: '/admin/events', label: 'Événements' },
        actions: [archiveBtn, h('a', { class: 'btn btn--secondary', href: `/admin/events/${ev.id}/edit`, 'data-link': '' }, icon('edit'), 'Modifier'), publishBtn],
      }),
      h('div', { class: 'row', style: { 'margin-top': '-12px', 'margin-bottom': '24px' } }, typeBadge(ev.type), pointsChip(ev.points), statusPill('event', ev.status),
        h('span', { class: 'muted' }, `${formatDay(ev.date)}, ${formatTime(ev.time)}`)));
  }

  async function publish(e) {
    const btn = e.currentTarget;
    const ok = await confirmDialog({
      title: 'Publier cet événement ?',
      message: 'Il apparaîtra dans la bibliothèque des membres, qui pourront s’y inscrire.',
      confirmLabel: 'Publier',
    });
    if (!ok) return;
    withBusy(btn, async () => {
      try {
        await api(`/admin/events/${ev.id}`, {
          method: 'PUT',
          body: {
            title: ev.title, type: ev.type, description: ev.description, date: ev.date, time: ev.time, location: ev.location,
            isFree: ev.isFree, price: ev.price, currency: ev.currency, additionalInfo: ev.additionalInfo, status: 'PUBLISHED',
          },
        });
        ev = await api(`/admin/events/${ev.id}`);
        paintHead();
        paintPeople();
        toast('Événement publié.');
      } catch (err) { toast(err.message, 'error'); }
    });
  }

  async function archive(e) {
    const btn = e.currentTarget;
    const ok = await confirmDialog({
      title: 'Archiver cet événement ?',
      message: 'Il disparaîtra de la bibliothèque des membres. Les participations et les points déjà acquis sont conservés. Vous pourrez le republier depuis le formulaire de modification.',
      confirmLabel: 'Archiver', danger: true,
    });
    if (!ok) return;
    withBusy(btn, async () => {
      try {
        await api(`/admin/events/${ev.id}`, { method: 'DELETE' });
        ev = await api(`/admin/events/${ev.id}`);
        paintHead();
        paintPeople();
        toast('Événement archivé.');
      } catch (err) { toast(err.message, 'error'); }
    });
  }

  const canValidate = () => ev.status === 'PUBLISHED' || ev.status === 'COMPLETED';

  async function act(btn, fn, okMessage) {
    await withBusy(btn, async () => {
      try {
        ev = await fn();
        paintPeople();
        toast(okMessage);
      } catch (err) { toast(err.message, 'error'); }
    });
  }

  function personRow(p, actions) {
    return h('li', {},
      h('div', { class: 'who' }, avatar(p.member), h('div', { class: 'grow' },
        h('a', { href: `/admin/members/${p.member.id}`, 'data-link': '' }, h('b', p.member.name)),
        h('span', { class: 'small muted' }, p.member.email))),
      p.status === 'VALIDATED' ? pointsChip(p.pointsAwarded) : statusPill('participation', 'REGISTERED'),
      h('div', { class: 'acts' }, actions));
  }

  function paintPeople() {
    const registered = ev.participants.filter((p) => p.status === 'REGISTERED');
    const validated = ev.participants.filter((p) => p.status === 'VALIDATED');
    const removeBtn = (p) => {
      const b = h('button', { class: 'btn btn--danger-ghost btn--sm', type: 'button', 'aria-label': `Retirer ${p.member.name}` }, 'Retirer');
      b.addEventListener('click', async () => {
        const ok = await confirmDialog({
          title: `Retirer ${p.member.name} ?`,
          message: p.status === 'VALIDATED'
            ? `La participation validée sera retirée et ${p.pointsAwarded} points seront déduits de son score.`
            : 'L’inscription de ce membre sera annulée.',
          confirmLabel: 'Retirer', danger: true,
        });
        if (ok) act(b, () => api(`/admin/participations/${p.id}`, { method: 'DELETE' }), 'Participation retirée.');
      });
      return b;
    };
    const validateBtn = (p) => {
      const b = h('button', { class: 'btn btn--sm', type: 'button', disabled: !canValidate(), 'aria-label': `Valider la participation de ${p.member.name}` }, icon('check'), 'Valider');
      b.addEventListener('click', () => act(b, () => api(`/admin/participations/${p.id}/validate`, { method: 'POST' }), `Participation de ${p.member.name} validée${ev.points ? ` : +${ev.points} pts` : ''}.`));
      return b;
    };

    replace(people,
      !canValidate() ? h('div', { class: 'alert alert--warning', style: { 'margin-bottom': '16px' } }, icon('info'),
        h('p', ev.status === 'DRAFT' ? 'Publiez l’événement pour pouvoir valider des participations.' : 'Cet événement est archivé : les participations sont conservées mais ne peuvent plus être validées.')) : null,
      canValidate() ? addParticipant() : null,
      h('div', { class: 'participants' },
        h('div', { class: 'p-section' },
          h('h3', 'Inscrits en attente de validation', h('span', { class: 'count' }, String(registered.length))),
          registered.length
            ? h('ul', { class: 'p-list' }, registered.map((p) => personRow(p, [validateBtn(p), removeBtn(p)])))
            : h('p', { class: 'p-empty' }, 'Aucune inscription en attente.')),
        h('div', { class: 'p-section' },
          h('h3', 'Participations validées', h('span', { class: 'count' }, String(validated.length))),
          validated.length
            ? h('ul', { class: 'p-list' }, validated.map((p) => personRow(p, [removeBtn(p)])))
            : h('p', { class: 'p-empty' }, ev.points ? `Validez une présence pour attribuer ${ev.points} points au membre.` : 'Aucune participation validée. Les réunions ne rapportent pas de points.'))));
  }

  /** Accessible combobox to record attendance of any active member. */
  function addParticipant() {
    const listId = nextId('combo');
    const inputId = nextId('combo-in');
    const taken = new Set(ev.participants.filter((p) => p.status === 'VALIDATED').map((p) => p.member.id));
    const pending = new Map(ev.participants.filter((p) => p.status === 'REGISTERED').map((p) => [p.member.id, p.id]));
    let options = [];
    let active = -1;
    const input = h('input', {
      id: inputId, class: 'input', type: 'text', role: 'combobox', autocomplete: 'off', 'aria-autocomplete': 'list',
      'aria-expanded': 'false', 'aria-controls': listId, placeholder: 'Nom ou email du membre',
    });
    const list = h('ul', { id: listId, class: 'combo__list', role: 'listbox', hidden: true, 'aria-label': 'Membres trouvés' });

    function close() { list.hidden = true; input.setAttribute('aria-expanded', 'false'); input.removeAttribute('aria-activedescendant'); active = -1; }
    function setActive(i) {
      active = i;
      [...list.children].forEach((li, j) => li.setAttribute('aria-selected', String(j === i)));
      const li = list.children[i];
      if (li) { input.setAttribute('aria-activedescendant', li.id); li.scrollIntoView({ block: 'nearest' }); }
    }
    async function choose(m) {
      if (!m || taken.has(m.id)) return;
      close();
      input.value = '';
      const pid = pending.get(m.id);
      const fake = h('button');
      await act(fake, () => (pid
        ? api(`/admin/participations/${pid}/validate`, { method: 'POST' })
        : api(`/admin/events/${ev.id}/participations`, { method: 'POST', body: { memberId: m.id } })),
      `Participation de ${m.name} validée${ev.points ? ` : +${ev.points} pts` : ''}.`);
      people.querySelector('[role="combobox"]')?.focus();
    }
    const search = debounce(async () => {
      const q = input.value.trim();
      if (q.length < 2) return close();
      try {
        const res = await api('/admin/members', { query: { q, pageSize: 8 } });
        options = res.items;
        replace(list, options.length ? options.map((m, i) => h('li', {
          id: `${listId}-${i}`, role: 'option', 'aria-selected': 'false', 'aria-disabled': taken.has(m.id) ? 'true' : undefined,
          class: ['combo__opt', taken.has(m.id) && 'is-disabled'],
          onMousedown: (e) => { e.preventDefault(); choose(m); },
        }, avatar(m, { size: 'sm' }), h('div', {}, m.name, h('small', taken.has(m.id) ? 'Déjà validé' : pending.has(m.id) ? 'Inscrit, à valider' : m.email))))
          : h('li', { class: 'combo__opt is-disabled', role: 'option', 'aria-disabled': 'true' }, 'Aucun membre actif trouvé'));
        list.hidden = false;
        input.setAttribute('aria-expanded', 'true');
      } catch (err) { toast(err.message, 'error'); }
    }, 250);
    input.addEventListener('input', search);
    input.addEventListener('blur', () => setTimeout(close, 150));
    input.addEventListener('keydown', (e) => {
      if (list.hidden || !options.length) return;
      if (e.key === 'ArrowDown') { e.preventDefault(); setActive((active + 1) % options.length); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((active - 1 + options.length) % options.length); }
      else if (e.key === 'Enter') { e.preventDefault(); if (active >= 0) choose(options[active]); }
      else if (e.key === 'Escape') { close(); }
    });
    return h('div', { class: 'field', style: { 'margin-bottom': '24px', 'max-width': '520px' } },
      h('label', { for: inputId }, 'Enregistrer une présence'),
      h('div', { class: 'hint' }, 'Recherchez un membre actif pour valider directement sa participation.'),
      h('div', { class: 'combo' }, h('div', { class: 'input-icon' }, icon('search'), input), list));
  }

  paintHead();
  paintPeople();

  const fact = (ic, label, value) => h('div', { class: 'fact' }, h('span', { class: 'fact__icon' }, icon(ic)), h('div', {}, h('small', label), h('b', value)));
  return h('div', {},
    head,
    h('div', { class: 'profile-cols' },
      h('section', { class: 'panel', 'aria-labelledby': 'parts' },
        h('div', { class: 'panel__head' }, h('h2', { id: 'parts' }, 'Participants')),
        people),
      h('aside', { class: 'stack' },
        h('div', { class: 'panel panel--flush' },
          ev.imageUrl ? h('img', { class: 'event-hero__img', src: ev.imageUrl, alt: '', style: { 'margin-bottom': '0', 'border-radius': '0' } })
            : h('div', { class: ['event-cover', `event-cover--${ev.type}`], style: { 'margin-bottom': '0', 'border-radius': '0' } }, eventCover(ev.id, ev.type)),
          h('div', { class: 'facts', style: { padding: '24px' } },
            fact('pin', 'Lieu', ev.location),
            fact('ticket', 'Tarif', formatPrice(ev)),
            fact('calendar', 'Date', `${formatDay(ev.date)}, ${formatTime(ev.time)}`))),
        ev.description ? h('section', { class: 'panel' }, h('h2', { style: { 'margin-bottom': '8px' } }, 'Description'), h('p', { class: 'prose' }, ev.description)) : null)));
}
