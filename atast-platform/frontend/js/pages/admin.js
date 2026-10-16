/** Admin interface pages: dashboard, requests, members, messages, suggestions. */
import { h, replace } from '../components/dom.js';
import { icon } from '../components/icons.js';
import { scoreOrbit } from '../components/brand.js';
import {
  load, emptyState, pageHead, avatar, pagination, searchBox, typeBadge, pointsChip, statusPill, paidPill, socialLinks,
  toast, confirmDialog, openModal, withBusy, field, showErrors, clearErrors, formData, eventCard, quietly,
} from '../components/ui.js';
import { onLive, navigate } from '../app/router.js';
import { api } from '../services/api.js';
import { refreshAdminCounts } from '../layouts/admin.js';
import {
  REQUEST_STATUS, MEMBER_STATUS, SUGGESTION_STATUS, formatDate, formatDateTime, formatDay, relative, plural, ordinal,
  currentSeason, seasonOptions, formatAmount,
} from '../services/format.js';

// ---------------------------------------------------------------- Dashboard
const ACTIVITY = {
  MEMBERSHIP_ACCEPTED: (m) => `a accepté la demande de ${m?.email || 'un candidat'}`,
  MEMBERSHIP_REJECTED: (m) => `a refusé la demande de ${m?.email || 'un candidat'}`,
  EVENT_CREATED: (m) => `a créé l’événement « ${m?.title} »`,
  EVENT_UPDATED: (m) => (m?.typeFrom ? `a modifié « ${m.title} » (points recalculés)` : `a modifié « ${m?.title} »`),
  EVENT_ARCHIVED: (m) => `a archivé « ${m?.title} »`,
  EVENT_IMAGE_UPDATED: () => 'a changé l’image d’un événement',
  EVENT_IMAGE_REMOVED: () => 'a retiré l’image d’un événement',
  PARTICIPATION_VALIDATED: (m) => `a validé une participation (${m?.points ?? 0} pts)`,
  PARTICIPATION_REMOVED: () => 'a retiré une participation',
  MESSAGE_SENT: (m) => `a envoyé le message « ${m?.title} »`,
  SUGGESTION_STATUS_CHANGED: () => 'a mis à jour le statut d’une suggestion',
  MEMBERSHIP_AUTO_ACCEPTED: (m) => `Adhésion de ${m?.email || 'un candidat'} acceptée automatiquement (cotisation payée)`,
  SUBSCRIPTIONS_IMPORTED: (m) => `a importé « ${m?.filename} » (${m?.imported ?? 0} ajoutées, ${m?.autoAccepted ?? 0} acceptées automatiquement)`,
  SUBSCRIPTION_ADDED: (m) => `a ajouté la cotisation de ${m?.email || 'un membre'}`,
  SUBSCRIPTION_REVOKED: (m) => `a retiré la cotisation de ${m?.email || 'un candidat'}`,
  IMPORT_REVERTED: (m) => `a annulé l’import « ${m?.filename} »`,
  MEMBER_UPDATED: () => 'a corrigé les informations d’un membre',
  MEMBER_STATUS_CHANGED: (m) => `a changé le statut d’un membre (${MEMBER_STATUS[m?.to] || m?.to})`,
};

