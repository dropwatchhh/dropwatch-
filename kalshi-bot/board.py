"""Local web board. Binds to loopback by default; any other bind requires BOARD_TOKEN."""
import hmac
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import kill
import preflight
from engine import cash_out
from pilot import ENABLE_PHRASE, RESET_PHRASE_1, RESET_PHRASE_2, PilotError
from signals import MODES

LOOPBACK = ("127.0.0.1", "localhost", "::1")


def validate_bind(host, token):
    """Refuse to expose the board without a strong token."""
    if host not in LOOPBACK and (not token or len(token) < 16):
        raise SystemExit("Refusing to bind the board to a non-loopback address without "
                         "BOARD_TOKEN (>= 16 chars). Set it, or use --host 127.0.0.1.")


COMMON_CSS = r"""
:root{--bg:#0b0f14;--card:#151b23;--fg:#e6edf3;--mut:#8b98a5;--ok:#2ea043;--bad:#f85149;--warn:#d29922;--acc:#388bfd}
@media(prefers-color-scheme:light){:root{--bg:#f4f6f8;--card:#fff;--fg:#17202a;--mut:#5b6773}}
*{box-sizing:border-box}body{font:15px/1.4 system-ui,sans-serif;margin:0;padding:52px 16px 84px;background:var(--bg);color:var(--fg);max-width:720px;margin:auto}
#banner{position:fixed;top:0;left:0;right:0;z-index:10;padding:8px 12px;text-align:center;font-weight:700;letter-spacing:.04em;color:#fff}
#banner.live{background:#d1242f}#banner.locked{background:#57606a}#banner.paper{background:#9a6700;font-weight:600}
nav{display:flex;gap:6px;margin:6px 0 4px}nav a{padding:7px 14px;border-radius:9px;background:#30363d;color:#e6edf3;text-decoration:none;font-size:14px}nav a.on{background:var(--acc);color:#fff}
#stopbar{position:fixed;bottom:0;left:0;right:0;z-index:10;padding:10px 12px;background:var(--bg);border-top:1px solid #30363d}
#stopbar button{width:100%;max-width:720px;display:block;margin:auto;background:#d1242f;color:#fff;font-weight:800;font-size:17px;padding:14px}
.c{background:var(--card);border-radius:12px;padding:14px;margin:10px 0}.row{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}
.mut{color:var(--mut)}.big{font-size:22px;font-weight:650}.pos{color:var(--ok)}.neg{color:var(--bad)}
.tag{padding:2px 8px;border-radius:99px;font-size:12px;font-weight:650;background:var(--warn);color:#000}.tag.live{background:var(--bad);color:#fff}
.sw{position:relative;width:76px;height:40px;flex:none}.sw input{opacity:0;width:100%;height:100%;position:absolute;margin:0;cursor:pointer;z-index:2}
.sw span{position:absolute;inset:0;background:#555;border-radius:40px;transition:.2s}.sw span:before{content:"";position:absolute;width:32px;height:32px;left:4px;top:4px;background:#fff;border-radius:50%;transition:.2s}
.sw input:checked+span{background:var(--ok)}.sw input:checked+span:before{transform:translateX(36px)}
button{padding:11px 16px;border-radius:10px;border:0;font-size:16px;background:var(--acc);color:#fff}button.x{background:var(--warn);color:#000;font-weight:650}
button.m{background:#30363d;color:#e6edf3;padding:8px 12px;font-size:14px}button.m.sel{background:var(--acc);color:#fff}button.dng{background:#d1242f}
input[type=text],input[type=number]{width:100%;padding:10px;border-radius:8px;border:1px solid #30363d;background:var(--bg);color:var(--fg);font-size:15px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:6px 14px;margin:8px 0}.grid b{display:block;font-size:16px}
ul{margin:6px 0 0;padding-left:18px;font-size:13px}pre{white-space:pre-wrap;font-size:12px;margin:0;max-height:300px;overflow:auto}
.ck{display:flex;gap:8px;font-size:14px;margin:4px 0}.ck i{font-style:normal;font-weight:800;width:44px;flex:none}.ck .p{color:var(--ok)}.ck .f{color:var(--bad)}
table{width:100%;border-collapse:collapse;font-size:13px}td,th{padding:4px 6px;border-bottom:1px solid #30363d;text-align:left;vertical-align:top}
"""

