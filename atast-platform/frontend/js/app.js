/** Application entry: restores the session, declares routes, starts the router. */
import { api, setUnauthorizedHandler } from './services/api.js';
import { session } from './state/session.js';
import { defineRoutes, startRouter, navigate, dispatchChange } from './app/router.js';
import {
  startSync, stopSync, onChange, setRevokedHandler, setAuthCheck, onOtherTab,
} from './services/sync.js';
import { refreshAdminCounts } from './layouts/admin.js';
import { toast } from './components/ui.js';
import { memberLayout } from './layouts/member.js';
import { adminLayout } from './layouts/admin.js';
import { bareLayout, notFound, forbidden } from './layouts/shared.js';
import { loginPage, registerPage } from './pages/auth.js';
import {
  homePage, eventsPage, eventDetailPage, scoreboardPage, membersPage, memberDetailPage, suggestionsPage,
} from './pages/member.js';
import { profilePage } from './pages/profile.js';
import {
  dashboardPage, requestsPage, adminMembersPage, adminMemberDetailPage, messagesPage, adminSuggestionsPage,
} from './pages/admin.js';
import { adminEventsPage, eventFormPage, adminEventDetailPage } from './pages/admin-events.js';
import { subscriptionsPage } from './pages/admin-subscriptions.js';

// guard: guest = signed-out only · any = MEMBER or ADMIN · member = MEMBER · admin = ADMIN
defineRoutes([
  { path: '/', guard: 'public', redirect: () => session.homePath() },
  { path: '/login', guard: 'guest', title: 'Connexion', page: loginPage },
  { path: '/register', guard: 'guest', title: 'Demande d’adhésion', page: registerPage },
  { path: '/home', guard: 'member', adminRedirect: '/admin', title: 'Accueil', page: homePage, live: ['events', 'messages', 'profile', 'scoreboard'] },
  { path: '/events', guard: 'any', title: 'Événements', page: eventsPage },
  { path: '/events/:id', guard: 'any', title: 'Événement', page: eventDetailPage, live: ['events', 'profile'] },
  { path: '/scoreboard', guard: 'any', title: 'Classement', page: scoreboardPage },
  { path: '/members', guard: 'any', title: 'Membres', page: membersPage },
  { path: '/members/:id', guard: 'any', title: 'Membre', page: memberDetailPage, live: ['members', 'scoreboard'] },
  { path: '/suggestions', guard: 'member', adminRedirect: '/admin/suggestions', title: 'Boîte à suggestions', page: suggestionsPage },
  { path: '/profile', guard: 'any', title: 'Mon profil', page: profilePage, live: ['profile'] },
  { path: '/admin', guard: 'admin', title: 'Tableau de bord', page: dashboardPage, live: ['stats', 'requests', 'events', 'suggestions', 'members'] },
  { path: '/admin/requests', guard: 'admin', title: 'Demandes d’adhésion', page: requestsPage },
  { path: '/admin/members', guard: 'admin', title: 'Membres', page: adminMembersPage },
  { path: '/admin/members/:id', guard: 'admin', title: 'Membre', page: adminMemberDetailPage, live: ['members', 'scoreboard'] },
  { path: '/admin/subscriptions', guard: 'admin', title: 'Cotisations', page: subscriptionsPage },
  { path: '/admin/events', guard: 'admin', title: 'Événements', page: adminEventsPage },
  { path: '/admin/events/new', guard: 'admin', title: 'Créer un événement', page: eventFormPage },
  { path: '/admin/events/:id', guard: 'admin', title: 'Événement', page: adminEventDetailPage, live: ['events'] },
  { path: '/admin/events/:id/edit', guard: 'admin', title: 'Modifier l’événement', page: eventFormPage },
  { path: '/admin/messages', guard: 'admin', title: 'Messages', page: messagesPage },
  { path: '/admin/suggestions', guard: 'admin', title: 'Suggestions', page: adminSuggestionsPage },
], {
  bare: bareLayout,
  member: memberLayout,
  admin: adminLayout,
  notFound,
  forbidden,
});

setUnauthorizedHandler(() => {
  if (!session.user) return;
  session.clear();
  toast('Votre session a expiré. Reconnectez-vous pour continuer.', 'info');
  const next = encodeURIComponent(location.pathname + location.search);
  navigate(`/login?next=${next}`, { replace: true });
});

// ------------------------------------------------------------------ synchronisation between devices
session.subscribe(() => (session.user ? startSync() : stopSync()));

onChange((change) => {
  if (!session.user) return;
  if (change.notice) toast(change.notice, 'info', { timeout: 8000 });
  if (change.topics.includes('profile') && session.isMember) {
    api('/members/me').then((p) => session.setProfile(p)).catch(() => {});
  }
  if (session.isAdmin && change.topics.some((t) => t === 'requests' || t === 'suggestions' || t === 'stats')) {
    refreshAdminCounts();
  }
  dispatchChange(change);
});

const REVOKED = {
  LOGOUT: 'Vous avez été déconnecté depuis un autre onglet.',
  PASSWORD_CHANGED: 'Votre mot de passe a été modifié depuis un autre appareil. Reconnectez-vous.',
  ACCOUNT_INACTIVE: 'Votre compte n’est plus actif. Contactez l’administration du club.',
};
setRevokedHandler((reason) => {
  if (!session.user) return;
  session.clear();
  navigate('/login', { replace: true });
  toast(REVOKED[reason] || REVOKED.LOGOUT, 'info', { timeout: 10000 });
});

setAuthCheck(async () => {
  try {
    await api('/auth/me');
    return 'ok';
  } catch (err) {
    return err.status === 401 ? 'unauthenticated' : 'unreachable';
  }
});

// Other tabs of this browser signed in or out.
onOtherTab(async ({ type }) => {
  if (type === 'login' && !session.user) {
    try {
      session.set(await api('/auth/me', { silent401: true }));
      navigate(session.homePath(), { replace: true });
    } catch {
      /* still signed out */
    }
  }
  if (type === 'logout' && session.user) {
    stopSync();
    session.clear();
    navigate('/login', { replace: true });
    toast(REVOKED.LOGOUT, 'info');
  }
});

async function boot() {
  try {
    const me = await api('/auth/me', { silent401: true });
    session.set(me);
  } catch (err) {
    if (err.status !== 401) toast(err.message, 'error');
  }
  startRouter();
}

boot();
