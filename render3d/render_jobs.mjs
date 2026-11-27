// usage: node render_jobs.mjs <outDir> '<json array of {name,w,h,pose,expr,deg,dist,camY,look,fov}>'
import http from 'http';
import fs from 'fs';
import path from 'path';
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const root = path.dirname(new URL(import.meta.url).pathname);
const [outDir, jobsJson, page = 'stage2.html'] = process.argv.slice(2);
const jobs = JSON.parse(jobsJson);
const types = { '.html': 'text/html', '.mjs': 'text/javascript', '.js': 'text/javascript', '.glb': 'model/gltf-binary', '.json': 'application/json', '.png': 'image/png' };
const server = http.createServer((q, r) => {
  const rel = decodeURIComponent(q.url.split('?')[0]).replace(/^\/+/, '');
  const base = rel.startsWith('assets/') ? path.join(root, '..') : root;
  const f = path.join(base, rel);
  if (!f.startsWith(base) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { r.writeHead(404); return r.end(); }
  r.writeHead(200, { 'content-type': types[path.extname(f)] || 'application/octet-stream' }); fs.createReadStream(f).pipe(r);
}).listen(0, '127.0.0.1');
await new Promise(r => server.on('listening', r));
const b = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--enable-webgl'] });
const p = await b.newPage({ viewport: { width: 1200, height: 1200 }, deviceScaleFactor: 1 });
p.on('console', m => { if (m.type() === 'error') console.log('[page]', m.text().slice(0, 300)); });
p.on('pageerror', e => console.log('[pageerror]', e.message.slice(0, 400)));
await p.goto(`http://127.0.0.1:${server.address().port}/${page}`);
await p.waitForFunction('window.ready === true', null, { timeout: 120000 });
fs.mkdirSync(outDir, { recursive: true });
for (const j of jobs) {
  const t0 = Date.now();
  await p.evaluate(j2 => window.job(j2), j);
  const buf = await p.evaluate(() => document.querySelector('canvas').toDataURL('image/png').split(',')[1]);
  const ms = Date.now() - t0;
  fs.writeFileSync(`${outDir}/${j.name}.png`, Buffer.from(buf, 'base64'));
  console.log('shot', j.name, ms + ' ms');
}
await b.close(); server.close();