export async function dashboardPage() {
  const [stats, upcoming] = await Promise.all([
    refreshAdminCounts().then((s) => s || api('/admin/stats')),
    api('/admin/events', { query: { when: 'upcoming', status: 'PUBLISHED', pageSize: 3 } }),
  ]);
  const stat = (href, value, label, attention, note) => h('a', { class: ['stat', attention && 'stat--attention'], href, 'data-link': '' },
    h('span', { class: 'stat__value' }, String(value)),
    h('span', { class: 'stat__label' }, label),
    attention && note ? h('span', { class: 'stat__note' }, note) : null);

  return h('div', {},
    pageHead({
      title: 'Tableau de bord',
      lead: 'Vue d’ensemble du club et des actions qui vous attendent.',
      actions: [
        h('a', { class: 'btn btn--secondary', href: '/admin/messages', 'data-link': '' }, icon('send'), 'Envoyer un message'),
        h('a', { class: 'btn', href: '/admin/events/new', 'data-link': '' }, icon('plus'), 'Créer un événement'),
      ],
    }),
    h('section', { class: 'stats', 'aria-label': 'Statistiques' },
      stat('/admin/requests', stats.pendingRequests, 'Demandes en attente', stats.pendingRequests > 0, 'À examiner'),
      stat('/admin/members', stats.activeMembers, 'Membres actifs'),
      stat('/admin/subscriptions', stats.subscriptions.paidMembers, `Cotisations ${stats.subscriptions.season} payées`),
      stat('/admin/members?subscription=unpaid', stats.subscriptions.unpaidMembers, 'Membres sans cotisation', stats.subscriptions.unpaidMembers > 0, 'À relancer'),
      stat('/admin/subscriptions', stats.subscriptions.awaitingRegistration, 'Payées, pas encore inscrites'),
      stat('/admin/events', stats.upcomingEvents, 'Événements à venir'),
      stat('/admin/events', stats.totalEvents, 'Événements enregistrés'),
      stat('/admin/events', stats.validatedParticipations, 'Participations validées'),
      stat('/admin/suggestions', stats.newSuggestions, 'Nouvelles suggestions', stats.newSuggestions > 0, 'À lire')),
    h('div', { class: 'home-cols', style: { 'margin-top': '32px' } },
      h('section', { 'aria-labelledby': 'dash-up' },
        h('div', { class: 'section-head' }, h('h2', { id: 'dash-up' }, 'Prochains événements publiés'), h('a', { href: '/admin/events', 'data-link': '' }, 'Gérer les événements')),
        upcoming.items.length
          ? h('div', { class: 'event-list' }, upcoming.items.map((e) => eventCard(e, { href: `/admin/events/${e.id}` })))
          : emptyState({ title: 'Aucun événement publié à venir', text: 'Créez un événement et publiez-le pour que les membres puissent s’inscrire.', action: h('a', { class: 'btn', href: '/admin/events/new', 'data-link': '' }, icon('plus'), 'Créer un événement') })),
      h('section', { class: 'panel', 'aria-labelledby': 'dash-act' },
        h('div', { class: 'panel__head' }, h('h2', { id: 'dash-act' }, 'Activité récente')),
        stats.recentActivity.length
          ? h('ul', { class: 'activity' }, stats.recentActivity.map((a) => h('li', {},
            h('span', { class: 'dot', 'aria-hidden': 'true' }),
            h('span', {}, h('b', a.actor || 'Système'), ' ', (ACTIVITY[a.action] || (() => a.action))(a.metadata)),
            h('time', { datetime: a.createdAt }, relative(a.createdAt)))))
          : h('p', { class: 'muted' }, 'Les actions de l’administration (demandes traitées, événements, messages) apparaîtront ici.'))));
}