COMMON_JS = r"""
let TOKEN=new URLSearchParams(location.search).get('t')||sessionStorage.getItem('tok')||'';
const $=id=>document.getElementById(id);
function h(t,a,...k){const e=document.createElement(t);for(const[x,v]of Object.entries(a||{}))x==='class'?e.className=v:x.startsWith('on')?e[x]=v:e.setAttribute(x,v);
 for(const c of k.flat())e.append(c&&c.nodeType?c:document.createTextNode(c??''));return e}
async function api(p,body){const o={headers:{'X-Token':TOKEN,'X-Board':'1'}};
 if(body!==undefined){o.method='POST';o.headers['Content-Type']='application/json';o.body=JSON.stringify(body)}
 const r=await fetch(p,o);if(r.status===401){TOKEN=prompt('Board token')||'';sessionStorage.setItem('tok',TOKEN);return null}return r.json()}
const f=(v,d=2)=>v==null?'-':Number(v).toFixed(d);
const money=v=>(v>=0?'+$':'-$')+Math.abs(v).toFixed(2);
function kv(k,v){return h('div',{},h('span',{class:'mut'},k),h('b',{},v))}
function banner(d){const b=$('banner');
 if(d.live_enabled){b.className='live';b.textContent='● LIVE — REAL MONEY ●'}
 else if(d.live){b.className='locked';b.textContent='LIVE PILOT LOADED — LOCKED (not trading)'}
 else{b.className='paper';b.textContent='PAPER — simulated money'}}
async function stopNow(){const x=await api('/api/stop',{});if(x)alert((x.steps||[]).join('\n'))}
"""


def banner_html(st, live):
    on = bool(st.pilot and st.pilot.live_enabled)
    cls, txt = (("live", "● LIVE — REAL MONEY ●") if on else
                (("locked", "LIVE PILOT LOADED — LOCKED (not trading)") if live else ("paper", "PAPER — simulated money")))
    return f'<div id=banner class="{cls}">{txt}</div>'


def page(st, live, active, body, script):
    nav = "".join(f'<a href="{href}" class="{"on" if key == active else ""}">{label}</a>'
                  for key, href, label in (("board", "/", "Board"), ("trading", "/trading", "Trading"), ("log", "/log", "Log")))
    return ('<!doctype html><html lang=en><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">'
            f'<title>Kalshi Board</title><style>{COMMON_CSS}</style>{banner_html(st, live)}<nav>{nav}</nav>{body}'
            '<div id=stopbar><button class=dng onclick="stopNow()">STOP TRADING NOW</button></div>'
            f'<script>{COMMON_JS}{script}</script></html>')


BOARD_BODY = r"""<div class=c><div class=row><div><span id=tag class=tag></span> <span class=mut>PnL today</span> <span id=pnl class=big></span>
<div class=mut id=meta></div></div><label class=sw><input type=checkbox id=arm><span></span></label></div>
<div class=row style="margin-top:10px"><div id=modes></div><div class=mut id=halt></div></div></div>
<div id=rounds></div><div class=c><b>Log</b> <span class=mut>(last 50)</span><pre id=log></pre></div>
"""
BOARD_JS = r"""
function render(d){banner(d);
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
   r.pilot?h('div',{class:'mut'},h('b',{},r.pilot.grade),' | flip risk: ',r.pilot.flip.label,' | ',r.pilot.failed.length?('failed: '+r.pilot.failed.join('; ')):'all checks passed'):'',
   h('ul',{},(r.reasoning||[]).map(x=>h('li',{},x))),
   p?h('div',{class:'row',style:'margin-top:10px'},h('span',{},`Position: ${p.count} ${p.side.toUpperCase()} @ ${f(p.price,3)}`),
     h('button',{class:'x',onclick:async()=>{const x=await api('/api/cashout',{ticker:r.ticker});alert(x&&x.result);load()}},'Cash out')):'')}));
 $('log').textContent=d.log.join('\n')}

async function load(){try{const d=await api('/api/status');if(d)render(d)}catch(e){}}
$('arm').onchange=async e=>{const r=await api('/api/arm',{armed:e.target.checked});if(r&&r.error)alert(r.error);load()};
load();setInterval(load,2000)
"""



