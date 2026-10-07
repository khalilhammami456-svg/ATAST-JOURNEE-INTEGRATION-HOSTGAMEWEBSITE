/** Session state: the signed-in user, CSRF token and a cached score. */
const listeners = new Set();

export const session = {
  user: null,
  csrf: null,
  profile: null, // cached /members/me summary (score, rank) — refreshed when it can change

  set({ user, csrfToken }) {
    this.user = user;
    this.csrf = csrfToken;
    emit();
  },
  setProfile(profile) {
    this.profile = profile;
    if (this.user && profile) {
      this.user = { ...this.user, name: profile.name, avatarUrl: profile.avatarUrl };
    }
    emit();
  },
  invalidateProfile() {
    this.profile = null;
  },
  clear() {
    this.user = null;
    this.csrf = null;
    this.profile = null;
    emit();
  },
  get isAdmin() {
    return this.user?.role === 'ADMIN';
  },
  get isMember() {
    return this.user?.role === 'MEMBER';
  },
  homePath() {
    if (!this.user) return '/login';
    return this.isAdmin ? '/admin' : '/home';
  },
  subscribe(fn) {
    listeners.add(fn);
    return () => listeners.delete(fn);
  },
};

function emit() {
  for (const fn of listeners) fn(session);
}
