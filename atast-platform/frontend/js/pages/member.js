/** Member interface pages: home, events, scoreboard, members, suggestions. */
import { h, replace } from '../components/dom.js';
import { icon } from '../components/icons.js';
import { scoreOrbit, eventCover } from '../components/brand.js';
import {
  load, emptyState, pageHead, eventCard, memberCard, avatar, pagination, searchBox, chipGroup, typeBadge,
  pointsChip, statusPill, socialLinks, toast, confirmDialog, withBusy, field, showErrors, clearErrors, formData, quietly,
} from '../components/ui.js';
import { onLive } from '../app/router.js';
import { api } from '../services/api.js';
import { session } from '../state/session.js';
import {
  TYPE_SHORT, TYPE_POINTS, EVENT_TYPES, formatDay, formatTime, formatPrice, formatDate, relative, plural, ordinal,
  firstName, isPast, SUGGESTION_STATUS,
} from '../services/format.js';

// ---------------------------------------------------------------- Home (FR-17)
export async function homePage() {
  const [profile, upcoming, messages] = await Promise.all([
    api('/members/me'),
    api('/events', { query: { when: 'upcoming', pageSize: 4 } }),
    api('/messages', { query: { pageSize: 4 } }),
  ]);
  session.setProfile(profile);
  const rank = profile.rank;
  const validated = (profile.participations || []).filter((p) => p.status === 'VALIDATED').length;
  const weekAgo = Date.now() - 7 * 86400 * 1000;

  return h('div', {},
    h('section', { class: 'home-hero', 'aria-labelledby': 'home-title' },
      h('div', {},
        h('h1', { id: 'home-title', 'data-page-title': '', tabindex: '-1' }, `Bonjour ${firstName(profile.name)}`),
        h('p', validated
          ? `Vous avez participé à ${plural(validated, 'événement validé', 'événements validés')} avec ATAST. Chaque participation compte dans le classement du club.`
          : 'Bienvenue dans l’espace membre d’ATAST. Inscrivez-vous à un événement : chaque participation validée vous rapporte des points.'),
        rank ? h('div', { class: 'rank-line' },
          h('span', { class: 'num' }, ordinal(rank.rank)),
          h('span', `sur ${plural(rank.total, 'membre', 'membres')} au classement`)) : null,
        h('div', { class: 'row', style: { 'margin-top': '16px' } },
          h('a', { class: 'btn', href: '/scoreboard', 'data-link': '' }, icon('trophy'), 'Voir le classement'),
          h('a', { class: 'btn btn--secondary', href: '/events', 'data-link': '' }, 'Tous les événements'))),
      scoreOrbit(profile.score)),

    h('div', { class: 'home-cols' },
      h('section', { 'aria-labelledby': 'up-title' },
        h('div', { class: 'section-head' },
          h('h2', { id: 'up-title' }, 'Prochains événements'),
          h('a', { href: '/events', 'data-link': '' }, 'Tout voir')),
        upcoming.items.length
          ? h('div', { class: 'event-list' }, upcoming.items.map((e) => eventCard(e)))
          : emptyState({ title: 'Aucun événement programmé', text: 'Les prochains événements du club apparaîtront ici dès leur publication.' })),
      h('section', { 'aria-labelledby': 'ann-title' },
        h('div', { class: 'section-head' }, h('h2', { id: 'ann-title' }, 'Annonces du bureau')),
        messages.items.length
          ? h('ul', { class: 'announcements' }, messages.items.map((m) => h('li', { class: ['announcement', new Date(m.createdAt).getTime() > weekAgo && 'is-new'] },
            h('h3', m.title),
            h('time', { datetime: m.createdAt }, `${m.author}, ${relative(m.createdAt)}`),
            h('p', m.content))))
          : emptyState({ title: 'Pas encore d’annonce', text: 'Les messages envoyés par l’administration à tous les membres s’afficheront ici.' }))));
}

