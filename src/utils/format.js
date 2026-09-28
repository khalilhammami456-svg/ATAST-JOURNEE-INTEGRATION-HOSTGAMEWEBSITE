const timeFormatter = new Intl.DateTimeFormat('fr-FR', { hour: '2-digit', minute: '2-digit' });
const dateTimeFormatter = new Intl.DateTimeFormat('fr-FR', {
  day: '2-digit',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
});

export const formatTime = (timestamp) => timeFormatter.format(new Date(timestamp));
export const formatDateTime = (timestamp) => dateTimeFormatter.format(new Date(timestamp));

export const formatPoints = (value) => new Intl.NumberFormat('fr-FR').format(value);

export const formatDelta = (delta) => (delta > 0 ? `+${delta}` : `${delta}`);

export function pluralize(count, singular, plural = `${singular}s`) {
  return `${count} ${count > 1 ? plural : singular}`;
}

export function ordinalLabel(rank) {
  return rank === 1 ? '1er' : `${rank}e`;
}

export function relativeTime(timestamp, now = Date.now()) {
  const seconds = Math.round((now - timestamp) / 1000);
  if (seconds < 10) return "à l'instant";
  if (seconds < 60) return `il y a ${seconds} s`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `il y a ${minutes} min`;
  return formatDateTime(timestamp);
}

export const normalize = (text) => text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();

export function initials(name) {
  const cleaned = name.replace(/^team\s+/i, '').trim();
  const words = cleaned.split(/\s+/).filter(Boolean);
  if (words.length === 0) return '?';
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[1][0]).toUpperCase();
}
