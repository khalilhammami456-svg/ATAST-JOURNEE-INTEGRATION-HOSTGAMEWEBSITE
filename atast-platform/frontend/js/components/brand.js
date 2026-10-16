/**
 * Brand graphics drawn from the ATAST logo: a blue sphere circled by orange
 * orbits. All markup is built with h(); only numbers/known strings go in.
 */
import { h, nextId } from './dom.js';

const ORANGE = '#F06C17';
const NAVY = '#062247';

function sphereGradient(id) {
  return h('radialGradient', { id, cx: '36%', cy: '30%', r: '75%' },
    h('stop', { offset: '0%', 'stop-color': '#A9D0FF' }),
    h('stop', { offset: '42%', 'stop-color': '#2E8BFA' }),
    h('stop', { offset: '78%', 'stop-color': '#0A63E0' }),
    h('stop', { offset: '100%', 'stop-color': '#0646A8' }));
}

/** Compact mark for navigation bars. */
export function mark({ title } = {}) {
  const g = nextId('sg');
  return h('svg', { viewBox: '0 0 64 64', 'aria-hidden': title ? undefined : 'true', role: title ? 'img' : undefined },
    title ? h('title', title) : null,
    h('defs', sphereGradient(g)),
    h('ellipse', { cx: 32, cy: 32, rx: 11, ry: 29, fill: 'none', stroke: ORANGE, 'stroke-width': 3, transform: 'rotate(16 32 32)' }),
    h('circle', { cx: 32, cy: 32, r: 17, fill: `url(#${g})` }),
    h('ellipse', { cx: 32, cy: 32, rx: 29, ry: 10.5, fill: 'none', stroke: ORANGE, 'stroke-width': 3.2, transform: 'rotate(-14 32 32)' }),
    h('ellipse', { cx: 27, cy: 24, rx: 7, ry: 4, fill: '#fff', opacity: 0.28, transform: 'rotate(-20 27 24)' }));
}

export function brand({ href = '/', sub = 'Club ISIMM' } = {}) {
  return h('a', { class: 'brand', href, 'data-link': '', 'aria-label': 'ATAST Club, accueil' },
    mark(),
    h('span', { class: 'brand__word', 'aria-hidden': 'true' }, h('b', 'ATAST'), h('small', sub)),
  );
}

/** Orbit drawn behind the sphere, then its front half again on top (depth like the logo). */
function orbit({ cx, cy, rx, ry, rotate, width, cls, clipId, front }) {
  const attrs = {
    cx, cy, rx, ry, fill: 'none', stroke: ORANGE, 'stroke-width': width, 'stroke-linecap': 'round',
    transform: `rotate(${rotate} ${cx} ${cy})`, pathLength: 1, class: cls,
  };
  if (front) attrs['clip-path'] = `url(#${clipId})`;
  return h('ellipse', attrs);
}

/** Large emblem used on the sign-in screens (vector rendition of the club logo). */
export function emblem() {
  const g = nextId('eg');
  const c1 = nextId('ec');
  const c2 = nextId('ec');
  const cx = 200; const cy = 190;
  const o1 = { cx, cy, rx: 178, ry: 60, rotate: -12, width: 8, cls: 'orbit' };
  const o2 = { cx, cy, rx: 58, ry: 172, rotate: 18, width: 6, cls: 'orbit orbit--2' };
  return h('svg', { class: 'emblem auth__emblem', viewBox: '0 0 400 400', role: 'img', 'aria-label': 'Emblème du club ATAST' },
    h('defs',
      sphereGradient(g),
      h('clipPath', { id: c1, clipPathUnits: 'userSpaceOnUse' }, h('rect', { x: cx - 200, y: cy, width: 400, height: 220, transform: `rotate(${o1.rotate} ${cx} ${cy})` })),
      h('clipPath', { id: c2, clipPathUnits: 'userSpaceOnUse' }, h('rect', { x: cx, y: cy - 220, width: 220, height: 440, transform: `rotate(${o2.rotate} ${cx} ${cy})` })),
    ),
    orbit(o1), orbit(o2),
    h('g', { class: 'sphere' },
      h('circle', { cx, cy, r: 104, fill: `url(#${g})` }),
      h('ellipse', { cx: cx - 30, cy: cy - 52, rx: 50, ry: 26, fill: '#fff', opacity: 0.22, transform: `rotate(-18 ${cx - 30} ${cy - 52})` }),
      h('text', { x: cx, y: cy + 14, 'text-anchor': 'middle', 'font-family': 'Exo 2, sans-serif', 'font-style': 'italic', 'font-weight': 800, 'font-size': 58, fill: NAVY }, 'ATAST'),
      h('text', { x: cx - 8, y: cy + 93, 'text-anchor': 'middle', 'font-family': 'Exo 2, sans-serif', 'font-weight': 700, 'font-size': 20, fill: '#fff' }, 'Club'),
    ),
    orbit({ ...o1, front: true, clipId: c1 }),
    orbit({ ...o2, front: true, clipId: c2 }),
    h('text', { x: 372, y: 382, 'text-anchor': 'end', 'font-family': 'Exo 2, sans-serif', 'font-weight': 700, 'font-size': 50, fill: '#3E93FF', 'letter-spacing': 2 }, 'ISIMM'),
  );
}

