'use strict';
/**
 * DTO mappers. They decide what leaves the server, so privacy (FR-19) is
 * enforced here: public views never carry email, phone or birthday.
 */
const { pointsFor } = require('./points');
const { publicUrl } = require('./files');

function formatPrice(minor, currency) {
  const decimals = currency === 'TND' ? 3 : 2;
  return (minor / 10 ** decimals).toFixed(decimals);
}

const socials = (u) => ({
  instagram: u.instagram || null,
  facebook: u.facebook || null,
  github: u.github || null,
  linkedin: u.linkedin || null,
});

/** What any member may see about another member. */
function publicMember(u) {
  return {
    id: u.id,
    name: u.name,
    avatarUrl: publicUrl(u.profile_photo),
    description: u.description || null,
    socials: socials(u),
    score: u.score ?? 0,
    memberSince: u.created_at,
  };
}

/** The member's own profile (FR-20) — includes their own private data. */
function selfProfile(u, score) {
  return {
    id: u.id,
    name: u.name,
    email: u.email,
    phone: u.phone,
    role: u.role,
    avatarUrl: publicUrl(u.profile_photo),
    description: u.description || null,
    birthday: u.birthday || null,
    socials: socials(u),
    score,
    memberSince: u.created_at,
  };
}

/** Minor units (millimes) -> "25.000". */
const money = (minor) => (minor === null || minor === undefined ? null : formatPrice(minor, 'TND'));

/** Admin view (FR-06). `season` set => the row carries the subscription columns of that season. */
function adminMember(u, season = null) {
  return {
    ...publicMember(u),
    email: u.email,
    phone: u.phone,
    birthday: u.birthday || null,
    status: u.status,
    updatedAt: u.updated_at,
    ...(season ? { subscription: { season, paid: u.sub_paid === 1, paidAt: u.sub_paid_at || null, amount: money(u.sub_amount) } } : {}),
  };
}

/** A paid-subscription record (admin only). */
function subscription(s) {
  return {
    id: s.id,
    season: s.season,
    name: s.name,
    email: s.email,
    phone: s.phone,
    amount: money(s.amount),
    paidAt: s.paid_at || null,
    reference: s.reference || null,
    status: s.status,
    memberId: s.user_id || null,
    claimedAt: s.claimed_at || null,
    createdAt: s.created_at,
  };
}

function sessionUser(u) {
  return { id: u.id, name: u.name, role: u.role, avatarUrl: publicUrl(u.profile_photo) };
}

function event(e, extra = {}) {
  return {
    id: e.id,
    title: e.title,
    description: e.description,
    type: e.type,
    points: pointsFor(e.type),
    date: e.date,
    time: e.time,
    location: e.location,
    isFree: e.is_free === 1,
    price: e.is_free === 1 ? null : formatPrice(e.price, e.currency),
    currency: e.currency,
    imageUrl: publicUrl(e.image_url),
    additionalInfo: e.additional_info || null,
    status: e.status,
    validatedCount: e.validated_count ?? 0,
    registeredCount: e.registered_count ?? 0,
    createdAt: e.created_at,
    updatedAt: e.updated_at,
    ...extra,
  };
}

module.exports = { publicMember, selfProfile, adminMember, subscription, sessionUser, event, formatPrice, money };
