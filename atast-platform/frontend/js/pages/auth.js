/** /login and /register (FR-01). */
import { h, replace } from '../components/dom.js';
import { icon } from '../components/icons.js';
import { brand, emblem } from '../components/brand.js';
import { field, passwordField, showErrors, clearErrors, withBusy, formData } from '../components/ui.js';
import { api } from '../services/api.js';
import { session } from '../state/session.js';
import { navigate } from '../app/router.js';
import { tellOtherTabs } from '../services/sync.js';

function visual(children) {
  return h('section', { class: 'auth__visual' },
    brand({ href: '/login' }),
    emblem(),
    h('div', {}, children));
}

function safeNext(next) {
  return typeof next === 'string' && next.startsWith('/') && !next.startsWith('//') && !next.startsWith('/login') ? next : null;
}

function alertBox(kind, text) {
  return h('div', { class: ['alert', `alert--${kind}`, 'form-alert'], role: kind === 'error' ? 'alert' : 'status' },
    icon(kind === 'error' ? 'alert' : 'info'), h('p', text));
}

// ---------------------------------------------------------------- Login
export function loginPage({ query }) {
  const email = field({ label: 'Adresse email', name: 'email', type: 'email', autocomplete: 'email', required: true, inputmode: 'email' });
  const password = passwordField({ label: 'Mot de passe', name: 'password', autocomplete: 'current-password', required: true });
  const submit = h('button', { class: 'btn btn--block', type: 'submit' }, 'Se connecter');
  const form = h('form', { class: 'form', novalidate: true }, email, password, submit);

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    clearErrors(form);
    const data = formData(form);
    const fields = {};
    if (!data.email) fields.email = "L'adresse email est obligatoire.";
    if (!data.password) fields.password = 'Le mot de passe est obligatoire.';
    if (Object.keys(fields).length) return showErrors(form, { fields });
    withBusy(submit, async () => {
      try {
        const res = await api('/auth/login', { method: 'POST', body: { email: data.email, password: data.password } });
        session.set(res);
        tellOtherTabs('login');
        navigate(safeNext(query.next) || session.homePath(), { replace: true });
      } catch (err) {
        if (err.fields) return showErrors(form, err);
        form.querySelector('.form-alert')?.remove();
        const kind = err.code === 'REQUEST_PENDING' ? 'info' : 'error';
        form.prepend(alertBox(kind, err.message));
        if (err.code === 'INVALID_CREDENTIALS') {
          password.control.value = '';
          password.control.focus();
        }
      }
    });
  });

  return h('div', { class: 'auth' },
    visual([
      h('p', { class: 'auth__tagline' }, 'Apprendre, construire, partager.'),
      h('p', { class: 'auth__sub' }, 'L’espace des membres du club ATAST de l’ISIMM : les événements à venir, vos points de participation et la vie du club.'),
    ]),
    h('section', { class: 'auth__panel' },
      h('div', { class: 'auth__form' },
        h('h1', { 'data-page-title': '', tabindex: '-1' }, 'Connexion'),
        h('p', { class: 'lead' }, 'Connectez-vous avec l’adresse email de votre adhésion.'),
        query.next ? alertBox('info', 'Connectez-vous pour continuer.') : null,
        form,
        h('p', { class: 'auth__switch' }, 'Pas encore membre ? ', h('a', { href: '/register', 'data-link': '' }, 'Demander l’adhésion')))));
}

// ---------------------------------------------------------------- Register
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

function checkRegister(d) {
  const f = {};
  if (!d.name || d.name.trim().length < 2) f.name = 'Le nom doit contenir au moins 2 caractères.';
  if (!d.email) f.email = "L'adresse email est obligatoire.";
  else if (!EMAIL_RE.test(d.email.trim())) f.email = "L'adresse email n'est pas valide.";
  const digits = (d.phone || '').replace(/[\s().+-]/g, '');
  if (!d.phone) f.phone = 'Le numéro de téléphone est obligatoire.';
  else if (!/^[0-9]{8,15}$/.test(digits)) f.phone = 'Le numéro doit contenir entre 8 et 15 chiffres.';
  if (!d.password) f.password = 'Le mot de passe est obligatoire.';
  else if (d.password.length < 8) f.password = 'Le mot de passe doit contenir au moins 8 caractères.';
  else if (!/[A-Za-z]/.test(d.password) || !/[0-9]/.test(d.password)) f.password = 'Le mot de passe doit contenir au moins une lettre et un chiffre.';
  if (!d.passwordConfirm) f.passwordConfirm = 'Confirmez le mot de passe.';
  else if (d.password && d.passwordConfirm !== d.password) f.passwordConfirm = 'Les deux mots de passe ne correspondent pas.';
  return f;
}

