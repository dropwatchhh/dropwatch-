"""Full mix: voice A track + original music (drops out at the freeze frame) + synthesized SFX, ducked, -14 LUFS."""
import numpy as np, soundfile as sf, subprocess, json
SR=44100; meta=json.load(open('full_meta.json')); D=meta['total']; N=int(SR*(D+0.2)); t=np.arange(N)/SR; rng=np.random.default_rng(7)
def lp(x,k): return np.convolve(x,np.ones(k)/k,'same') if k>1 else x
def env(n,a=0.002,d=0.1): x=np.arange(n)/SR; return np.minimum(1,x/a)*np.exp(-x/d)
def saw(f,n): x=np.arange(n)/SR; return 2*((x*f)%1)-1
def put(buf,x,at): i=int(at*SR); x=x[:max(0,len(buf)-i)]; buf[i:i+len(x)]+=x
voc,sr=sf.read('../output/dex_voice_track_v6.wav'); voc=voc.mean(1) if voc.ndim>1 else voc; voc=np.pad(voc,(0,max(0,N-len(voc))))[:N]
# ---- music: 150 BPM punk-pop, ends at the freeze frame (59.1 s)
beat=60/150; mus=np.zeros(N); roots=[82.41,82.41,110.0,123.47]; MEND=59.1
for bar in range(int(MEND/(4*beat))+1):
    r=roots[bar%4]
    for k in range(8):
        at=bar*4*beat+k*beat/2
        if at>=MEND: break
        n=int(SR*0.16); x=sum(saw(f,n) for f in (r*2,r*3,r*4,r*2.003))/4; x=np.tanh(3.2*x)*env(n,0.001,0.07 if k%2 else 0.11); x=x-lp(x,40); put(mus,0.5*x,at)
        nb=int(SR*0.2); b=np.sin(2*np.pi*r*np.arange(nb)/SR)+0.4*saw(r,nb); put(mus,0.45*b*env(nb,0.003,0.12),at)
        h=rng.standard_normal(int(SR*0.05)); h=h-lp(h,6); put(mus,0.12*h*env(len(h),0.001,0.015)*(1.6 if k%2 else 1),at)
    for b4 in range(4):
        at=bar*4*beat+b4*beat
        if at>=MEND: break
        n=int(SR*0.22); x=np.arange(n)/SR
        if b4%2==0: put(mus,0.9*np.sin(2*np.pi*np.cumsum(45+110*np.exp(-x*35))/SR)*env(n,0.001,0.09),at)
        else: put(mus,0.8*(rng.standard_normal(n)*np.exp(-x/0.07)*0.6+np.sin(2*np.pi*190*x)*np.exp(-x/0.05)*0.5),at)
mus*=np.minimum(1,t/0.05)*np.clip((MEND-t)/0.15,0,1)
# ---- SFX
sfx=np.zeros(N)
def tone(f,dur,vol,kind='sine'):
    n=int(SR*dur); x=np.arange(n)/SR
    if kind=='sine': return vol*np.sin(2*np.pi*f*x)*env(n,0.001,dur/3)
def ev(kind,at,dur=0.5,vol=0.5):
    n=int(SR*dur); x=np.arange(n)/SR
    if kind=='ping': y=0.35*np.sin(2*np.pi*1318*x)*env(n,0.001,0.09)+0.3*np.sin(2*np.pi*1760*np.maximum(0,x-0.09))*env(n,0.001,0.12)*(x>0.09)
    elif kind=='swish': y=lp(rng.standard_normal(n),30)*np.sin(np.pi*x/dur)*0.5
    elif kind=='ding': y=0.4*np.sin(2*np.pi*880*x)*env(n,0.001,0.15)+0.4*np.sin(2*np.pi*1175*np.maximum(0,x-0.12))*env(n,0.001,0.2)*(x>0.12)
    elif kind=='horn': y=lp((np.sign(np.sin(2*np.pi*330*x))+np.sign(np.sin(2*np.pi*415*x)))*0.3,6)*np.minimum(1,x/0.01)*np.minimum(1,(dur-x)/0.03)
    elif kind=='clang': y=sum(np.sin(2*np.pi*f*x)*np.exp(-x*d) for f,d in ((800,9),(1230,12),(1700,16),(2310,22)))*0.35
    elif kind=='thud': y=np.sin(2*np.pi*(40+60*np.exp(-x*30))*x)*np.exp(-x*12)+lp(rng.standard_normal(n),30)*np.exp(-x*20)*0.8
    elif kind=='wings': e=(np.sin(2*np.pi*9*x)>0.2)*np.minimum(1,x/0.05)*np.minimum(1,(dur-x)/0.2); y=(lp(rng.standard_normal(n),5)-lp(rng.standard_normal(n),40))*e*1.4
    elif kind=='squeak': f=1700+900*np.minimum(1,x/dur); y=np.sin(2*np.pi*np.cumsum(f)/SR)*np.sin(np.pi*np.minimum(1,x/dur))*0.5
    elif kind=='whoosh': y=(lp(rng.standard_normal(n),12)-lp(rng.standard_normal(n),80))*np.sin(np.pi*np.minimum(1,x/dur))*1.2
    elif kind=='scratch': f=1800*np.exp(-x*5); y=np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-x*4)*0.4+lp(rng.standard_normal(n),3)*np.exp(-x*5)*0.5
    elif kind=='rattle': e=(np.sin(2*np.pi*14*x)>0.3)*np.exp(-x*2.2); y=(lp(rng.standard_normal(n),3)-lp(rng.standard_normal(n),20))*e*1.3
    elif kind=='riser': f=200+1400*(x/dur)**2; y=np.sin(2*np.pi*np.cumsum(f)/SR)*(x/dur)*0.35+lp(rng.standard_normal(n),8)*(x/dur)*0.25
    elif kind=='scrape': y=(lp(rng.standard_normal(n),4)-lp(rng.standard_normal(n),30))*(0.6+0.4*np.sin(2*np.pi*7*x))
    put(sfx,y*vol,at)