// ---------------------------------------------------------------- Membership requests (FR-02..04)
export function requestsPage({ query }) {
  const state = { status: query.status || 'PENDING', q: '', page: 1 };
  const results = h('div', {});
  const tabs = h('div', { class: 'tabs', role: 'tablist', 'aria-label': 'Statut des demandes' });

  function paintTabs() {
    replace(tabs, [['PENDING', 'En attente'], ['ACCEPTED', 'Acceptées'], ['REJECTED', 'Refusées'], ['', 'Toutes']].map(([v, l]) => h('button', {
      class: 'tab', role: 'tab', type: 'button', 'aria-selected': String(state.status === v), 'aria-controls': 'req-panel',
      onClick: () => { state.status = v; state.page = 1; paintTabs(); refresh(); },
    }, l)));
  }

  async function accept(r, btn) {
    const ok = await confirmDialog({
      title: `Accepter ${r.name} ?`,
      message: `Un compte membre actif sera créé pour ${r.email}. La personne pourra se connecter immédiatement.`,
      confirmLabel: 'Accepter la demande',
    });
    if (!ok) return;
    withBusy(btn, async () => {
      try {
        await api(`/admin/membership-requests/${r.id}/accept`, { method: 'POST' });
        toast(`${r.name} est maintenant membre du club.`);
        refreshAdminCounts();
        refresh();
      } catch (err) { toast(err.message, 'error'); }
    });
  }

  function reject(r) {
    const reason = field({ label: 'Motif du refus', name: 'reason', multiline: true, required: true, maxlength: 500, rows: 4, hint: 'Ce motif sera affiché à la personne si elle tente de se connecter.' });
    const form = h('form', { class: 'form', novalidate: true }, reason);
    const submit = h('button', { class: 'btn btn--danger', type: 'button' }, 'Refuser la demande');
    const m = openModal({
      title: `Refuser la demande de ${r.name}`,
      description: `${r.email}. La demande sera conservée pour le suivi mais ne deviendra pas un compte membre.`,
      body: form,
      actions: [h('button', { class: 'btn btn--secondary', type: 'button', onClick: () => m.close() }, 'Annuler'), submit],
    });
    const send = () => {
      const value = reason.control.value.trim();
      if (value.length < 3) return showErrors(form, { fields: { reason: 'Indiquez un motif d’au moins 3 caractères.' } });
      clearErrors(form);
      withBusy(submit, async () => {
        try {
          await api(`/admin/membership-requests/${r.id}/reject`, { method: 'POST', body: { reason: value } });
          m.close();
          toast(`Demande de ${r.name} refusée.`);
          refreshAdminCounts();
          refresh();
        } catch (err) { showErrors(form, err); }
      });
    };
    submit.addEventListener('click', send);
    form.addEventListener('submit', (e) => { e.preventDefault(); send(); });
    reason.control.focus();
  }

  const refresh = () => load(results, () => api('/admin/membership-requests', { query: { status: state.status, q: state.q, page: state.page } }), (data) => {
    if (!data.items.length) {
      return emptyState(state.status === 'PENDING' && !state.q
        ? { title: 'Aucune demande en attente', text: 'Les nouvelles demandes d’adhésion envoyées depuis la page d’inscription apparaîtront ici.' }
        : { title: 'Aucune demande trouvée', text: 'Modifiez la recherche ou choisissez un autre statut.' });
    }
    return h('div', {},
      h('div', { class: 'panel panel--flush' },
        h('div', { class: 'table-wrap' },
          h('table', { class: 'table table--stack' },
            h('caption', { class: 'sr-only' }, 'Demandes d’adhésion'),
            h('thead', h('tr', h('th', { scope: 'col' }, 'Candidat'), h('th', { scope: 'col' }, 'Téléphone'), h('th', { scope: 'col' }, 'Reçue'), h('th', { scope: 'col' }, 'Statut'), h('th', { scope: 'col' }, h('span', { class: 'sr-only' }, 'Actions')))),
            h('tbody', data.items.map((r) => {
              const acceptBtn = h('button', { class: 'btn btn--sm', type: 'button' }, icon('check'), 'Accepter');
              acceptBtn.addEventListener('click', () => accept(r, acceptBtn));
              return h('tr', {},
                h('td', {}, h('b', { class: 'nowrap' }, r.name), h('div', { class: 'small muted' }, r.email),
                  r.status === 'REJECTED' && r.rejectionReason ? h('div', { class: 'small', style: { color: 'var(--danger)', 'margin-top': '4px' } }, `Motif : ${r.rejectionReason}`) : null),
                h('td', { 'data-label': 'Téléphone' }, h('a', { href: `tel:${r.phone}` }, r.phone)),
                h('td', { 'data-label': 'Reçue' }, h('time', { datetime: r.createdAt, title: formatDateTime(r.createdAt) }, relative(r.createdAt))),
                h('td', { 'data-label': 'Statut' }, statusPill('request', r.status), r.autoAccepted ? h('div', { class: 'small muted' }, 'automatiquement (cotisation payée)') : r.reviewerName ? h('div', { class: 'small muted' }, `par ${r.reviewerName}`) : null,
                  r.status === 'PENDING' && r.onPaidList ? h('div', { class: 'small', style: { color: 'var(--blue)' } }, 'Sur la liste des cotisations (téléphone différent)') : null),
                h('td', {}, r.status === 'PENDING'
                  ? h('div', { class: 'actions' }, acceptBtn, h('button', { class: 'btn btn--danger-ghost btn--sm', type: 'button', onClick: () => reject(r) }, 'Refuser'))
                  : null));
            }))))),
      pagination(data, (p) => { state.page = p; refresh(); }, ['demande', 'demandes']));
  }, { skeleton: 'row', count: 4 });

  paintTabs();
  refresh();
  onLive(['requests'], () => quietly(refresh), { container: results });
  return h('div', {},
    pageHead({ title: 'Demandes d’adhésion', lead: 'Acceptez une demande pour créer le compte membre, ou refusez-la en indiquant un motif.' }),
    tabs,
    h('div', { class: 'toolbar' }, searchBox({ label: 'Rechercher une demande', placeholder: 'Rechercher par nom ou email', onSearch: (q) => { state.q = q; state.page = 1; refresh(); } })),
    h('div', { id: 'req-panel', role: 'tabpanel' }, results));
}

