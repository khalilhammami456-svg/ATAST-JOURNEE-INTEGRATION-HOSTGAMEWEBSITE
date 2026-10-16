/**
 * Tiny DOM builder. All dynamic text goes through textContent / attributes,
 * never innerHTML, so user content can never inject markup (XSS protection).
 */
const SVG_NS = 'http://www.w3.org/2000/svg';
const SVG_TAGS = new Set(['svg', 'g', 'path', 'circle', 'ellipse', 'rect', 'line', 'polyline', 'polygon', 'text', 'tspan', 'defs', 'radialGradient', 'linearGradient', 'stop', 'clipPath', 'title', 'pattern', 'use']);

function setAttr(el, key, value) {
  if (value === undefined || value === null || value === false) return;
  if (key === 'class' || key === 'className') {
    el.setAttribute('class', Array.isArray(value) ? value.filter(Boolean).join(' ') : value);
  } else if (key === 'text') {
    el.textContent = value;
  } else if (key === 'style' && typeof value === 'object') {
    for (const [p, v] of Object.entries(value)) el.style.setProperty(p, v);
  } else if (key === 'dataset') {
    Object.assign(el.dataset, value);
  } else if (key.startsWith('on') && typeof value === 'function') {
    el.addEventListener(key.slice(2).toLowerCase(), value);
  } else if (key === 'value' && 'value' in el && el.namespaceURI !== SVG_NS) {
    el.value = value;
  } else if (key === 'checked' || key === 'selected' || key === 'disabled' || key === 'multiple') {
    el[key] = Boolean(value);
    if (value) el.setAttribute(key, '');
  } else if (value === true) {
    el.setAttribute(key, '');
  } else {
    el.setAttribute(key, String(value));
  }
}

export function append(el, children) {
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false || child === '') continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return el;
}

/** h('div', { class: 'x', onClick }, 'text', childNode, [more]) */
export function h(tag, attrs, ...children) {
  const isSvg = SVG_TAGS.has(tag);
  const el = isSvg ? document.createElementNS(SVG_NS, tag) : document.createElement(tag);
  if (attrs && (attrs.constructor === Object)) {
    for (const [k, v] of Object.entries(attrs)) setAttr(el, k, v);
  } else if (attrs !== undefined) {
    children.unshift(attrs);
  }
  return append(el, children);
}

/** Parses a constant, developer-written SVG string (never user data). */
export function staticSvg(markup) {
  const tpl = document.createElement('template');
  tpl.innerHTML = markup.trim();
  return tpl.content.firstElementChild;
}

export function clear(el) {
  while (el.firstChild) el.removeChild(el.firstChild);
  return el;
}

export function replace(el, ...children) {
  clear(el);
  return append(el, children);
}

let uid = 0;
export const nextId = (prefix = 'id') => `${prefix}-${++uid}`;