TRADING_BODY = r"""
<div class=c><b>LIVE pilot</b> <span class=mut id=t_state></span><div id=t_checks style="margin-top:8px"></div>
 <div class=row style="margin-top:8px"><button class=m onclick="recheck()">Re-run checks (incl. shard)</button><span class=mut id=t_demo></span></div></div>
<div class=c id=t_enable><b>Enable LIVE</b><div class=mut style="margin:6px 0">Type exactly: <code id=t_phrase></code></div>
 <input type=text id=t_in autocomplete=off autocapitalize=off spellcheck=false placeholder="type the phrase">
 <div class=row style="margin-top:8px"><button class=dng onclick="enableLive()">Enable LIVE</button><button class=m onclick="disableLive()">Disable LIVE</button></div>
 <div class=mut style="margin-top:6px">Enabling LIVE does not arm the bot. Arm it on the Board once you are ready.</div></div>
<div class=c><b>Loss breakers</b><div id=t_brk class=grid></div><div id=t_reset></div></div>
<div class=c><b>Pilot limits</b> <span class=mut>(you can lower these; the maximums are fixed in code)</span><table id=t_lim></table></div>
"""
TRADING_JS = r"""
let TD=null;
async function loadT(){const d=await api('/api/trading');if(!d)return;if(d.error){document.body.insertBefore(h('div',{class:'c'},'Not a live-pilot process. Start with --live and a live config (see PILOT.md).'),$('t_checks').parentNode);return}TD=d;banner(d);
 $('t_state').textContent=d.pilot.live_enabled?'LIVE is ENABLED':'LIVE is OFF';
 $('t_phrase').textContent=d.enable_phrase;
 $('t_checks').replaceChildren(...d.readiness.checks.map(c=>h('div',{class:'ck'},h('i',{class:c.ok?'p':'f'},c.ok?'PASS':'FAIL'),h('span',{},c.name+(c.detail?' - '+c.detail:'')))));
 $('t_demo').textContent=d.demo_detail||'';
 const p=d.pilot;
 $('t_brk').replaceChildren(kv('Today (UTC)',money(p.daily_pnl)+(p.daily_paused?' PAUSED':'')),kv('Pause at','-$'+p.limits.daily_pause_usd.toFixed(2)),
  kv('Since start/reset',money(p.drawdown)),kv('Hard stop at','-$'+p.limits.hard_stop_usd.toFixed(2)),kv('Trades today',p.trades_today+' / '+p.limits.trades_per_day));
 const r=$('t_reset');r.replaceChildren();
 if(p.hard_stopped){r.append(h('div',{class:'neg'},'HARD STOP: '+p.hard_stop_reason),
  h('div',{class:'mut'},p.reset_stage===0?'Reset step 1 of 2 - type: '+d.reset_phrases[0]:'Reset step 2 of 2 - type: '+d.reset_phrases[1]),
  h('input',{type:'text',id:'t_rin',autocomplete:'off'}),h('button',{class:'dng',onclick:resetStop},'Confirm reset step '+(p.reset_stage+1)))}
 $('t_lim').replaceChildren(h('tr',{},h('th',{},'limit'),h('th',{},'now'),h('th',{},'max'),h('th',{},'lower to')),
  ...Object.keys(p.maximums).map(k=>h('tr',{},h('td',{},k),h('td',{},p.limits[k]),h('td',{},p.maximums[k]),
   h('td',{},h('input',{type:'number',step:'any',min:'0',id:'lim_'+k,style:'width:80px'}),h('button',{class:'m',onclick:()=>lower(k)},'Lower')))))}
async function post(path,body){const x=await api(path,body);if(x&&x.error)alert(x.error);await loadT();return x}
async function enableLive(){await post('/api/live/enable',{phrase:$('t_in').value});$('t_in').value=''}
async function disableLive(){await post('/api/live/disable',{})}
async function recheck(){await post('/api/preflight/shard',{})}
async function resetStop(){const v=$('t_rin').value;await post('/api/hardstop/reset',{phrase:v})}
async function lower(k){const v=parseFloat($('lim_'+k).value);if(isNaN(v)){alert('enter a number');return}await post('/api/limits/lower',{name:k,value:v})}
loadT();setInterval(loadT,5000)
"""