// ---------------------------------------------------------------- Event library (FR-10)
export function eventsPage({ query }) {
  const state = { q: query.q || '', type: query.type || '', when: query.when === 'past' ? 'past' : 'upcoming', page: 1 };
  const results = h('div', { 'aria-live': 'polite' });

  const refresh = () => load(results,
    () => api('/events', { query: { q: state.q, type: state.type, when: state.when, page: state.page } }),
    (data) => {
      if (!data.items.length) {
        return emptyState({
          title: state.q || state.type ? 'Aucun événement ne correspond' : state.when === 'upcoming' ? 'Aucun événement à venir' : 'Aucun événement passé',
          text: state.q || state.type ? 'Modifiez la recherche ou retirez le filtre de type.' : 'Revenez bientôt : le bureau publie les nouveaux événements ici.',
        });
      }
      return h('div', {},
        h('p', { class: 'small muted' }, plural(data.total, 'événement', 'événements')),
        h('div', { class: 'event-grid' }, data.items.map((e) => eventCard(e))),
        pagination(data, (p) => { state.page = p; refresh(); }, ['événement', 'événements']));
    });

  onLive(['events'], () => quietly(refresh), { container: results });
  const typeOptions = [['', 'Tous'], ...EVENT_TYPES.map((t) => [t, `${TYPE_SHORT[t]} (${TYPE_POINTS[t]} pts)`])];
  const page = h('div', {},
    pageHead({ title: 'Événements', lead: 'Ateliers, conférences, sorties et réunions du club. Le type de chaque événement fixe les points gagnés quand votre participation est validée.' }),
    h('div', { class: 'toolbar' },
      searchBox({ label: 'Rechercher un événement', placeholder: 'Rechercher par titre ou lieu', value: state.q, onSearch: (q) => { state.q = q; state.page = 1; refresh(); } }),
      h('div', { class: 'segmented', role: 'radiogroup', 'aria-label': 'Période' },
        [['upcoming', 'À venir'], ['past', 'Passés']].map(([v, l]) => h('label', {},
          h('input', { type: 'radio', name: 'when', value: v, checked: state.when === v, onChange: () => { state.when = v; state.page = 1; refresh(); } }),
          h('span', l))))),
    h('div', { class: 'toolbar' }, chipGroup({ label: 'Filtrer par type', options: typeOptions, value: state.type, onChange: (t) => { state.type = t; state.page = 1; refresh(); } })),
    results);
  refresh();
  return page;
}

// ---------------------------------------------------------------- Event detail
export async function eventDetailPage({ params, setTitle }) {
  const e = await api(`/events/${params.id}`);
  setTitle(e.title);
  const regBox = h('div', { class: 'register-box' });

  function paintRegistration(ev) {
    let content;
    if (session.isAdmin) {
      content = h('a', { class: 'btn btn--secondary btn--block', href: `/admin/events/${ev.id}`, 'data-link': '' }, 'Gérer cet événement');
    } else if (ev.myParticipation === 'VALIDATED') {
      content = h('div', { class: 'alert alert--success' }, icon('check'), h('p', ev.points
        ? `Participation validée : ${ev.points} points ajoutés à votre score.`
        : 'Participation validée. Les réunions ne rapportent pas de points.'));
    } else if (ev.myParticipation === 'REGISTERED') {
      const btn = h('button', { class: 'btn btn--secondary btn--block', type: 'button' }, 'Annuler mon inscription');
      btn.addEventListener('click', async () => {
        const ok = await confirmDialog({ title: 'Annuler votre inscription ?', message: `Vous ne serez plus inscrit à « ${ev.title} ». Vous pourrez vous réinscrire tant que l’événement n’a pas eu lieu.`, confirmLabel: 'Annuler l’inscription' });
        if (!ok) return;
        withBusy(btn, async () => {
          try {
            await api(`/events/${ev.id}/participation`, { method: 'DELETE' });
            toast('Inscription annulée.');
            paintRegistration({ ...ev, myParticipation: null });
          } catch (err) { toast(err.message, 'error'); }
        });
      });
      content = [h('div', { class: 'alert alert--info' }, icon('info'), h('p', 'Vous êtes inscrit. Les points seront ajoutés quand le bureau validera votre présence.')), btn];
    } else if (ev.canRegister) {
      const btn = h('button', { class: 'btn btn--block', type: 'button' }, 'M’inscrire à l’événement');
      btn.addEventListener('click', () => withBusy(btn, async () => {
        try {
          await api(`/events/${ev.id}/participation`, { method: 'POST' });
          toast('Inscription enregistrée.');
          paintRegistration({ ...ev, myParticipation: 'REGISTERED' });
        } catch (err) { toast(err.message, 'error'); }
      }));
      content = [btn, h('p', { class: 'small muted' }, ev.points ? `Votre présence validée vous rapportera ${ev.points} points.` : 'Les réunions ne rapportent pas de points, mais votre présence compte.')];
    } else {
      content = h('p', { class: 'muted' }, isPast(ev.date) ? 'Cet événement a eu lieu. Les inscriptions sont fermées.' : 'Les inscriptions ne sont pas ouvertes pour cet événement.');
    }
    replace(regBox, content);
  }
  paintRegistration(e);

  const fact = (ic, label, value) => h('div', { class: 'fact' }, h('span', { class: 'fact__icon' }, icon(ic)), h('div', {}, h('small', label), h('b', value)));

  return h('div', {},
    h('a', { class: 'back-link', href: '/events', 'data-link': '' }, icon('left'), 'Événements'),
    e.imageUrl
      ? h('img', { class: 'event-hero__img', src: e.imageUrl, alt: '' })
      : h('div', { class: ['event-cover', `event-cover--${e.type}`] }, eventCover(e.id, e.type)),
    h('div', { class: 'event-hero' },
      h('article', {},
        h('div', { class: 'row' }, typeBadge(e.type), pointsChip(e.points), e.status === 'COMPLETED' ? statusPill('event', 'COMPLETED') : null),
        h('h1', { class: 'event-title', 'data-page-title': '', tabindex: '-1' }, e.title),
        e.description ? h('div', { class: 'prose' }, e.description) : h('p', { class: 'muted' }, 'Aucune description pour le moment.'),
        e.additionalInfo ? h('div', { class: 'alert alert--info', style: { 'margin-top': '24px' } }, icon('info'), h('p', e.additionalInfo)) : null),
      h('aside', { class: 'panel sticky-side', 'aria-label': 'Informations pratiques' },
        h('div', { class: 'facts' },
          fact('calendar', 'Date', formatDay(e.date)),
          fact('clock', 'Heure', formatTime(e.time)),
          fact('pin', 'Lieu', e.location),
          fact('ticket', 'Tarif', formatPrice(e)),
          fact('users', 'Participants validés', String(e.validatedCount))),
        regBox)));
}