/** Signature element: the member's score inside the sphere, circled by an orbit. */
export function scoreOrbit(score, { small = false, label = 'points' } = {}) {
  const g = nextId('og');
  const clip = nextId('oc');
  const cx = 120; const cy = 100;
  const digits = String(score).length;
  const size = digits >= 4 ? 36 : digits === 3 ? 44 : 50;
  const o = { cx, cy, rx: 114, ry: 50, rotate: -14, width: 7, cls: 'orbit-path' };
  return h('div', { class: ['score-orbit', small && 'score-orbit--sm'] },
    h('svg', { viewBox: '0 0 240 210', role: 'img', 'aria-label': `${score} ${label}` },
      h('defs', sphereGradient(g),
        h('clipPath', { id: clip, clipPathUnits: 'userSpaceOnUse' }, h('rect', { x: 0, y: cy, width: 240, height: 120, transform: `rotate(${o.rotate} ${cx} ${cy})` }))),
      orbit(o),
      h('circle', { cx, cy, r: 66, fill: `url(#${g})` }),
      h('ellipse', { cx: cx - 20, cy: cy - 34, rx: 30, ry: 15, fill: '#fff', opacity: 0.22, transform: `rotate(-18 ${cx - 20} ${cy - 34})` }),
      h('text', { class: 'score-value', x: cx, y: cy + 4, 'text-anchor': 'middle', 'font-size': size }, String(score)),
      h('text', { class: 'score-label', x: cx, y: cy + 26, 'text-anchor': 'middle', 'font-size': 14 }, label),
      orbit({ ...o, front: true, clipId: clip }),
    ));
}

/** Deterministic cover art for events without a picture, tinted by event type. */
export function eventCover(seed, type) {
  let n = 0;
  for (const ch of String(seed)) n = (n * 31 + ch.charCodeAt(0)) >>> 0;
  const rnd = () => ((n = (n * 1664525 + 1013904223) >>> 0) / 4294967296);
  const g = nextId('cg');
  const sphereX = 520 + rnd() * 180;
  const sphereY = 110 + rnd() * 90;
  const r = { SMALL: 54, MEDIUM: 74, BIG: 96, MEETING: 46 }[type] || 60;
  const orbits = [];
  const count = { SMALL: 1, MEDIUM: 2, BIG: 3, MEETING: 1 }[type] || 1;
  for (let i = 0; i < count; i += 1) {
    orbits.push(h('ellipse', {
      cx: sphereX, cy: sphereY, rx: r * (2.4 + i * 0.7), ry: r * (0.62 + i * 0.12), fill: 'none',
      stroke: type === 'MEETING' ? '#8EA6C8' : ORANGE, 'stroke-width': 5 - i, opacity: 1 - i * 0.25,
      transform: `rotate(${-18 + i * 26 + rnd() * 10} ${sphereX} ${sphereY})`,
    }));
  }
  const stars = Array.from({ length: 26 }, () => h('circle', { cx: rnd() * 800, cy: rnd() * 350, r: rnd() * 1.6 + 0.4, fill: '#fff', opacity: 0.25 + rnd() * 0.5 }));
  return h('svg', { viewBox: '0 0 800 350', preserveAspectRatio: 'xMidYMid slice', 'aria-hidden': 'true' },
    h('defs', sphereGradient(g)),
    stars,
    orbits,
    h('circle', { cx: sphereX, cy: sphereY, r, fill: type === 'MEETING' ? '#1B4A8C' : `url(#${g})` }),
  );
}

/** Small illustration for empty states. */
export function emptyArt() {
  return h('svg', { class: 'empty__art', viewBox: '0 0 120 72', 'aria-hidden': 'true' },
    h('ellipse', { cx: 60, cy: 36, rx: 54, ry: 16, fill: 'none', stroke: '#B9C8DC', 'stroke-width': 2, 'stroke-dasharray': '4 5', transform: 'rotate(-10 60 36)' }),
    h('circle', { cx: 60, cy: 36, r: 18, fill: '#E7F0FD', stroke: '#B9C8DC', 'stroke-width': 2 }),
    h('circle', { cx: 110, cy: 28, r: 4, fill: ORANGE }),
  );
}