export function registerPage() {
  const submit = h('button', { class: 'btn btn--block', type: 'submit' }, 'Envoyer ma demande');
  const form = h('form', { class: 'form', novalidate: true },
    field({ label: 'Nom complet', name: 'name', autocomplete: 'name', required: true, maxlength: 80 }),
    field({ label: 'Adresse email', name: 'email', type: 'email', autocomplete: 'email', required: true, inputmode: 'email' }),
    field({ label: 'Numéro de téléphone', name: 'phone', type: 'tel', autocomplete: 'tel', required: true, inputmode: 'tel', hint: 'Exemple : +216 20 123 456' }),
    passwordField({ label: 'Mot de passe', name: 'password', autocomplete: 'new-password', required: true, hint: 'Au moins 8 caractères, avec des lettres et des chiffres.' }),
    passwordField({ label: 'Confirmation du mot de passe', name: 'passwordConfirm', autocomplete: 'new-password', required: true }),
    submit);
  const panel = h('div', { class: 'auth__form' },
    h('h1', { 'data-page-title': '', tabindex: '-1' }, 'Demande d’adhésion'),
    h('p', { class: 'lead' }, 'Votre compte sera activé dès que le bureau du club aura validé votre demande.'),
    form,
    h('p', { class: 'auth__switch' }, 'Déjà membre ? ', h('a', { href: '/login', 'data-link': '' }, 'Se connecter')));

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const data = formData(form);
    const fields = checkRegister(data);
    if (Object.keys(fields).length) return showErrors(form, { fields });
    clearErrors(form);
    withBusy(submit, async () => {
      try {
        const result = await api('/auth/register', { method: 'POST', body: data });
        if (result.status === 'ACCEPTED') {
          replace(panel,
            h('div', { class: 'auth-done' },
              h('div', { class: 'alert alert--success', role: 'status' }, icon('check'), h('p', 'Cotisation confirmée.')),
              h('h1', { 'data-page-title': '', tabindex: '-1', class: 'mt' }, 'Bienvenue au club !'),
              h('p', { class: 'lead' }, `Votre cotisation est enregistrée : votre adhésion est acceptée. Connectez-vous avec ${data.email.trim()} et le mot de passe choisi.`),
              h('a', { class: 'btn', href: '/login', 'data-link': '' }, 'Se connecter')));
          panel.querySelector('h1').focus();
          return;
        }
        replace(panel,
          h('div', { class: 'auth-done' },
            h('div', { class: 'alert alert--success', role: 'status' }, icon('check'), h('p', 'Demande envoyée.')),
            h('h1', { 'data-page-title': '', tabindex: '-1', class: 'mt' }, 'Merci, votre demande est en attente'),
            h('p', { class: 'lead' }, `Le bureau d’ATAST va examiner la demande de ${data.name.trim()}. Une fois acceptée, vous pourrez vous connecter avec ${data.email.trim()} et le mot de passe choisi.`),
            h('a', { class: 'btn', href: '/login', 'data-link': '' }, 'Retour à la connexion')));
        panel.querySelector('h1').focus();
      } catch (err) {
        showErrors(form, err);
      }
    });
  });

  return h('div', { class: 'auth' },
    visual([
      h('p', { class: 'auth__tagline' }, 'Rejoindre ATAST'),
      h('ol', { class: 'auth__steps', 'aria-label': 'Comment se passe l’adhésion' },
        h('li', h('div', {}, h('b', 'Vous envoyez votre demande'), 'Nom, email, téléphone et mot de passe.')),
        h('li', h('div', {}, h('b', 'Le bureau l’examine'), 'Chaque demande est validée par un administrateur, ou tout de suite si votre cotisation est déjà enregistrée.')),
        h('li', h('div', {}, h('b', 'Vous accédez à l’espace membre'), 'Événements, classement, suggestions et profil.'))),
    ]),
    h('section', { class: 'auth__panel' }, panel));
}
