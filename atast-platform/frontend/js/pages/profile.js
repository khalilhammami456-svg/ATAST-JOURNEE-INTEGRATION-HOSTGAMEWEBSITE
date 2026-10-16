/** /profile — own profile, editing, photo and password (FR-20..FR-23). */
import { h, replace } from '../components/dom.js';
import { icon } from '../components/icons.js';
import { scoreOrbit } from '../components/brand.js';
import {
  avatar, field, passwordField, showErrors, clearErrors, withBusy, formData, toast, confirmDialog, pageHead,
  typeBadge, pointsChip, statusPill, emptyState,
} from '../components/ui.js';
import { api } from '../services/api.js';
import { session } from '../state/session.js';
import { formatDate, formatDay, ordinal, plural } from '../services/format.js';

const MAX_PHOTO = 2 * 1024 * 1024;
const PHOTO_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

export async function profilePage() {
  const profile = await api('/members/me');
  session.setProfile(profile);
  let current = profile;

  // ------------------------------------------------ Photo
  const photoWrap = h('div', { class: 'photo-edit' });
  const fileInput = h('input', { id: 'photo-input', class: 'file-input', type: 'file', accept: PHOTO_TYPES.join(',') });
  function paintPhoto() {
    const remove = current.avatarUrl ? h('button', { class: 'btn btn--danger-ghost btn--sm', type: 'button', onClick: removePhoto }, 'Retirer') : null;
    replace(photoWrap,
      avatar(current, { size: 'xl', decorative: false }),
      h('div', { class: 'actions' },
        fileInput,
        h('label', { for: 'photo-input', class: 'btn btn--secondary btn--sm' }, icon('upload'), current.avatarUrl ? 'Changer la photo' : 'Ajouter une photo'),
        remove));
  }
  fileInput.addEventListener('change', async () => {
    const file = fileInput.files[0];
    fileInput.value = '';
    if (!file) return;
    if (!PHOTO_TYPES.includes(file.type)) return toast('Formats acceptés : JPEG, PNG ou WebP.', 'error');
    if (file.size > MAX_PHOTO) return toast('L’image ne doit pas dépasser 2 Mo.', 'error');
    const form = new FormData();
    form.append('file', file);
    const label = photoWrap.querySelector('label');
    label.classList.add('is-loading');
    try {
      current = await api('/members/me/photo', { method: 'POST', form });
      session.setProfile(current);
      paintPhoto();
      toast('Photo de profil mise à jour.');
    } catch (err) {
      label.classList.remove('is-loading');
      toast(err.fields?.file || err.message, 'error');
    }
  });
  async function removePhoto() {
    const ok = await confirmDialog({ title: 'Retirer votre photo ?', message: 'L’avatar par défaut sera affiché à la place.', confirmLabel: 'Retirer la photo', danger: true });
    if (!ok) return;
    try {
      current = await api('/members/me/photo', { method: 'DELETE' });
      session.setProfile(current);
      paintPhoto();
      toast('Photo retirée.');
    } catch (err) { toast(err.message, 'error'); }
  }
  // Keyboard users reach the visible label-button through the file input itself.
  fileInput.setAttribute('aria-label', 'Choisir une photo de profil (JPEG, PNG ou WebP, 2 Mo maximum)');
  paintPhoto();

  // ------------------------------------------------ Personal information
  const saveBtn = h('button', { class: 'btn', type: 'submit' }, 'Enregistrer les modifications');
  const today = new Date().toISOString().slice(0, 10);
  const info = h('form', { class: 'form', novalidate: true },
    h('div', { class: 'form-section' },
      h('h2', 'Informations personnelles'),
      h('div', { class: 'form-grid form-grid--2' },
        field({ label: 'Nom complet', name: 'name', value: profile.name, required: true, autocomplete: 'name', maxlength: 80 }),
        field({ label: 'Adresse email', name: 'emailRo', value: profile.email, readonly: true, hint: 'L’adresse email sert à la connexion et ne peut pas être modifiée ici.' }),
        field({ label: 'Téléphone', name: 'phone', type: 'tel', value: profile.phone, required: true, autocomplete: 'tel', hint: 'Visible uniquement par vous et l’administration.' }),
        field({ label: 'Date de naissance', name: 'birthday', type: 'date', value: profile.birthday || '', optional: true, max: today, hint: 'Visible uniquement par vous et l’administration.' }),
        field({ label: 'Présentation', name: 'description', value: profile.description || '', multiline: true, optional: true, maxlength: 600, rows: 4, span: true, hint: 'Visible par les autres membres.' }))),
    h('div', { class: 'form-section' },
      h('h2', 'Réseaux sociaux'),
      h('p', { class: 'muted small' }, 'Liens facultatifs, visibles par les autres membres. Collez l’adresse complète de votre profil.'),
      h('div', { class: 'form-grid form-grid--2' },
        field({ label: 'Instagram', name: 'instagram', type: 'url', value: profile.socials.instagram || '', optional: true, placeholder: 'https://instagram.com/votre-nom', inputmode: 'url' }),
        field({ label: 'Facebook', name: 'facebook', type: 'url', value: profile.socials.facebook || '', optional: true, placeholder: 'https://facebook.com/votre-nom', inputmode: 'url' }),
        field({ label: 'GitHub', name: 'github', type: 'url', value: profile.socials.github || '', optional: true, placeholder: 'https://github.com/votre-nom', inputmode: 'url' }),
        field({ label: 'LinkedIn', name: 'linkedin', type: 'url', value: profile.socials.linkedin || '', optional: true, placeholder: 'https://linkedin.com/in/votre-nom', inputmode: 'url' }))),
    h('div', { class: 'form-actions' }, saveBtn));

  info.addEventListener('submit', (e) => {
    e.preventDefault();
    const { emailRo, ...data } = formData(info);
    clearErrors(info);
    withBusy(saveBtn, async () => {
      try {
        current = await api('/members/me', { method: 'PUT', body: data });
        delete info.dataset.dirty; // saved: a live refresh may now update this page
        session.setProfile(current);
        replace(nameEl, current.name);
        toast('Profil enregistré.');
      } catch (err) { showErrors(info, err); }
    });
  });

  // ------------------------------------------------ Password (separate secured procedure)
  const pwBtn = h('button', { class: 'btn btn--secondary', type: 'submit' }, icon('lock'), 'Changer le mot de passe');
  const pwForm = h('form', { class: 'form', novalidate: true },
    passwordField({ label: 'Mot de passe actuel', name: 'currentPassword', autocomplete: 'current-password', required: true }),
    passwordField({ label: 'Nouveau mot de passe', name: 'newPassword', autocomplete: 'new-password', required: true, hint: 'Au moins 8 caractères, avec des lettres et des chiffres.' }),
    passwordField({ label: 'Confirmation du nouveau mot de passe', name: 'newPasswordConfirm', autocomplete: 'new-password', required: true }),
    h('div', {}, pwBtn));
  pwForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const data = formData(pwForm);
    const f = {};
    if (!data.currentPassword) f.currentPassword = 'Le mot de passe actuel est obligatoire.';
    if (!data.newPassword || data.newPassword.length < 8) f.newPassword = 'Le nouveau mot de passe doit contenir au moins 8 caractères.';
    if (data.newPassword !== data.newPasswordConfirm) f.newPasswordConfirm = 'Les deux mots de passe ne correspondent pas.';
    if (Object.keys(f).length) return showErrors(pwForm, { fields: f });
    clearErrors(pwForm);
    withBusy(pwBtn, async () => {
      try {
        const res = await api('/auth/password', { method: 'PUT', body: data });
        pwForm.reset();
        toast(res.message);
      } catch (err) { showErrors(pwForm, err); }
    });
  });

  // ------------------------------------------------ Participations
  const isMember = profile.role === 'MEMBER';
  let history = null;
  if (isMember) {
    const parts = profile.participations || [];
    history = h('section', { class: 'panel', 'aria-labelledby': 'hist-title' },
      h('div', { class: 'panel__head' }, h('h2', { id: 'hist-title' }, 'Mes participations')),
      parts.length
        ? h('div', {},
          h('ul', { class: 'history' }, parts.map((p) => h('li', {},
            h('a', { href: `/events/${p.event.id}`, 'data-link': '' }, p.event.title),
            p.status === 'VALIDATED' ? pointsChip(p.pointsAwarded) : statusPill('participation', 'REGISTERED'),
            h('div', { class: 'meta' }, typeBadge(p.event.type, { short: true }), formatDay(p.event.date, { day: 'numeric', month: 'short', year: 'numeric' }))))),
          h('div', { class: 'score-sum' }, h('span', 'Score total'), h('span', { class: 'num' }, `${profile.score} pts`)))
        : emptyState({ title: 'Aucune participation pour l’instant', text: 'Inscrivez-vous à un événement : vos participations validées s’afficheront ici.', action: h('a', { class: 'btn', href: '/events', 'data-link': '' }, 'Voir les événements') }));
  }

  const nameEl = h('h1', { 'data-page-title': '', tabindex: '-1' }, profile.name);
  return h('div', {},
    h('div', { class: 'profile-head' },
      photoWrap,
      h('div', {},
        nameEl,
        h('p', { class: 'muted' }, `${profile.role === 'ADMIN' ? 'Administrateur' : 'Membre'} depuis ${formatDate(profile.memberSince)}`),
        isMember && profile.rank ? h('p', { class: 'small' }, h('b', ordinal(profile.rank.rank)), ` sur ${plural(profile.rank.total, 'membre', 'membres')} au `, h('a', { href: '/scoreboard', 'data-link': '' }, 'classement')) : null),
      isMember ? scoreOrbit(profile.score, { small: true }) : null),
    h('div', { class: 'profile-cols' },
      h('section', { class: 'panel', 'aria-label': 'Modifier mon profil' }, info),
      h('div', { class: 'stack' },
        h('section', { class: 'panel', 'aria-labelledby': 'pw-title' }, h('h2', { id: 'pw-title', style: { 'margin-bottom': '16px' } }, 'Mot de passe'), pwForm),
        history)));
}

export { pageHead };