// ---------------------------------------------------------------- Member library (FR-05)
export function adminMembersPage({ query }) {
  const state = { q: query.q || '', status: 'ACTIVE', subscription: ['paid', 'unpaid'].includes(query.subscription) ? query.subscription : '', season: currentSeason(), page: 1 };
  const results = h('div', {});
  const exportLink = h('a', { class: 'btn btn--secondary', href: '#' }, icon('download'), 'Exporter en Excel');
  const paintExport = () => exportLink.setAttribute('href', `/api/admin/downloads/members?${new URLSearchParams({ status: state.status, season: state.season })}`);
  const refresh = () => load(results, () => api('/admin/members', { query: state }), (data) => {
    if (!data.items.length) return emptyState({ title: state.q ? 'Aucun membre trouvé' : 'Aucun membre dans cette catégorie', text: state.q ? 'La recherche porte sur le nom et l’adresse email.' : 'Les membres apparaissent ici dès qu’une demande d’adhésion est acceptée.' });
    return h('div', {},
      h('p', { class: 'small muted' }, plural(data.total, 'membre', 'membres')),
      h('div', { class: 'panel panel--flush' },
        h('div', { class: 'table-wrap' },
          h('table', { class: 'table table--stack' },
            h('caption', { class: 'sr-only' }, 'Bibliothèque des membres'),
            h('thead', h('tr', h('th', { scope: 'col' }, 'Membre'), h('th', { scope: 'col' }, 'Score'), h('th', { scope: 'col' }, `Cotisation ${data.season}`), h('th', { scope: 'col' }, 'Statut'), h('th', { scope: 'col' }, 'Membre depuis'), h('th', { scope: 'col' }, h('span', { class: 'sr-only' }, 'Profil')))),
            h('tbody', data.items.map((m) => h('tr', {},
              h('td', {}, h('div', { class: 'cell-person' }, avatar(m), h('div', {}, h('a', { class: 'cell-link', href: `/admin/members/${m.id}`, 'data-link': '' }, m.name), h('div', { class: 'small muted' }, m.email)))),
              h('td', { 'data-label': 'Score' }, h('span', { class: 'num' }, `${m.score} pts`)),
              h('td', { 'data-label': 'Cotisation' }, paidPill(m.subscription.paid)),
              h('td', { 'data-label': 'Statut' }, statusPill('member', m.status)),
              h('td', { 'data-label': 'Membre depuis' }, formatDate(m.memberSince)),
              h('td', {}, h('div', { class: 'actions' }, h('a', { class: 'btn btn--ghost btn--sm', href: `/admin/members/${m.id}`, 'data-link': '' }, 'Voir le profil'))))))))),
      pagination(data, (p) => { state.page = p; refresh(); }, ['membre', 'membres']));
  }, { skeleton: 'row', count: 6 });

  const statusSel = h('select', { class: 'select', 'aria-label': 'Filtrer par statut', onChange: (e) => { state.status = e.target.value; state.page = 1; paintExport(); refresh(); } },
    [['ACTIVE', 'Membres actifs'], ['SUSPENDED', 'Suspendus'], ['DEACTIVATED', 'Désactivés'], ['ANY', 'Tous les statuts']].map(([v, l]) => h('option', { value: v }, l)));
  const subSel = h('select', { class: 'select', 'aria-label': 'Filtrer par cotisation', onChange: (e) => { state.subscription = e.target.value; state.page = 1; refresh(); } },
    [['', 'Toutes les cotisations'], ['paid', 'Cotisation payée'], ['unpaid', 'Cotisation non payée']].map(([v, l]) => h('option', { value: v, selected: v === state.subscription }, l)));
  paintExport();
  refresh();
  onLive(['members', 'subscriptions'], () => quietly(refresh), { container: results });
  return h('div', {},
    pageHead({
      title: 'Membres',
      lead: 'Tous les membres du club avec leur score et leur cotisation. Ouvrez un profil pour voir et corriger les coordonnées, l’historique des participations et les paiements.',
      actions: [exportLink, h('a', { class: 'btn', href: '/admin/subscriptions', 'data-link': '' }, icon('ticket'), 'Cotisations')],
    }),
    h('div', { class: 'toolbar' },
      searchBox({ label: 'Rechercher un membre', placeholder: 'Rechercher par nom ou email', value: state.q, onSearch: (q) => { state.q = q; state.page = 1; refresh(); } }),
      statusSel, subSel),
    results);
}