LOG_BODY = r"""
<div class=c><b>Real P&amp;L (live, after fees)</b><div id=l_sum class=grid></div></div>
<div class=c><b>Post-mortems</b> <span class=mut>(automatic, one per loss; descriptive only, nothing is retrained or re-tuned)</span><div id=l_pm></div></div>
<div class=c><b>Live ledger</b> <span class=mut>(orders, fill checks, settlements, controls)</span><table id=l_ev></table></div>
"""
LOG_JS = r"""
async function loadL(){const d=await api('/api/ledger');if(!d)return;banner(d);const s=d.summary;
 $('l_sum').replaceChildren(kv('Total net',money(s.pnl_net_total)),kv('Today net',money(s.pnl_net_today)),kv('Closed trades',s.trades+' ('+s.wins+' wins)'),
  kv('Fees paid','$'+s.fees_total.toFixed(2)),kv('Unverified vs Kalshi',s.unverified));
 $('l_pm').replaceChildren(...(d.postmortems.length?d.postmortems.slice().reverse().map(x=>h('div',{style:'margin:8px 0;padding-top:8px;border-top:1px solid #30363d'},
  h('b',{},x.ticker+' ('+x.mode+') '+money(x.pnl)),' ',h('span',{class:'tag'},x.tags.join(', ')),h('ul',{},x.lines.map(l=>h('li',{},l))))):[h('span',{class:'mut'},'no losses yet')]));
 $('l_ev').replaceChildren(h('tr',{},h('th',{},'time'),h('th',{},'event'),h('th',{},'details')),...d.events.slice().reverse().slice(0,80).map(e=>{
  const {ts,event,...rest}=e;return h('tr',{},h('td',{},ts.slice(11,19)),h('td',{},event),h('td',{},JSON.stringify(rest).slice(0,260)))}))}
loadL();setInterval(loadL,5000)
"""


