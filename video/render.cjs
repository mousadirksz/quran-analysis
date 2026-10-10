#!/usr/bin/env node
// Draw a film page (video/sarf.html, video/nahw.html) frame by frame and
// encode the frames with ffmpeg.
//
// sarf_video.py and nahw_video.py call this after writing the page's data;
// see there for what each film shows and where its figures come from. The page draws any moment on
// request (window.renderAt), so the film is cut into one stretch per worker,
// each stretch is encoded on its own, and the stretches are joined without
// re-encoding. Each worker gets a browser of its own: pages in one browser
// share its compositor, and with four of them it was the only thing busy.
// Frames are taken through the DevTools protocol with optimizeForSpeed, a
// faster PNG encoder than page.screenshot uses -- 150 ms a frame against 530,
// and still lossless.
//
//   node video/render.cjs [--html video/nahw.html] [--out video/nahw.mp4] [--fps 30] [--workers 4]
//   node video/render.cjs [--html ...] --stills 12,95.5 [--dir video/stills]
//
// --html defaults to video/sarf.html, --out to the page's name with .mp4.

const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const argv = process.argv.slice(2);
const opt = (name, dflt) => { const i = argv.indexOf(name); return i >= 0 ? argv[i + 1] : dflt; };
const HTML = path.resolve(opt('--html', path.join(__dirname, 'sarf.html')));
const OUT = path.resolve(opt('--out', HTML.replace(/\.html$/, '.mp4')));
const FPS = +opt('--fps', 30);
const WORKERS = +opt('--workers', Math.max(1, Math.min(4, os.cpus().length)));
const STILLS = opt('--stills', null);
const DIR = path.resolve(opt('--dir', path.join(__dirname, 'stills')));

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push(String(e)));
  page.on('requestfailed', r => errors.push(`${r.url()}: ${r.failure() && r.failure().errorText}`));
  await page.addInitScript(() => { window.__capture = true; });
  await page.goto('file://' + HTML, { waitUntil: 'networkidle' });
  await page.evaluate(() => window.FILM_READY);
  if (errors.length) throw new Error('the page reported:\n  ' + errors.join('\n  '));
  return page;
}

function run(cmd, args, input) {
  const p = spawn(cmd, args, { stdio: [input ? 'pipe' : 'ignore', 'ignore', 'pipe'] });
  let err = '';
  p.stderr.on('data', d => { err = (err + d).slice(-4000); });
  const done = new Promise((resolve, reject) => p.on('close', code =>
    code === 0 ? resolve() : reject(new Error(`${cmd} exited with ${code}:\n${err}`))));
  return { p, done };
}

const write = (stream, buf) => new Promise(resolve => {
  if (stream.write(buf)) resolve(); else stream.once('drain', resolve);
});

async function stretch(from, to, file, report) {
  const browser = await launch();
  const page = await openPage(browser);
  const cdp = await page.context().newCDPSession(page);
  // BT.709 is what a player assumes for HD; ffmpeg's default would be BT.601
  const ff = run('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS),
    '-c:v', 'png', '-i', '-', '-vf', 'scale=out_color_matrix=bt709:out_range=tv,format=yuv420p',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-g', String(FPS * 2),
    '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
    '-r', String(FPS), file], true);
  for (let f = from; f < to; f++) {
    await page.evaluate(t => window.renderAt(t), f / FPS);
    const shot = await cdp.send('Page.captureScreenshot', { format: 'png', optimizeForSpeed: true });
    await write(ff.p.stdin, Buffer.from(shot.data, 'base64'));
    report();
  }
  ff.p.stdin.end();
  await ff.done;
  await browser.close();
}

function launch() {
  const proxy = process.env.HTTPS_PROXY || process.env.https_proxy;
  return chromium.launch(proxy ? { proxy: { server: proxy } } : {});
}

(async () => {
  const browser = await launch();
  try {
    if (STILLS) {
      fs.mkdirSync(DIR, { recursive: true });
      const page = await openPage(browser);
      for (const s of STILLS.split(',').map(Number)) {
        await page.evaluate(t => window.renderAt(t), s);
        const file = path.join(DIR, `still-${String(s).replace('.', '_')}.png`);
        await page.screenshot({ path: file });
        console.log(path.relative(process.cwd(), file));
      }
      return;
    }
    const probe = await openPage(browser);
    const total = await probe.evaluate(() => window.FILM_TOTAL);
    await probe.close();
    await browser.close();
    const frames = Math.round(total * FPS), per = Math.ceil(frames / WORKERS);
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'film-'));
    console.log(`${total} s, ${frames} frames at ${FPS} fps, ${WORKERS} workers`);
    let done = 0, last = 0;
    const start = Date.now();
    const report = () => {
      done++;
      if (done - last >= frames / 20 || done === frames) {
        last = done;
        console.log(`  ${Math.round(100 * done / frames)}% after ${Math.round((Date.now() - start) / 1000)} s`);
      }
    };
    const parts = [];
    for (let w = 0; w < WORKERS; w++) {
      const from = w * per, to = Math.min(frames, from + per);
      if (from < to) parts.push({ from, to, file: path.join(tmp, `part${w}.mp4`) });
    }
    await Promise.all(parts.map(p => stretch(p.from, p.to, p.file, report)));
    const list = path.join(tmp, 'parts.txt');
    fs.writeFileSync(list, parts.map(p => `file '${p.file}'`).join('\n') + '\n');
    fs.mkdirSync(path.dirname(OUT), { recursive: true });
    await run('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list,
      '-c', 'copy', '-movflags', '+faststart', OUT]).done;
    fs.rmSync(tmp, { recursive: true, force: true });
    console.log(path.relative(process.cwd(), OUT));
  } finally {
    if (browser.isConnected()) await browser.close();
  }
})().catch(e => { console.error(e.message || e); process.exit(1); });