// ---------------------------------------------------------------- Admin member profile (FR-06)
export async function adminMemberDetailPage({ params, setTitle }) {
  let m = await api(`/admin/members/${params.id}`);
  setTitle(m.name);
  const statusSlot = h('div', { class: 'row' });

  function paintStatus() {
    const actions = [];
    const change = (status, label, message, danger) => {
      const btn = h('button', { class: ['btn', 'btn--sm', danger ? 'btn--danger-ghost' : 'btn--secondary'], type: 'button' }, label);
      btn.addEventListener('click', async () => {
        const ok = await confirmDialog({ title: `${label} ?`, message, confirmLabel: label, danger });
        if (!ok) return;
        withBusy(btn, async () => {
          try {
            const updated = await api(`/admin/members/${m.id}/status`, { method: 'PATCH', body: { status } });
            m = { ...m, status: updated.status };
            paintStatus();
            toast(`Statut mis à jour : ${MEMBER_STATUS[status]}.`);
          } catch (err) { toast(err.message, 'error'); }
        });
      });
      actions.push(btn);
    };
    if (m.status === 'ACTIVE') {
      change('SUSPENDED', 'Suspendre le compte', `${m.name} ne pourra plus se connecter jusqu’à réactivation. Son historique et ses points sont conservés.`, false);
      change('DEACTIVATED', 'Désactiver le compte', `${m.name} sera retiré de la liste des membres et du classement. Son historique est conservé et le compte peut être réactivé.`, true);
    } else {
      change('ACTIVE', 'Réactiver le compte', `${m.name} pourra de nouveau se connecter et apparaîtra au classement.`, false);
    }
    replace(statusSlot, statusPill('member', m.status), actions);
  }
  paintStatus();

  const parts = m.participations;
  const validated = parts.filter((p) => p.status === 'VALIDATED');

  function editDialog() {
    const form = h('form', { class: 'form', novalidate: true },
      field({ label: 'Nom complet', name: 'name', value: m.name, required: true, maxlength: 80 }),
      field({ label: 'Adresse email', name: 'email', type: 'email', value: m.email, required: true, hint: 'Le membre se connecte avec cette adresse.' }),
      field({ label: 'Téléphone', name: 'phone', type: 'tel', value: m.phone, required: true }),
      field({ label: 'Date de naissance', name: 'birthday', type: 'date', value: m.birthday || '', optional: true }));
    const submit = h('button', { class: 'btn', type: 'submit' }, 'Enregistrer');
    const dlg = openModal({
      title: `Modifier ${m.name}`,
      description: 'Corrigez les informations d’identité du membre. Le mot de passe, le score et le rôle ne sont pas modifiables ici.',
      body: form,
      actions: [h('button', { class: 'btn btn--secondary', type: 'button', onClick: () => dlg.close() }, 'Annuler'), submit],
    });
    submit.addEventListener('click', () => form.requestSubmit());
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      clearErrors(form);
      withBusy(submit, async () => {
        try {
          await api(`/admin/members/${m.id}`, { method: 'PUT', body: formData(form) });
          dlg.close();
          toast('Informations du membre mises à jour.');
          navigate(location.pathname);
        } catch (err) { showErrors(form, err); }
      });
    });
  }

  function paymentDialog() {
    const form = h('form', { class: 'form', novalidate: true },
      field({ label: 'Saison', name: 'season', options: seasonOptions().map((x) => [x, x]), value: m.subscription.season }),
      field({ label: 'Montant (DT)', name: 'amount', optional: true, inputmode: 'decimal', hint: 'Exemple : 25 ou 25,500' }),
      field({ label: 'Date de paiement', name: 'paidAt', type: 'date', optional: true }),
      field({ label: 'Référence du reçu', name: 'reference', optional: true, maxlength: 60 }));
    const submit = h('button', { class: 'btn', type: 'submit' }, 'Enregistrer le paiement');
    const dlg = openModal({
      title: `Cotisation de ${m.name}`,
      body: form,
      actions: [h('button', { class: 'btn btn--secondary', type: 'button', onClick: () => dlg.close() }, 'Annuler'), submit],
    });
    submit.addEventListener('click', () => form.requestSubmit());
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      clearErrors(form);
      withBusy(submit, async () => {
        try {
          await api(`/admin/members/${m.id}/subscriptions`, { method: 'POST', body: formData(form) });
          dlg.close();
          toast('Cotisation enregistrée.');
          navigate(location.pathname);
        } catch (err) { showErrors(form, err); }
      });
    });
  }

  return h('div', {},
    h('a', { class: 'back-link', href: '/admin/members', 'data-link': '' }, icon('left'), 'Membres'),
    h('div', { class: 'profile-head' },
      avatar(m, { size: 'xl', decorative: false }),
      h('div', {},
        h('h1', { 'data-page-title': '', tabindex: '-1' }, m.name),
        h('p', { class: 'muted' }, `Membre depuis ${formatDate(m.memberSince)}`, m.rank ? `, ${ordinal(m.rank.rank)} sur ${m.rank.total} au classement` : ''),
        statusSlot,
        h('div', { class: 'row', style: { 'margin-top': '12px' } },
          h('button', { class: 'btn btn--secondary btn--sm', type: 'button', onClick: editDialog }, icon('edit'), 'Modifier les informations'))),
      scoreOrbit(m.score, { small: true })),
    h('div', { class: 'profile-cols' },
      h('section', { class: 'panel', 'aria-labelledby': 'hist' },
        h('div', { class: 'panel__head' }, h('h2', { id: 'hist' }, 'Historique des participations'), h('span', { class: 'muted small' }, plural(validated.length, 'participation validée', 'participations validées'))),
        parts.length
          ? h('div', {},
            h('ul', { class: 'history' }, parts.map((p) => h('li', {},
              h('a', { href: `/admin/events/${p.event.id}`, 'data-link': '' }, p.event.title),
              p.status === 'VALIDATED' ? pointsChip(p.pointsAwarded) : statusPill('participation', 'REGISTERED'),
              h('div', { class: 'meta' }, typeBadge(p.event.type, { short: true }), formatDay(p.event.date, { day: 'numeric', month: 'short', year: 'numeric' }), p.event.status === 'ARCHIVED' ? statusPill('event', 'ARCHIVED') : null)))),
            h('div', { class: 'score-sum' }, h('span', 'Score total'), h('span', { class: 'num' }, `${m.score} pts`)))
          : h('p', { class: 'muted' }, 'Ce membre n’a encore participé à aucun événement.')),
      h('div', { class: 'stack' },
        h('section', { class: 'panel', 'aria-labelledby': 'coords' },
          h('h2', { id: 'coords', style: { 'margin-bottom': '16px' } }, 'Coordonnées'),
          h('dl', { class: 'dl' },
            h('dt', 'Email'), h('dd', h('a', { href: `mailto:${m.email}` }, m.email)),
            h('dt', 'Téléphone'), h('dd', h('a', { href: `tel:${m.phone}` }, m.phone)),
            h('dt', 'Date de naissance'), h('dd', m.birthday ? formatDay(m.birthday, { day: 'numeric', month: 'long', year: 'numeric' }) : h('span', { class: 'muted' }, 'Non renseignée')))),
        h('section', { class: 'panel', 'aria-labelledby': 'subs' },
          h('div', { class: 'panel__head' }, h('h2', { id: 'subs' }, 'Cotisations'), paidPill(m.subscription.paid)),
          m.subscriptions.length
            ? h('ul', { class: 'history' }, m.subscriptions.map((x) => h('li', {},
              h('span', {}, h('b', `Saison ${x.season}`), x.paidAt ? ` · payée le ${formatDay(x.paidAt, { day: 'numeric', month: 'short', year: 'numeric' })}` : ''),
              h('span', { class: 'small muted' }, [formatAmount(x.amount), x.reference ? `reçu ${x.reference}` : null].filter(Boolean).join(' · ')))))
            : h('p', { class: 'muted' }, `Aucune cotisation enregistrée. Saison en cours : ${m.subscription.season}.`),
          m.subscription.paid ? null : h('div', { style: { 'margin-top': '12px' } },
            h('button', { class: 'btn btn--sm', type: 'button', onClick: paymentDialog }, icon('plus'), 'Enregistrer un paiement'))),
        h('section', { class: 'panel stack', 'aria-labelledby': 'about' },
          h('h2', { id: 'about' }, 'Présentation et réseaux'),
          m.description ? h('p', { class: 'prose' }, m.description) : h('p', { class: 'muted' }, 'Pas de présentation.'),
          socialLinks(m.socials) || h('p', { class: 'muted small' }, 'Aucun réseau social renseigné.')))));
}