// ---------------------------------------------------------------- Scoreboard (FR-24)
export function scoreboardPage() {
  const state = { page: 1 };
  const list = h('div', {});
  const myId = session.user.id;

  const refresh = () => load(list, () => api('/scoreboard', { query: { page: state.page, pageSize: 50 } }), (data) => {
    if (!data.items.length) return emptyState({ title: 'Le classement est vide', text: 'Il apparaîtra dès que des membres auront été acceptés.' });
    const max = Math.max(...data.items.map((r) => r.score), 1);
    return h('div', {},
      h('ol', { class: 'board', 'aria-label': 'Classement des membres par score' },
        data.items.map((r) => {
          const pct = Math.round((r.score / max) * 100);
          const bar = h('span', {});
          bar.style.setProperty('width', `${Math.max(pct, r.score ? 3 : 0)}%`);
          const me = r.memberId === myId;
          return h('li', { class: ['board-row', r.rank <= 3 && 'board-row--top', `board-row--${r.rank}`, me && 'board-row--me'], 'aria-current': me ? 'true' : undefined },
            h('span', { class: 'board-row__rank', 'aria-label': `Rang ${r.rank}` }, String(r.rank)),
            avatar({ name: r.name, avatarUrl: r.avatarUrl }),
            h('div', { class: 'grow' },
              h('div', { class: 'board-row__name' },
                session.isMember || session.isAdmin ? h('a', { href: session.isAdmin ? `/admin/members/${r.memberId}` : `/members/${r.memberId}`, 'data-link': '' }, r.name) : r.name,
                me ? h('span', { class: 'you-tag' }, 'vous') : null),
              h('div', { class: 'board-row__bar', 'aria-hidden': 'true' }, bar)),
            h('span', { class: 'board-row__score' }, String(r.score), h('small', 'pts')));
        })),
      pagination(data, (p) => { state.page = p; refresh(); }, ['membre', 'membres']));
  }, { skeleton: 'row', count: 8 });

  refresh();
  onLive(['scoreboard'], () => quietly(refresh), { container: list });
  return h('div', {},
    pageHead({ title: 'Classement', lead: 'Membres actifs classés par points. Seules les participations validées par le bureau comptent ; à égalité, l’ordre alphabétique départage.' }),
    h('div', { class: 'rules', 'aria-label': 'Barème des points' },
      EVENT_TYPES.map((t) => h('div', { class: 'rule' }, typeBadge(t, { short: true }), h('b', `${TYPE_POINTS[t]} pts`)))),
    list);
}

