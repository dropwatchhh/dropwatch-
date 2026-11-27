// Serve render3d/ locally, open stage.html in headless Chromium (software WebGL), screenshot angles.
import http from 'http';
import fs from 'fs';
import path from 'path';
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const { chromium } = require('/opt/node22/lib/node_modules/playwright');

const root = path.dirname(new URL(import.meta.url).pathname);
const outDir = process.argv[2];
const views = JSON.parse(process.argv[3] || '[["front",0],["three_quarter",35],["side",90],["back",180]]');
const types = { '.html': 'text/html', '.mjs': 'text/javascript', '.js': 'text/javascript' };
const server = http.createServer((q, r) => {
  const f = path.join(root, decodeURIComponent(q.url.split('?')[0]).replace(/^\/+/, '') || 'stage.html');
  if (!f.startsWith(root) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { r.writeHead(404); return r.end(); }
  r.writeHead(200, { 'content-type': types[path.extname(f)] || 'application/octet-stream' }); fs.createReadStream(f).pipe(r);
}).listen(0, '127.0.0.1');
await new Promise(r => server.on('listening', r));
const port = server.address().port;

const b = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--enable-webgl'] });
const p = await b.newPage({ viewport: { width: 800, height: 1000 }, deviceScaleFactor: 1 });
p.on('console', m => { if (['error', 'warning'].includes(m.type())) console.log('[page]', m.text().slice(0, 200)); });
p.on('pageerror', e => console.log('[pageerror]', e.message.slice(0, 300)));
await p.goto(`http://127.0.0.1:${port}/stage.html?w=800&h=1000`);
await p.waitForFunction('window.ready === true', null, { timeout: 120000 });
fs.mkdirSync(outDir, { recursive: true });
for (const [name, deg, dist, h, look] of views) {
  await p.evaluate(a => window.shot(...a), [deg, dist, h, look].map(v => v ?? undefined));
  await p.screenshot({ path: `${outDir}/dex_${name}.png` });
  console.log('shot', name);
}
await b.close(); server.close();