// ---------------------------------------------------------------- Message Sandbox (FR-15)
export function messagesPage() {
  const history = h('div', {});
  const state = { page: 1 };
  const refresh = () => load(history, () => api('/messages', { query: { page: state.page, pageSize: 10 } }), (data) => (data.items.length
    ? h('div', {},
      h('ul', { class: 'announcements' }, data.items.map((m) => h('li', { class: 'announcement' },
        h('h3', m.title), h('time', { datetime: m.createdAt }, `${m.author}, ${formatDateTime(m.createdAt)}`), h('p', m.content)))),
      pagination(data, (p) => { state.page = p; refresh(); }, ['message', 'messages']))
    : emptyState({ title: 'Aucun message envoyé', text: 'Les messages envoyés apparaissent sur la page d’accueil de chaque membre.' })), { skeleton: 'row', count: 3 });

  const submit = h('button', { class: 'btn', type: 'submit' }, icon('send'), 'Envoyer à tous les membres');
  const form = h('form', { class: 'form', novalidate: true },
    field({ label: 'Titre', name: 'title', required: true, maxlength: 140 }),
    field({ label: 'Message', name: 'content', multiline: true, required: true, maxlength: 5000, rows: 8 }),
    h('div', {}, submit));
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = formData(form);
    const f = {};
    if (!data.title || data.title.trim().length < 3) f.title = 'Le titre doit contenir au moins 3 caractères.';
    if (!data.content || data.content.trim().length < 3) f.content = 'Le message doit contenir au moins 3 caractères.';
    if (Object.keys(f).length) return showErrors(form, { fields: f });
    clearErrors(form);
    let count = null;
    try { count = (await api('/admin/stats')).activeMembers; } catch { /* count is informative only */ }
    const ok = await confirmDialog({
      title: 'Envoyer ce message ?',
      message: `« ${data.title.trim()} » sera visible par ${count === null ? 'tous les membres actifs' : plural(count, 'membre actif', 'membres actifs')} sur leur page d’accueil. Un message envoyé ne peut pas être modifié.`,
      confirmLabel: 'Envoyer le message',
    });
    if (!ok) return;
    withBusy(submit, async () => {
      try {
        await api('/admin/messages', { method: 'POST', body: data });
        form.reset();
        form.querySelectorAll('textarea').forEach((t) => t.dispatchEvent(new Event('input')));
        toast('Message envoyé à tous les membres.');
        state.page = 1;
        refresh();
      } catch (err) { showErrors(form, err); }
    });
  });
  refresh();
  onLive(['messages'], () => quietly(refresh), { container: history });
  return h('div', {},
    pageHead({ title: 'Messages', lead: 'Envoyez une annonce à tous les membres actifs. Elle s’affiche sur leur page d’accueil.', actions: h('a', { class: 'btn btn--secondary', href: '/admin/suggestions', 'data-link': '' }, icon('bulb'), 'Suggestions reçues') }),
    h('div', { class: 'two-col' },
      h('section', { class: 'panel', 'aria-labelledby': 'msg-new' }, h('h2', { id: 'msg-new', style: { 'margin-bottom': '16px' } }, 'Nouveau message'), form),
      h('section', { 'aria-labelledby': 'msg-hist' }, h('div', { class: 'section-head' }, h('h2', { id: 'msg-hist' }, 'Messages envoyés')), history)));
}