for k in ('ping',): ev('ping',3.68,0.35,0.9)
ev('swish',3.58,0.35,0.35)
# engine: low rumble that follows the van: loud as it passes (6.6-8.3), then from the street shots rising with speed
eng=np.sin(2*np.pi*np.cumsum(38+4*np.sin(2*np.pi*3*t))/SR)+0.6*saw(19,N); eng=lp(eng,12)*(0.55+0.45*np.sign(np.sin(2*np.pi*11*t)))
lvl=0.55*np.exp(-((t-7.4)/1.4)**2)+0.12*np.clip((t-11.3)/2,0,1)*np.clip((57.3-t)/0.3,0,1)*(0.5+0.5*np.clip((t-30)/25,0,1))
sfx+=0.5*eng*lvl*np.minimum(1,t/0.2)
for at in (14.0,): ev('ding',at,0.7,0.8)
ev('clang',22.9,0.6,0.7)
for at in (28.75,29.2,29.65): ev('horn',at,0.35,0.5)
ev('wings',30.6,1.7,0.8); ev('thud',37.95,0.4,0.9)
for at in (44.5,45.0): ev('horn',at,0.4,0.5)
ev('scrape',38.3,7.6,0.18); ev('riser',50.0,2.5,0.7); ev('squeak',54.6,0.35,0.6)
ev('thud',57.3,0.5,1.0); ev('rattle',57.3,1.4,0.9); ev('whoosh',57.35,0.9,0.7)
ev('scratch',59.05,0.8,0.8)
for k in range(9): ev('squeak',10.3+k*0.0+0.0,0.0,0.0) if False else None
# gig chitters at the end of the cab shots
for k in range(5): ev('squeak',10.0+k*0.14,0.09,0.25)
v_env=np.convolve(np.abs(voc),np.ones(int(SR*0.12))/int(SR*0.12),'same'); v_env=np.clip(v_env/(max(v_env.max(),1e-6)*0.25),0,1); duck=1-0.62*v_env
mix=voc/max(np.abs(voc).max(),1e-6)*0.6+0.22*mus*duck+0.5*sfx*(0.6+0.4*duck)
sf.write('mix_full_raw.wav',np.stack([mix,mix],1).astype(np.float32),SR)
for _ in range(2):
    r=subprocess.run(['ffmpeg','-i','mix_full_raw.wav','-af','loudnorm=I=-14:TP=-1.5:print_format=json','-f','null','-'],capture_output=True,text=True).stderr
    g=-14-float(json.loads(r[r.rindex('{'):])['input_i']); subprocess.run(['ffmpeg','-y','-v','error','-i','mix_full_raw.wav','-af',f'volume={g}dB,alimiter=limit=0.9:level=false','mix_full_14.wav']); break
r=subprocess.run(['ffmpeg','-i','mix_full_14.wav','-af','ebur128=peak=true','-f','null','-'],capture_output=True,text=True).stderr
I=float([l for l in r.splitlines() if l.strip().startswith('I:')][-1].split()[1]); subprocess.run(['ffmpeg','-y','-v','error','-i','mix_full_14.wav','-af',f'volume={-14-I}dB,alimiter=limit=0.9:level=false','audio_full_final.wav'])
r=subprocess.run(['ffmpeg','-i','audio_full_final.wav','-af','ebur128=peak=true','-f','null','-'],capture_output=True,text=True).stderr
print([l.strip() for l in r.splitlines() if l.strip().startswith(('I:','Peak:'))][-2:])
