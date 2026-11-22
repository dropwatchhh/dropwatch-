"""Local web board. Binds to loopback by default; any other bind requires BOARD_TOKEN."""
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from engine import cash_out
from signals import MODES

LOOPBACK = ("127.0.0.1", "localhost", "::1")


def validate_bind(host, token):
    """Refuse to expose the board without a strong token."""
    if host not in LOOPBACK and (not token or len(token) < 16):
        raise SystemExit("Refusing to bind the board to a non-loopback address without "
                         "BOARD_TOKEN (>= 16 chars). Set it, or use --host 127.0.0.1.")


PAGE = r"""<!doctype html><html lang=en><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>Kalshi Board</title>
<style>
:root{--bg:#0b0f14;--card:#151b23;--fg:#e6edf3;--mut:#8b98a5;--ok:#2ea043;--bad:#f85149;--warn:#d29922;--acc:#388bfd}
@media(prefers-color-scheme:light){:root{--bg:#f4f6f8;--card:#fff;--fg:#17202a;--mut:#5b6773}}
*{box-sizing:border-box}body{font:15px/1.4 system-ui,sans-serif;margin:0;padding:12px 16px;background:var(--bg);color:var(--fg);max-width:720px;margin:auto}
.c{background:var(--card);border-radius:12px;padding:14px;margin:10px 0}.row{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}
.mut{color:var(--mut)}.big{font-size:22px;font-weight:650}.pos{color:var(--ok)}.neg{color:var(--bad)}
.tag{padding:2px 8px;border-radius:99px;font-size:12px;font-weight:650;background:var(--warn);color:#000}.tag.live{background:var(--bad);color:#fff}
.sw{position:relative;width:76px;height:40px;flex:none}.sw input{opacity:0;width:100%;height:100%;position:absolute;margin:0;cursor:pointer;z-index:2}
.sw span{position:absolute;inset:0;background:#555;border-radius:40px;transition:.2s}.sw span:before{content:"";position:absolute;width:32px;height:32px;left:4px;top:4px;background:#fff;border-radius:50%;transition:.2s}
.sw input:checked+span{background:var(--ok)}.sw input:checked+span:before{transform:translateX(36px)}
button{padding:11px 16px;border-radius:10px;border:0;font-size:16px;background:var(--acc);color:#fff}button.x{background:var(--warn);color:#000;font-weight:650}
button.m{background:#30363d;color:var(--fg);padding:8px 12px;font-size:14px}button.m.sel{background:var(--acc);color:#fff}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:6px 14px;margin:8px 0}.grid b{display:block;font-size:16px}
ul{margin:6px 0 0;padding-left:18px;font-size:13px}pre{white-space:pre-wrap;font-size:12px;margin:0;max-height:300px;overflow:auto}
</style>
<div class=c><div class=row><div><span id=tag class=tag></span> <span class=mut>PnL today</span> <span id=pnl class=big></span>
<div class=mut id=meta></div></div><label class=sw><input type=checkbox id=arm><span></span></label></div>
<div class=row style="margin-top:10px"><div id=modes></div><div class=mut id=halt></div></div></div>
<div id=rounds></div><div class=c><b>Log</b> <span class=mut>(last 50)</span><pre id=log></pre></div>
<script>
let TOKEN=new URLSearchParams(location.search).get('t')||sessionStorage.getItem('tok')||'';
const $=id=>document.getElementById(id);
function h(t,a,...k){const e=document.createElement(t);for(const[x,v]of Object.entries(a||{}))x==='class'?e.className=v:x.startsWith('on')?e[x]=v:e.setAttribute(x,v);
 for(const c of k.flat())e.append(c&&c.nodeType?c:document.createTextNode(c??''));return e}
async function api(p,body){const o={headers:{'X-Token':TOKEN,'X-Board':'1'}};
 if(body!==undefined){o.method='POST';o.headers['Content-Type']='application/json';o.body=JSON.stringify(body)}
 const r=await fetch(p,o);if(r.status===401){TOKEN=prompt('Board token')||'';sessionStorage.setItem('tok',TOKEN);return null}return r.json()}
const f=(v,d=2)=>v==null?'-':Number(v).toFixed(d);
function kv(k,v){return h('div',{},h('span',{class:'mut'},k),h('b',{},v))}
function render(d){
 $('tag').textContent=d.live?'LIVE':'PAPER';$('tag').className='tag'+(d.live?' live':'');
 $('pnl').textContent=(d.pnl>=0?'+$':'-$')+Math.abs(d.pnl).toFixed(2);$('pnl').className='big '+(d.pnl>=0?'pos':'neg');
 $('meta').textContent=`cap -$${d.cap} | streak ${d.loss_streak}/${d.max_streak} | size $${d.size}`+(d.balance!=null?` | bal $${f(d.balance)}`:'');
 $('arm').checked=d.armed;$('halt').textContent=d.halted?('HALTED: '+d.halted):(d.armed?'ARMED':'DISARMED');
 $('modes').replaceChildren(...d.modes.map(m=>h('button',{class:'m'+(m===d.mode?' sel':''),onclick:async()=>{await api('/api/mode',{mode:m});load()}},m)));
 $('rounds').replaceChildren(...Object.entries(d.last).map(([a,r])=>{
  const p=r.position;const hl=r.high_low||[];
  return h('div',{class:'c'},h('div',{class:'row'},h('b',{},a+' '+r.ticker),h('span',{class:'mut'},r.secs_left+'s left'+(r.fresh?'':' - STALE'))),
   h('div',{class:'grid'},kv('Price',f(r.price)),kv('Target',f(r.target)),kv('Distance',f(r.z)+' sigma'),kv('Likely side',(r.likely||'-')+' '+(r.p_up==null?'':f((r.likely==='DOWN'?1-r.p_up:r.p_up)*100,0)+'%')),
    kv('Momentum 2m',r.momentum==null?'-':f(r.momentum,3)+'%'),kv('Vol /min',r.vol==null?'-':f(r.vol,3)+'%'),kv('Market P(up)',f(r.p_market,2)),kv('10m hi/lo',f(hl[0])+' / '+f(hl[1]))),
   h('div',{},h('b',{},r.action),': ',r.why),
   h('ul',{},(r.reasoning||[]).map(x=>h('li',{},x))),
   p?h('div',{class:'row',style:'margin-top:10px'},h('span',{},`Position: ${p.count} ${p.side.toUpperCase()} @ ${f(p.price,3)}`),
     h('button',{class:'x',onclick:async()=>{const x=await api('/api/cashout',{ticker:r.ticker});alert(x&&x.result);load()}},'Cash out')):'')}));
 $('log').textContent=d.log.join('\n')}
async function load(){try{const d=await api('/api/status');if(d)render(d)}catch(e){}}
$('arm').onchange=async e=>{const r=await api('/api/arm',{armed:e.target.checked});load()};
load();setInterval(load,2000)
</script></html>"""