// ---------------------------------------------------------------- Suggestions received
export function adminSuggestionsPage() {
  const state = { status: '', page: 1 };
  const tabs = h('div', { class: 'tabs', role: 'tablist', 'aria-label': 'Statut des suggestions' });
  const results = h('div', { id: 'sug-panel', role: 'tabpanel' });
  function paintTabs() {
    replace(tabs, [['', 'Toutes'], ...Object.entries(SUGGESTION_STATUS)].map(([v, l]) => h('button', {
      class: 'tab', role: 'tab', type: 'button', 'aria-selected': String(state.status === v), 'aria-controls': 'sug-panel',
      onClick: () => { state.status = v; state.page = 1; paintTabs(); refresh(); },
    }, l)));
  }
  const refresh = () => load(results, () => api('/admin/suggestions', { query: state }), (data) => {
    if (!data.items.length) return emptyState({ title: 'Aucune suggestion ici', text: 'Les suggestions envoyées par les membres depuis leur boîte à suggestions apparaîtront ici.' });
    return h('div', {},
      h('ul', { class: 'item-list' }, data.items.map((s) => {
        const sel = h('select', { class: 'select', 'aria-label': `Statut de la suggestion de ${s.author.name}` },
          Object.entries(SUGGESTION_STATUS).map(([v, l]) => h('option', { value: v, selected: v === s.status }, l)));
        const item = h('li', { class: ['item', `item--${s.status}`] },
          h('div', { class: 'item__head' },
            h('div', { class: 'row' }, avatar(s.author, { size: 'sm' }), h('div', {}, h('div', { class: 'item__title' }, s.title || 'Suggestion sans titre'), h('div', { class: 'item__meta' }, `${s.author.name}, ${relative(s.createdAt)}`)))),
          h('p', s.content),
          h('div', { class: 'item__foot' }, h('span', { class: 'small muted' }, `Reçue le ${formatDateTime(s.createdAt)}`), h('label', { class: 'row small' }, h('span', { class: 'muted' }, 'Statut'), sel)));
        sel.addEventListener('change', async () => {
          try {
            await api(`/admin/suggestions/${s.id}`, { method: 'PATCH', body: { status: sel.value } });
            item.className = `item item--${sel.value}`;
            toast(`Statut mis à jour : ${SUGGESTION_STATUS[sel.value]}.`);
            refreshAdminCounts();
          } catch (err) {
            sel.value = s.status;
            toast(err.message, 'error');
          }
        });
        return item;
      })),
      pagination(data, (p) => { state.page = p; refresh(); }, ['suggestion', 'suggestions']));
  }, { skeleton: 'row', count: 3 });
  paintTabs();
  refresh();
  onLive(['suggestions'], () => quietly(refresh), { container: results });
  return h('div', {},
    pageHead({ title: 'Suggestions', lead: 'Les idées et remarques des membres. Mettez à jour le statut pour qu’ils suivent le traitement depuis leur boîte à suggestions.' }),
    tabs, results);
}

export { REQUEST_STATUS };