// ---------------------------------------------------------------- Members list (FR-19)
export function membersPage({ query }) {
  const state = { q: query.q || '', page: 1 };
  const results = h('div', { 'aria-live': 'polite' });
  const refresh = () => load(results, () => api('/members', { query: { q: state.q, page: state.page } }), (data) => {
    if (!data.items.length) return emptyState({ title: state.q ? `Aucun membre ne s’appelle « ${state.q} »` : 'Aucun membre pour le moment', text: state.q ? 'Vérifiez l’orthographe ou cherchez avec le prénom seul.' : null });
    return h('div', {},
      h('p', { class: 'small muted' }, plural(data.total, 'membre actif', 'membres actifs')),
      h('div', { class: 'member-grid' }, data.items.map((m) => memberCard(m))),
      pagination(data, (p) => { state.page = p; refresh(); }, ['membre', 'membres']));
  }, { skeleton: 'row', count: 6 });
  refresh();
  onLive(['members'], () => quietly(refresh), { container: results });
  return h('div', {},
    pageHead({ title: 'Membres', lead: 'Les membres actifs du club. Seules les informations publiques sont visibles : nom, photo, présentation et réseaux.' }),
    h('div', { class: 'toolbar' }, searchBox({ label: 'Rechercher un membre', placeholder: 'Rechercher par nom', value: state.q, onSearch: (q) => { state.q = q; state.page = 1; refresh(); } })),
    results);
}

export async function memberDetailPage({ params, setTitle }) {
  const m = await api(`/members/${params.id}`);
  setTitle(m.name);
  return h('div', {},
    h('a', { class: 'back-link', href: '/members', 'data-link': '' }, icon('left'), 'Membres'),
    h('div', { class: 'profile-head' },
      avatar(m, { size: 'xl', decorative: false }),
      h('div', {},
        h('h1', { 'data-page-title': '', tabindex: '-1' }, m.name),
        h('p', { class: 'muted' }, `Membre depuis ${formatDate(m.memberSince)}`)),
      scoreOrbit(m.score, { small: true })),
    h('section', { class: 'panel stack', 'aria-label': 'Présentation' },
      h('h2', 'Présentation'),
      m.description ? h('p', { class: 'prose' }, m.description) : h('p', { class: 'muted' }, `${firstName(m.name)} n’a pas encore rédigé de présentation.`),
      socialLinks(m.socials)));
}

// ---------------------------------------------------------------- Suggestion box (FR-16)
export function suggestionsPage() {
  const mine = h('div', {});
  const refreshMine = () => load(mine, () => api('/suggestions/mine'), (data) => (data.items.length
    ? h('ul', { class: 'item-list' }, data.items.map((s) => h('li', { class: 'item' },
      h('div', { class: 'item__head' },
        h('span', { class: 'item__title' }, s.title || 'Suggestion sans titre'),
        statusPill('suggestion', s.status)),
      h('p', s.content),
      h('div', { class: 'item__meta', style: { 'margin-top': '8px' } }, `Envoyée ${relative(s.createdAt)}`))))
    : emptyState({ title: 'Aucune suggestion envoyée', text: 'Vos suggestions et leur suivi par le bureau apparaîtront ici.' })), { skeleton: 'row', count: 2 });

  const submit = h('button', { class: 'btn', type: 'submit' }, icon('send'), 'Envoyer la suggestion');
  const form = h('form', { class: 'form', novalidate: true },
    field({ label: 'Titre', name: 'title', optional: true, maxlength: 140 }),
    field({ label: 'Votre suggestion', name: 'content', multiline: true, required: true, maxlength: 3000, rows: 7, hint: 'Une idée d’atelier, une amélioration, une remarque sur la vie du club.' }),
    h('div', { class: 'row' }, submit));

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const data = formData(form);
    if (!data.content || data.content.trim().length < 5) return showErrors(form, { fields: { content: 'Votre suggestion doit contenir au moins 5 caractères.' } });
    clearErrors(form);
    withBusy(submit, async () => {
      try {
        await api('/suggestions', { method: 'POST', body: data });
        form.reset();
        form.querySelectorAll('textarea').forEach((t) => t.dispatchEvent(new Event('input')));
        toast('Suggestion envoyée au bureau. Merci !');
        refreshMine();
      } catch (err) { showErrors(form, err); }
    });
  });

  refreshMine();
  onLive(['suggestions'], () => quietly(refreshMine), { container: mine });
  return h('div', {},
    pageHead({ title: 'Boîte à suggestions', lead: 'Vos suggestions sont transmises à l’administration du club, qui indique où en est leur traitement.' }),
    h('div', { class: 'two-col' },
      h('section', { class: 'panel', 'aria-labelledby': 'sug-new' }, h('h2', { id: 'sug-new', style: { 'margin-bottom': '16px' } }, 'Nouvelle suggestion'), form),
      h('section', { 'aria-labelledby': 'sug-mine' }, h('div', { class: 'section-head' }, h('h2', { id: 'sug-mine' }, 'Mes suggestions')), mine)));
}

export { SUGGESTION_STATUS };