def make_handler(client, st, live, fee_mult=1.0):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body, ctype="application/json"):
            b = body if isinstance(body, bytes) else body.encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(b)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(b)

        def _token(self):
            return os.getenv("BOARD_TOKEN") or ""

        def _host_ok(self):
            """Anti DNS-rebinding: without a token, only accept loopback Host headers."""
            if self._token():
                return True
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]")
            return host in LOOPBACK

        def _authed(self):
            tok = self._token()
            return not tok or hmac.compare_digest(self.headers.get("X-Token", ""), tok)

        def do_GET(self):
            if not self._host_ok():
                return self._send(403, "{}")
            path = urlparse(self.path).path
            if path == "/api/status":
                if not self._authed():
                    return self._send(401, "{}")
                with st.lock:
                    c = st.cfg
                    return self._send(200, json.dumps(dict(
                        armed=st.armed, halted=st.halted, mode=c["mode"], modes=list(MODES), live=live,
                        pnl=round(st.pnl, 2), loss_streak=st.loss_streak, max_streak=c["max_losses_in_row"],
                        cap=c["daily_loss_cap_usd"], size=c["size_per_trade_usd"], balance=st.balance,
                        last=st.last, log=list(st.log))))
            if path in ("/", "/index.html"):
                return self._send(200, PAGE, "text/html; charset=utf-8")
            self._send(404, "{}")

        def do_POST(self):
            # custom header forces a CORS preflight, which we never grant => no cross-site POSTs
            if not self._host_ok() or self.headers.get("X-Board") != "1":
                return self._send(403, "{}")
            if not self._authed():
                return self._send(401, "{}")
            try:
                n = min(int(self.headers.get("Content-Length", 0)), 4096)
                data = json.loads(self.rfile.read(n) or "{}")
            except Exception:
                return self._send(400, "{}")
            path = urlparse(self.path).path
            if path == "/api/arm":
                with st.lock:
                    if data.get("armed") and st.halted:
                        return self._send(409, json.dumps(dict(error=f"halted: {st.halted}")))
                    st.armed = bool(data.get("armed"))
                    st.note("ARMED" if st.armed else "DISARMED")
                return self._send(200, "{}")
            if path == "/api/mode":
                if data.get("mode") not in MODES:
                    return self._send(400, "{}")
                with st.lock:
                    st.cfg["mode"] = data["mode"]
                    st.note(f"mode -> {data['mode']}")
                return self._send(200, "{}")
            if path == "/api/cashout":
                try:
                    res = cash_out(client, st, str(data.get("ticker", "")), live, fee_mult)
                except Exception as e:
                    res = f"cash-out error: {e}"
                return self._send(200, json.dumps(dict(result=res)))
            self._send(404, "{}")
    return H


def serve(client, st, live, host, port, fee_mult=1.0):
    validate_bind(host, os.getenv("BOARD_TOKEN"))
    return ThreadingHTTPServer((host, port), make_handler(client, st, live, fee_mult))
