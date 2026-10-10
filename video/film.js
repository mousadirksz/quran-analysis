// The engine both films run on. A page loads its data (window.FILM, written by
// sarf_video.py or nahw_video.py from quran.db), then this file, then writes
// its scenes and calls Film.start() with the builders that put together the
// scenes whose rows come from the data.
//
// Opened in a browser a film plays in real time: space or a click pauses, the
// arrow keys skip five seconds, and #t=95 in the address starts at 95 s.
// render.cjs drives it frame by frame instead. Everything on screen is a
// function of one number, the time, so a frame can be drawn in any order and
// by any number of workers.
//
// Markup conventions:
//   data-dur on a .scene   its length in seconds; scenes follow one another
//   data-t, data-d         when an element comes in (scene time) and how long it takes
//   data-a                 how: up (default), fade, pop, zoom, grow, move (from
//                          data-x/-y, over data-bump on the way), barx,
//                          wipe, count, draw, or none (there from the start)
//   data-out               when it leaves again
//   data-k                 fill with this value from the data ("roots.total")
//   data-m                 colour an Arabic word letter by letter: r root letter,
//                          z added letter, v vowel that matters, w weak letter,
//                          . as is; digits and a-h also link letters to a pattern
//   data-arcs on a .dep    arcs between its words, "head>dependent:label:class;..."
//                          by their data-n, drawn from the 'amil to what it governs
(function () {
'use strict';
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const easeOut = p => 1 - Math.pow(1 - p, 3);
const easeInOut = p => (p < .5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2);
const get = k => k.split('.').reduce((o, p) => (o == null ? o : o[p]), window.FILM);
const NS = 'http://www.w3.org/2000/svg';

// Dutch number format: 128.219 and 48,9
function fmt(x, dec = 0) {
  let [i, f] = Math.abs(x).toFixed(dec).split('.');
  i = i.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  return (x < 0 ? '-' : '') + i + (f ? ',' + f : '');
}

function html(el, s) { el.insertAdjacentHTML('beforeend', s); }

function svgEl(name, attrs) {
  const el = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
}

// ------------------------------------------------------- data and colour

function fill() {
  for (const el of document.querySelectorAll('[data-k]')) {
    if (el.dataset.a === 'count' || el.dataset.a === 'barx') continue;
    const v = get(el.dataset.k);
    if (v === undefined) { console.error('no value for ' + el.dataset.k); continue; }
    el.textContent = typeof v === 'number' ? fmt(v, +(el.dataset.dec || 0)) : v;
  }
  for (const el of document.querySelectorAll('[data-mk]')) el.dataset.m = get(el.dataset.mk);
  for (const el of document.querySelectorAll('.seg[data-w]')) el.style.width = get(el.dataset.w) + '%';
}

// A letter with the marks on it; the same split sarf_video.clusters makes.
const clusters = s => s.match(/\P{M}\p{M}*/gu) || [];

function paint(el) {
  const cl = clusters(el.textContent), m = el.dataset.m;
  if (cl.length !== m.length) console.error(`mask ${m} does not fit ${el.textContent} (${cl.length} letters)`);
  el.textContent = '';
  cl.forEach((c, i) => {
    const k = m[i] || '.', span = document.createElement('span');
    span.textContent = c;
    if (/[1-9]/.test(k)) { span.className = 'r'; span.dataset.l = k; }
    else if (/[a-h]/.test(k)) { span.className = 'z'; span.dataset.l = k; }
    else if (k !== '.') span.className = k;
    el.appendChild(span);
  });
}

// ------------------------------------------------------------ the links
// In the mizan scene each letter of the word is tied to its letter in the
// pattern. Positions are measured once, before anything moves.

function buildLinks() {
  for (const w of document.querySelectorAll('.weigh')) {
    const svg = w.querySelector('svg.links'), box = w.getBoundingClientRect();
    svg.setAttribute('width', box.width); svg.setAttribute('height', box.height);
    const ww = w.querySelector('.ww').getBoundingClientRect(), wp = w.querySelector('.wp').getBoundingClientRect();
    const t0 = +w.dataset.t + .8;
    [...w.querySelectorAll('.ww [data-l]')].forEach((a, i) => {
      const b = w.querySelector(`.wp [data-l="${a.dataset.l}"]`);
      if (!b) { console.error('no partner for ' + a.dataset.l); return; }
      const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
      const x1 = ra.left + ra.width / 2 - box.left, y1 = ww.bottom - box.top - 4;
      const x2 = rb.left + rb.width / 2 - box.left, y2 = wp.top - box.top - 34;
      const line = document.createElementNS(NS, 'line');
      Object.entries({ x1, y1, x2, y2, 'stroke-width': 3, 'stroke-linecap': 'round',
        stroke: a.className === 'r' ? '#f2b544' : '#45c4b5' }).forEach(([k, v]) => line.setAttribute(k, v));
      const len = Math.hypot(x2 - x1, y2 - y1);
      line.setAttribute('stroke-dasharray', len);
      line.dataset.t = (t0 + i * .2).toFixed(2); line.dataset.a = 'draw'; line.dataset.d = '.6';
      line.dataset.len = len;
      svg.appendChild(line);
    });
  }
}

// ------------------------------------------------------------- the arcs
// A sentence whose words point at one another: an arc leaves the word that
// does the work and comes down, arrowhead first, on the word it governs, with
// the name of that relation on its top. The arcs rise straight up from their
// words and run flat over the top, so one that spans another clears its label.
// Where several arcs meet one word they share it out, the shortest innermost,
// so they nest instead of crossing. Heights are given shortest first: each arc
// goes as low as it can while it stays above every arc it spans and its label
// touches no other label or arc; an arc within one written word runs under
// it. data-at says when the first arc is drawn (default: just after the
// sentence comes in), data-gap the time between arcs.

// points along the curve, leaving out the ends, where arcs meet words
function curve(a) {
  const pts = [];
  for (let k = 2; k <= 30; k++) {
    const t = k / 32, u = 1 - t, b0 = u * u * u, b1 = 3 * u * u * t, b2 = 3 * u * t * t, b3 = t * t * t;
    pts.push([b0 * a.x1 + b1 * a.x1 + b2 * a.x2 + b3 * a.x2, b0 * a.y1 + (b1 + b2) * a.c + b3 * a.y2]);
  }
  return pts;
}

function shape(a, top) {
  a.top = top;
  a.c = (8 * top - a.y1 - a.y2) / 6;   // the control height that puts the middle at `top`
  a.box = [a.lx - a.w / 2 - 6, top - a.h / 2 - 5, a.lx + a.w / 2 + 6, top + a.h / 2 + 5];
  a.pts = curve(a);
}

// A label sits in the middle of its arc, unless another arc rises through
// that spot: then it moves aside, which a short arc between two words that
// carry other arcs needs (bi- and its noun, ihdi- and its -naa).
function labelX(a, top, arcs, done) {
  const mid = (a.x1 + a.x2) / 2, half = a.w / 2 + 8;
  const sides = arcs.filter(o => o !== a && (!done.includes(o) || o.top < top + a.h))
    .flatMap(o => [o.x1, o.x2]);
  const free = x => !sides.some(s => s > x - half && s < x + half);
  for (let d = 0; d <= a.w; d += 4) for (const x of [mid - d, mid + d]) if (free(x)) return x;
  return mid;
}

const inBox = (b, [x, y]) => x > b[0] && x < b[2] && y > b[1] && y < b[3];
const boxes = (p, q) => p[0] < q[2] && q[0] < p[2] && p[1] < q[3] && q[1] < p[3];

function clash(a, done) {
  return done.some(o => boxes(a.box, o.box) || o.pts.some(pt => inBox(a.box, pt)) || a.pts.some(pt => inBox(o.box, pt)));
}

// Each end of an arc gets its own point on its word: ends that leave to the
// left take the left half, the shortest outermost, and to the right likewise.
function anchors(arcs) {
  const at = new Map();
  for (const a of arcs) for (const [el, other, end] of [[a.from, a.to, 1], [a.to, a.from, 2]]) {
    if (!at.has(el)) at.set(el, []);
    at.get(el).push({ a, end, dist: other.cx - el.cx });
  }
  for (const [el, ends] of at) for (const side of [-1, 1]) {
    const these = ends.filter(e => Math.sign(e.dist) === side).sort((p, q) => Math.abs(p.dist) - Math.abs(q.dist));
    const n = these.length, step = Math.min(16, el.w / 2 / (n + 1));
    // the shortest arc sits furthest out, so the longer ones can pass over it
    these.forEach((e, i) => { e.a['x' + e.end] = el.cx + side * step * (n - i - .5); });
  }
}

// An arc whose two ends are in one written word (the bi- of bismi and its
// noun) goes under the word instead, where nothing else runs.
function place(arcs, em) {
  const done = [];
  for (const a of [...arcs].sort((p, q) => (p.hi - p.lo) - (q.hi - q.lo))) {
    if (a.under) {
      a.lx = (a.x1 + a.x2) / 2;
      shape(a, Math.max(a.y1, a.y2) + .5 * em);
      continue;
    }
    let top = Math.min(a.y1, a.y2) - (.5 * em + Math.min(a.hi - a.lo, 1000) * .04);
    for (const o of done) if (o.lo >= a.lo - 20 && o.hi <= a.hi + 20) top = Math.min(top, o.top - 44);
    a.lx = labelX(a, top, arcs.filter(o => !o.under), done);
    shape(a, top);
    // raised a little at a time until it is clear; an arc that will not
    // clear stays where it was rather than climbing off the page
    let k = 0;
    while (k < 16 && clash(a, done)) { shape(a, a.top - 6); k++; }
    if (k === 16 && clash(a, done)) shape(a, top);
    done.push(a);
  }
}

function buildArcs() {
  for (const dep of document.querySelectorAll('.dep[data-arcs]')) {
    const box = dep.getBoundingClientRect();
    const svg = svgEl('svg', { class: 'arcs', width: box.width, height: box.height });
    const paths = svgEl('g', {}), labels = svgEl('g', {});
    svg.append(paths, labels);
    dep.appendChild(svg);
    // the ends sit a little above the word, clear of its vowels
    const em = parseFloat(getComputedStyle(dep).fontSize);
    const lift = dep.dataset.lift !== undefined ? +dep.dataset.lift : -.1 * em;
    const t0 = dep.dataset.at !== undefined ? +dep.dataset.at : +dep.dataset.t + .9;
    const gap = +(dep.dataset.gap || .7);
    const words = new Map(), word = el => {
      if (!words.has(el)) {
        const r = el.getBoundingClientRect();
        words.set(el, { cx: r.left + r.width / 2 - box.left, y: r.top - box.top + lift,
          bottom: r.bottom - box.top + .05 * em, w: r.width });
      }
      return words.get(el);
    };
    const arcs = [];
    for (const spec of dep.dataset.arcs.split(';').filter(Boolean)) {
      const [ends, label, cls = ''] = spec.split(':');
      const [h, d] = ends.split('>');
      const a = dep.querySelector(`[data-n="${h}"]`), b = dep.querySelector(`[data-n="${d}"]`);
      if (!a || !b) { console.error(`arc ${spec}: no word ${a ? d : h}`); continue; }
      const arc = { cls, from: word(a), to: word(b), under: a.closest('.w') === b.closest('.w') };
      arc.y1 = arc.under ? arc.from.bottom : arc.from.y; arc.y2 = arc.under ? arc.to.bottom : arc.to.y;
      arc.g = svgEl('g', { class: 'alab ' + cls });
      arc.text = svgEl('text', { 'text-anchor': 'middle', 'dominant-baseline': 'central' });
      arc.text.textContent = label;
      arc.g.appendChild(arc.text);
      labels.appendChild(arc.g);
      const bb = arc.text.getBBox();
      arc.w = bb.width + 20; arc.h = bb.height + 6;
      arcs.push(arc);
    }
    anchors(arcs.filter(a => !a.under));
    for (const a of arcs) {
      if (a.under) { a.x1 = a.from.cx; a.x2 = a.to.cx; }
      a.lo = Math.min(a.x1, a.x2); a.hi = Math.max(a.x1, a.x2);
    }
    place(arcs, em);
    arcs.forEach((a, i) => {
      const t = +(t0 + i * gap).toFixed(2);
      const path = svgEl('path', { class: 'arc ' + a.cls, d: `M${a.x1} ${a.y1} C${a.x1} ${a.c} ${a.x2} ${a.c} ${a.x2} ${a.y2}` });
      paths.appendChild(path);
      const len = path.getTotalLength();
      path.setAttribute('stroke-dasharray', len);
      Object.assign(path.dataset, { t, a: 'draw', d: '.7', len });
      // the arrowhead comes straight down onto the word, or up from under it
      const s = a.under ? -15 : 15, x = a.x2, y = a.y2;
      const head = svgEl('polygon', { class: 'arrowhead ' + a.cls, points: `${x},${y} ${x - 8},${y - s} ${x + 8},${y - s}` });
      Object.assign(head.dataset, { t: (t + .55).toFixed(2), a: 'fade', d: '.3' });
      paths.appendChild(head);
      a.text.setAttribute('x', a.lx); a.text.setAttribute('y', a.top);
      const bb = a.text.getBBox();
      a.g.insertBefore(svgEl('rect', { x: bb.x - 10, y: bb.y - 3, width: bb.width + 20, height: bb.height + 6, rx: 8 }), a.text);
      Object.assign(a.g.dataset, { t: (t + .4).toFixed(2), a: 'fade', d: '.4' });
    });
  }
}

// ------------------------------------------------------------- timeline

let scenes = [], TOTAL = 0, stage, pattern, progress;

function item(el) {
  const ds = el.dataset, it = { el, t: +ds.t, d: +(ds.d || .8), a: ds.a || 'up' };
  it.out = ds.out !== undefined ? +ds.out : null;
  if (it.a === 'move') { it.x = +(ds.x || 0); it.y = +(ds.y || 0); it.s = +(ds.s || 1); it.fade = !!ds.fade; it.bump = +(ds.bump || 0); }
  if (it.a === 'count') { it.v = ds.k ? get(ds.k) : +ds.v; it.dec = +(ds.dec || 0); }
  if (it.a === 'barx') {
    const v = ds.k ? get(ds.k) : +ds.v, max = ds.of ? get(ds.of) : +ds.max;
    it.frac = max ? v / max : 0;
  }
  if (it.a === 'draw') it.len = +ds.len;
  return it;
}

function apply(it, lt) {
  const raw = clamp((lt - it.t) / it.d);
  const p = (it.a === 'move' ? easeInOut : easeOut)(raw);
  let o = 1, tf = null;
  switch (it.a) {
    case 'up':    o = p; tf = `translateY(${(1 - p) * 26}px)`; break;
    case 'left':  o = p; tf = `translateX(${-(1 - p) * 36}px)`; break;
    case 'fade':  o = p; break;
    case 'pop':   o = p; tf = `scale(${.6 + .4 * p})`; break;
    case 'zoom':  o = p; tf = `scale(${1.12 - .12 * p})`; break;
    case 'grow':  o = p; tf = `scaleX(${p})`; break;
    case 'move':  o = it.fade ? clamp(raw * 2) : 1;
                  tf = `translate(${it.x * (1 - p)}px,${it.y * (1 - p) - it.bump * Math.sin(Math.PI * p)}px) scale(${it.s + (1 - it.s) * p})`; break;
    case 'barx':  o = raw > 0 ? 1 : 0; tf = `scaleX(${p * it.frac})`; break;
    case 'wipe':  o = raw > 0 ? 1 : 0; it.el.style.clipPath = `inset(0 ${(1 - p) * 100}% 0 0)`; break;
    case 'count': o = clamp(raw * 4); it.el.textContent = fmt(it.dec ? it.v * p : Math.round(it.v * p), it.dec); break;
    case 'draw':  o = raw > 0 ? 1 : 0; it.el.style.strokeDashoffset = (1 - p) * it.len; break;
  }
  if (it.out !== null) o *= 1 - clamp((lt - it.out) / .45);
  it.el.style.opacity = o;
  if (tf) it.el.style.transform = tf;
}

function render(t) {
  for (const s of scenes) {
    const lt = t - s.start, on = lt >= 0 && lt < s.dur;
    s.style.visibility = on ? 'visible' : 'hidden';
    if (!on) continue;
    const fi = s.start === 0 ? 1 : clamp(lt / .45), fo = clamp((s.dur - lt) / s.fo);
    s.style.opacity = Math.min(fi, fo);
    for (const it of s.items) apply(it, lt);
  }
  pattern.style.transform = `translate(${-(t * 6) % 180}px,${-(t * 3.5) % 180}px)`;
  progress.style.transform = `scaleX(${clamp(t / TOTAL)})`;
}

// an eight-pointed star lattice, very faint, drifting
function drawPattern() {
  const star = (x, y) => `<rect x="${x - 26}" y="${y - 26}" width="52" height="52"/>` +
    `<rect x="${x - 26}" y="${y - 26}" width="52" height="52" transform="rotate(45 ${x} ${y})"/>`;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="180" height="180"><g fill="none" stroke="#fff" stroke-width="1.3">` +
    star(90, 90) + star(0, 0) + star(180, 0) + star(0, 180) + star(180, 180) +
    `<path d="M0 90H180M90 0V180" stroke-opacity=".45"/></g></svg>`;
  pattern.style.backgroundImage = `url("data:image/svg+xml,${encodeURIComponent(svg)}")`;
}

function fit() {
  const s = Math.min(innerWidth / 1920, innerHeight / 1080);
  stage.style.transform = `translate(${(innerWidth - 1920 * s) / 2}px,${(innerHeight - 1080 * s) / 2}px) scale(${s})`;
}

async function init(builders) {
  const ar = 'صرف نحو ابتثجحخدذرزسشصضطظعغفقكلمنهوي ٱ', lat = 'Ṣarf Naḥw ḍḥṭẓ ʿʾ āīū';
  await Promise.all(['400 100px Amiri', '700 100px Amiri'].map(f => document.fonts.load(f, ar))
    .concat(['400', '500', '600', '700', '800', 'italic 400'].map(w => document.fonts.load(`${w} 40px Inter`, lat))));
  await document.fonts.ready;
  if (!document.fonts.check('100px Amiri', 'ص')) console.error('Amiri did not load');
  if (!document.fonts.check('40px Inter', 'a')) console.error('Inter did not load');

  stage = document.getElementById('stage');
  pattern = document.getElementById('pattern');
  progress = document.getElementById('progress');
  scenes = [...document.querySelectorAll('.scene')];
  for (const build of builders) build();
  fill();
  for (const el of document.querySelectorAll('[data-m]')) paint(el);
  drawPattern();
  buildLinks();
  buildArcs();
  for (const s of scenes) {
    s.start = TOTAL; s.dur = +s.dataset.dur; s.fo = +(s.dataset.fo || .45); TOTAL += s.dur;
    s.items = [...s.querySelectorAll('[data-t]')].map(item);
  }
  window.FILM_TOTAL = TOTAL;
  window.renderAt = render;
  render(0);

  if (window.__capture) return;
  // played in a browser: real time, with a pause and a skip
  fit(); addEventListener('resize', fit);
  const hud = document.getElementById('hud');
  let base = performance.now() / 1000 - (parseFloat((location.hash.match(/t=([\d.]+)/) || [])[1]) || 0);
  let paused = null;
  const now = () => (paused !== null ? paused : (performance.now() / 1000 - base) % TOTAL);
  const toggle = () => { if (paused === null) paused = now(); else { base = performance.now() / 1000 - paused; paused = null; } };
  addEventListener('click', toggle);
  addEventListener('keydown', e => {
    if (e.key === ' ') { toggle(); e.preventDefault(); }
    const skip = { ArrowRight: 5, ArrowLeft: -5 }[e.key];
    if (skip) { const t = clamp(now() + skip, 0, TOTAL - .01); if (paused !== null) paused = t; else base = performance.now() / 1000 - t; }
  });
  (function loop() {
    const t = now(); render(t);
    hud.textContent = `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, '0')} / ${Math.floor(TOTAL / 60)}:${String(Math.round(TOTAL % 60)).padStart(2, '0')}${paused !== null ? ' · pauze' : ''}`;
    requestAnimationFrame(loop);
  })();
}

window.Film = {
  fmt, get, html, clamp,
  start(builders = []) { window.FILM_READY = init(builders); return window.FILM_READY; },
};
})();