def make_handler(client, st, live, fee_mult=1.0, ctx=None):
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
            self.send_header("X-Frame-Options", "DENY")
            self.end_headers()
            self.wfile.write(b)

        def _json(self, code, obj):
            self._send(code, json.dumps(obj, default=str))

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

        def _status_extra(self):
            p = st.pilot
            return dict(live_enabled=bool(p and p.live_enabled), hard_stopped=bool(p and p.hard_stopped))

        def do_GET(self):
            if not self._host_ok():
                return self._send(403, "{}")
            path = urlparse(self.path).path
            if path == "/api/status":
                if not self._authed():
                    return self._send(401, "{}")
                with st.lock:
                    c, p = st.cfg, st.pilot
                    pilot_on = bool(live and p)         # in the pilot the REAL limits are the pilot's, and the rules are fixed
                    return self._json(200, dict(
                        armed=st.armed, halted=st.halted, live=live,
                        mode="pilot (conservative rules, fixed)" if pilot_on else c["mode"],
                        modes=[] if pilot_on else list(MODES),
                        pnl=round(st.pnl, 2), loss_streak=st.loss_streak, max_streak=c["max_losses_in_row"],
                        cap=p.limits["daily_pause_usd"] if pilot_on else c["daily_loss_cap_usd"],
                        size=min(c["size_per_trade_usd"], p.limits["stake_usd"]) if pilot_on else c["size_per_trade_usd"], balance=st.balance,
                        last=st.last, log=list(st.log), **self._status_extra()))
            if path == "/api/trading":
                if not self._authed():
                    return self._send(401, "{}")
                if not (st.pilot and ctx):
                    return self._json(404, dict(error="not a live-pilot process"))
                rd = ctx.readiness()
                okd, why = preflight.demo_fresh(ctx.preflight_path, getattr(client, "fingerprint", None))
                return self._json(200, dict(readiness=rd, pilot=st.pilot.status(), live=live, enable_phrase=ENABLE_PHRASE,
                                            reset_phrases=[RESET_PHRASE_1, RESET_PHRASE_2], demo_detail=f"demo test order: {why}",
                                            **self._status_extra()))
            if path == "/api/ledger":
                if not self._authed():
                    return self._send(401, "{}")
                lg = st.ledger
                return self._json(200, dict(events=lg.events(300) if lg else [], postmortems=lg.postmortems(50) if lg else [],
                                            summary=lg.summary() if lg else {}, live=live, **self._status_extra()))
            pages = {"/": ("board", BOARD_BODY, BOARD_JS), "/index.html": ("board", BOARD_BODY, BOARD_JS),
                     "/trading": ("trading", TRADING_BODY, TRADING_JS), "/log": ("log", LOG_BODY, LOG_JS)}
            if path in pages:
                key, body, js = pages[path]
                return self._send(200, page(st, live, key, body, js), "text/html; charset=utf-8")
            self._send(404, "{}")

        # ---- POST
        def _stop(self):
            """STOP TRADING NOW: engage the kill file, disarm, switch LIVE off, cancel ALL resting live orders."""
            steps = []
            try:
                kill.engage(st.kill_path)
                steps.append("kill switch engaged (no entries until `python kill.py --clear`)")
            except OSError as e:
                steps.append(f"WARNING could not write the kill file: {e}")
            with st.lock:
                st.armed = False
                if st.pilot:
                    st.pilot.disable()
                steps.append("disarmed; LIVE switched off")
            ok = True
            if live and getattr(client, "key", None):
                try:
                    client.cancel_all_orders()
                    steps.append("cancelled ALL resting live orders")
                except Exception as e:
                    ok = False
                    steps.append(f"CANCEL FAILED ({e}): cancel manually at kalshi.com NOW")
            else:
                steps.append("no live account attached: nothing to cancel")
            st.note("STOP TRADING NOW pressed: " + " | ".join(steps))
            if st.ledger:
                st.ledger.log("stop_pressed", steps=steps, cancel_ok=ok)
            return dict(ok=ok, steps=steps)

        def do_POST(self):
            # custom header forces a CORS preflight, which we never grant => no cross-site POSTs
            if not self._host_ok() or self.headers.get("X-Board") != "1":
                return self._send(403, "{}")
            if not self._authed():
                return self._send(401, "{}")
            try:
                n = min(int(self.headers.get("Content-Length", 0)), 4096)
                data = json.loads(self.rfile.read(n) or "{}")
                if not isinstance(data, dict):
                    raise ValueError
            except Exception:
                return self._send(400, "{}")
            path = urlparse(self.path).path
            if path == "/api/stop":
                return self._json(200, self._stop())
            if path == "/api/arm":
                with st.lock:
                    if data.get("armed") and os.path.exists(st.kill_path):
                        return self._json(409, dict(error="kill switch engaged"))
                    if data.get("armed") and st.halted:
                        return self._json(409, dict(error=f"halted: {st.halted}"))
                    if data.get("armed") and live and not (st.pilot and st.pilot.live_enabled):
                        return self._json(409, dict(error="LIVE is not enabled (Trading tab)"))
                    st.armed = bool(data.get("armed"))
                    st.note("ARMED" if st.armed else "DISARMED")
                return self._send(200, "{}")
            if path == "/api/mode":
                if live and st.pilot:
                    return self._json(409, dict(error="the live pilot's rules are fixed; mode cannot be changed"))
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
                return self._json(200, dict(result=res))
            if path.startswith(("/api/live/", "/api/limits/", "/api/hardstop/", "/api/preflight/")):
                if not (st.pilot and ctx):
                    return self._json(404, dict(error="not a live-pilot process"))
                try:
                    return self._json(200, self._pilot_action(path, data))
                except PilotError as e:
                    return self._json(400, dict(error=str(e)))
            self._send(404, "{}")

        def _pilot_action(self, path, data):
            p, lg = st.pilot, st.ledger
            log = lambda ev, **kw: lg and lg.log(ev, **kw)
            if path == "/api/live/enable":
                rd = ctx.readiness(fresh_shard=True)
                failed = [f"{c['name']}: {c['detail']}" if c["detail"] else c["name"] for c in rd["checks"] if not c["ok"]]
                try:
                    p.enable(data.get("phrase", ""), rd["ok"], failed)
                except PilotError as e:
                    log("live_enable_refused", reason=str(e))
                    raise
                ctx.ready_at = time.time()
                st.note("LIVE ENABLED by typed confirmation (real money; still disarmed until you arm)")
                log("live_enabled", limits=p.limits)
                return dict(ok=True)
            if path == "/api/live/disable":
                p.disable()
                st.armed = False
                st.note("LIVE DISABLED")
                log("live_disabled", reason="user")
                return dict(ok=True)
            if path == "/api/limits/lower":
                new = p.lower(str(data.get("name", "")), data.get("value"))
                st.note(f"pilot limit {data['name']} lowered to {new}")
                log("limit_lowered", name=data["name"], value=new)
                return dict(ok=True, value=new)
            if path == "/api/hardstop/reset":
                try:
                    res = p.reset_hard_stop(data.get("phrase", ""))
                except PilotError:
                    log("hardstop_reset_refused")
                    raise
                st.note(f"hard stop reset: {res}")
                log("hardstop_reset", stage=res, baseline=p.baseline)
                return dict(ok=True, stage=res)
            if path == "/api/preflight/shard":
                rd = ctx.readiness(fresh_shard=True)
                log("preflight", ok=rd["ok"], checks=rd["checks"])
                return dict(ok=rd["ok"], checks=rd["checks"])
            raise PilotError("unknown action")
    return H


def serve(client, st, live, host, port, fee_mult=1.0, ctx=None):
    validate_bind(host, os.getenv("BOARD_TOKEN"))
    return ThreadingHTTPServer((host, port), make_handler(client, st, live, fee_mult, ctx))
