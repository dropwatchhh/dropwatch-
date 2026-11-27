// usage: node render_anim.mjs OUTDIR frames.json [first last]   frames.json = {shots:{S1:{job:{...}}}, frames:[{n,shot,t,g,dur,lip,blink,amp,emph}]}
import http from 'http'; import fs from 'fs'; import path from 'path'; import { createRequire } from 'module';
const require = createRequire(import.meta.url); const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const root = path.dirname(new URL(import.meta.url).pathname);
const [outDir, fj, a = '0', bz = '99999'] = process.argv.slice(2); const T = JSON.parse(fs.readFileSync(fj));
const types = { '.html': 'text/html', '.mjs': 'text/javascript', '.js': 'text/javascript', '.glb': 'model/gltf-binary', '.json': 'application/json', '.png': 'image/png' };
const server = http.createServer((q, r) => { const rel = decodeURIComponent(q.url.split('?')[0]).replace(/^\/+/, ''); const base = rel.startsWith('assets/') ? path.join(root, '..') : root; const f = path.join(base, rel); if (!f.startsWith(base) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { r.writeHead(404); return r.end(); } r.writeHead(200, { 'content-type': types[path.extname(f)] || 'application/octet-stream' }); fs.createReadStream(f).pipe(r); }).listen(0, '127.0.0.1');
await new Promise(r => server.on('listening', r));
const b = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--enable-webgl'] });
const p = await b.newPage({ viewport: { width: 1200, height: 1200 }, deviceScaleFactor: 1 });
p.on('console', m => { if (m.type() === 'error') console.log('[page]', m.text().slice(0, 300)); }); p.on('pageerror', e => console.log('[pageerror]', e.message.slice(0, 400)));
await p.goto(`http://127.0.0.1:${server.address().port}/stage_anim.html`); await p.waitForFunction('window.ready === true', null, { timeout: 120000 });
fs.mkdirSync(outDir, { recursive: true }); let cur = null;
for (const f of T.frames) {
  if (f.n < +a || f.n > +bz) continue;
  const t0 = Date.now();
  if (cur !== f.shot) { await p.evaluate(j => window.job(j), { ...T.shots[f.shot].job, norender: true, w: T.w, h: T.h }); cur = f.shot; }
  await p.evaluate(x => window.frame(x), f);
  if (process.env.BBOX && f.n === +a) console.log(await p.evaluate(() => { const o = window.H.dex?.root; if (!o) return 'nodex'; const B = new window.THREE_Box3().setFromObject(o); const hh = window.H.dex.headRoot; const hb = new window.THREE_Box3().setFromObject(hh); return JSON.stringify({ body: [B.min.toArray(), B.max.toArray()], head: [hb.min.toArray(), hb.max.toArray()] }); }));
  const buf = await p.evaluate(() => document.querySelector('canvas').toDataURL('image/png').split(',')[1]);
  fs.writeFileSync(`${outDir}/f${String(f.n).padStart(4, '0')}.png`, Buffer.from(buf, 'base64')); console.log('frame', f.n, f.shot, Date.now() - t0, 'ms');
}
await b.close(); server.close();
