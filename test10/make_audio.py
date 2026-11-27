"""Original music + SFX synthesized in code, mixed with Dex's designed voice, normalized to -14 LUFS."""
import numpy as np, soundfile as sf, subprocess, json
SR=44100; D=10.0; N=int(SR*D); t=np.arange(N)/SR; rng=np.random.default_rng(7)
def env(n,a=0.002,d=0.1):
    x=np.arange(n)/SR; return np.minimum(1,x/a)*np.exp(-x/d)
def put(buf,x,at): i=int(at*SR); x=x[:max(0,len(buf)-i)]; buf[i:i+len(x)]+=x
def saw(f,n): x=np.arange(n)/SR; return 2*((x*f)%1)-1
def lp(x,k): return np.convolve(x,np.ones(k)/k,'same') if k>1 else x
# ---- music: 150 BPM punk-pop (kick 1&3, snare 2&4, 8th hats, palm-muted power chords, bass)
BPM=150; beat=60/BPM; mus=np.zeros(N)
roots=[82.41,82.41,110.0,123.47]   # E E A B
for bar in range(7):
    r=roots[bar%4]
    for k in range(8):               # eighth notes
        at=bar*4*beat+k*beat/2
        if at>=D: break
        n=int(SR*0.16); x=sum(saw(f,n) for f in (r*2,r*3,r*4,r*2.003))/4
        x=np.tanh(3.2*x)*env(n,0.001,0.07 if k%2 else 0.11); x=x-lp(x,40)  # tighten lows
        put(mus,0.5*x,at)
        nb=int(SR*0.2); b=np.sin(2*np.pi*r*np.arange(nb)/SR)+0.4*saw(r,nb); put(mus,0.45*b*env(nb,0.003,0.12),at)
        h=rng.standard_normal(int(SR*0.05)); h=h-lp(h,6); put(mus,0.12*h*env(len(h),0.001,0.015)*(1.6 if k%2 else 1),at)
    for b4 in range(4):
        at=bar*4*beat+b4*beat
        if at>=D: break
        if b4%2==0:
            n=int(SR*0.22); x=np.arange(n)/SR; f=45+110*np.exp(-x*35); put(mus,0.9*np.sin(2*np.pi*np.cumsum(f)/SR)*env(n,0.001,0.09),at)
        else:
            n=int(SR*0.2); x=np.arange(n)/SR; s=rng.standard_normal(n)*np.exp(-x/0.07)*0.6+np.sin(2*np.pi*190*x)*np.exp(-x/0.05)*0.5; put(mus,0.8*s,at)
mus*=np.minimum(1,t/0.05)*np.minimum(1,(D-t)/0.4)
# ---- SFX
sfx=np.zeros(N)
def ping(at,f1=1318,f2=1760):
    n=int(SR*0.35); x=np.arange(n)/SR; put(sfx,0.35*np.sin(2*np.pi*f1*x)*env(n,0.001,0.09),at); put(sfx,0.3*np.sin(2*np.pi*f2*x)*env(n,0.001,0.12),at+0.09)
ping(2.88)
n=int(SR*0.35); sw=rng.standard_normal(n); sw=sw-lp(sw,30); put(sfx,0.18*sw*np.sin(np.pi*np.arange(n)/n),2.78)   # banner swish
# engine putter: rough low pulses, louder as the van passes the camera (6.6-8.2 s)
eng=np.sin(2*np.pi*np.cumsum(38+4*np.sin(2*np.pi*3*t))/SR)+0.6*saw(19,N)
eng=lp(eng,12)*(0.55+0.45*np.sign(np.sin(2*np.pi*11*t)))*0.5
lvl=0.25+0.75*np.exp(-((t-7.4)/1.4)**2); sfx+=0.55*eng*lvl*np.minimum(1,t/0.2)
# gig chitter 8.3-9.3: quick rising chirps
for k in range(7):
    at=8.35+k*0.14; n=int(SR*0.09); x=np.arange(n)/SR; f=2600+1500*x/0.09*(1 if k%2 else -1)+300*k
    put(sfx,0.22*np.sin(2*np.pi*np.cumsum(f)/SR)*np.sin(np.pi*x/0.09),at)
put(sfx,0.0*sfx[:10],0)
# ---- voice: designed Dex voice (already edited to timeline), light cleanup via ffmpeg
subprocess.run(['ffmpeg','-y','-v','error','-i','dex_voice_raw.wav','-af','highpass=f=80,acompressor=threshold=-22dB:ratio=3:attack=5:release=80,aresample=44100','-ac','1','dex_voice_clean.wav'])
voc,_=sf.read('dex_voice_clean.wav'); voc=np.pad(voc,(0,max(0,N-len(voc))))[:N]
v_env=np.convolve(np.abs(voc),np.ones(int(SR*0.12))/int(SR*0.12),'same'); v_env=np.clip(v_env/(v_env.max()*0.25),0,1)
duck=1-0.62*v_env                                         # music/SFX dip ~8 dB under speech
vox_peak=np.abs(voc).max()
mix=voc/vox_peak*0.6+0.22*mus*duck+0.5*sfx*(0.6+0.4*duck)
sf.write('mix_raw.wav',np.stack([mix,mix],1).astype(np.float32),SR)
for name,x in (('music',mus),('sfx',sfx)): sf.write(f'stem_{name}.wav',x.astype(np.float32),SR)
m=subprocess.run(['ffmpeg','-i','mix_raw.wav','-af','loudnorm=I=-14:TP=-1.5:print_format=json','-f','null','-'],capture_output=True,text=True).stderr
g=-14-float(json.loads(m[m.rindex('{'):])['input_i'])
subprocess.run(['ffmpeg','-y','-v','error','-i','mix_raw.wav','-af',f'volume={g}dB,alimiter=limit=0.9:level=false','audio_mix.wav'])
r=subprocess.run(['ffmpeg','-i','audio_mix.wav','-af','ebur128=peak=true','-f','null','-'],capture_output=True,text=True).stderr
I=float([l for l in r.splitlines() if l.strip().startswith('I:')][-1].split()[1]); print('first pass',I)
subprocess.run(['ffmpeg','-y','-v','error','-i','audio_mix.wav','-af',f'volume={-14-I}dB,alimiter=limit=0.9:level=false','audio_final.wav'])
r=subprocess.run(['ffmpeg','-i','audio_final.wav','-af','ebur128=peak=true','-f','null','-'],capture_output=True,text=True).stderr
print([l.strip() for l in r.splitlines() if l.strip().startswith(('I:','Peak:'))][-2:])
