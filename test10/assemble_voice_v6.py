"""v6 voice track (~66 s with the vote card): best-matching take of every line to approved sample 2, tightened, level matched, scheduled with explicit silent beats."""
import numpy as np, soundfile as sf, subprocess, json, sys, glob, os
sys.path.insert(0,'.')
from tighten import find, tighten, norm14
SR=24000
def feats(x,sr):
    x=np.asarray(x,dtype=np.float32)
    if sr!=16000:
        import io
        sf.write('/tmp/_f.wav',x,sr); x=np.frombuffer(subprocess.run(['ffmpeg','-v','error','-i','/tmp/_f.wav','-ac','1','-ar','16000','-f','f32le','-'],capture_output=True).stdout,dtype=np.float32); sr=16000
    f=[]
    for i in range(0,len(x)-800,320):
        fr=x[i:i+800]-x[i:i+800].mean()
        if np.sqrt(np.mean(fr**2))<0.01: continue
        ac=np.correlate(fr,fr,'full')[len(fr)-1:]; k=int(sr/450)+np.argmax(ac[int(sr/450):int(sr/70)])
        if ac[0]>0 and ac[k]/ac[0]>0.5: f.append(sr/k)
    y=x[:len(x)//1024*1024]; S=np.abs(np.fft.rfft(y.reshape(-1,1024)*np.hanning(1024),axis=1)); fr=np.fft.rfftfreq(1024,1/sr); e=S.sum(1); m=e>e.max()*0.1
    cen=((S*fr).sum(1)/S.sum(1))[m].mean(); roll=np.mean([fr[min(len(fr)-1,np.searchsorted(np.cumsum(s)/s.sum(),0.85))] for s in S[m]])
    return np.array([np.median(f) if len(f)>5 else np.nan,cen,roll])
ref,sr0=sf.read('voice_takes/dex_natural_2_tight.wav'); ref=ref.astype(np.float32); RF=feats(ref,sr0)
def rms_active(x):
    h=240; e=np.array([np.sqrt(np.mean(x[i:i+h]**2)) for i in range(0,len(x)-h,h)]); return np.sqrt(np.mean(e[e>e.max()*0.2]**2))
R=rms_active(ref)
LINES=['s09','s10','s11','s12','s13','s14','s16','s20','s21','s22','s23','s24','s27','s28','s29','s30','s33','s35']
choice={}; prep={}
for k in LINES:
    best=None
    for p in sorted(glob.glob(f'/tmp/v6_{k}_*.wav')):
        x,s=sf.read(p); x=x.astype(np.float32)
        ft=feats(x,s); d=abs(ft[1]-RF[1])/250+abs(ft[2]-RF[2])/700+(0 if np.isnan(ft[0]) else abs(ft[0]-RF[0])/120*0.5)
        durpen=len(x)/s*0.04; sc=d+durpen
        if best is None or sc<best[0]: best=(sc,p,x,s,ft)
    sc,p,x,s,ft=best; choice[k]=(os.path.basename(p),round(sc,2))
    runs=[r for r in find(x,s) if r[1]-r[0]>=int(0.12*s)]
    if runs:
        gaps=[(q-a)/s for a,q in runs]; tg=[(0.08 if i==len(runs)-1 else (0.4 if g>0.45 else 0.2)) for i,g in enumerate(gaps)]
        try: x=tighten(x,s,[min(g,t) for g,t in zip(gaps,tg)])
        except AssertionError: pass
    e=np.abs(x); idx=np.where(e>e.max()*0.03)[0]; x=x[max(0,idx[0]-int(0.03*SR)):idx[-1]+int(0.06*SR)]
    x=np.clip(x*(R/max(rms_active(x),1e-6)),-0.98,0.98); prep[k]=x
# schedule: (line, silent seconds BEFORE it). Beats are the visual-only moments (horn, pigeons, tulips...)
SCHED=[('s09',0.7),('s10',0.5),('s11',0.15),('s12',0.15),('s13',0.5),('s14',0.15),('s16',1.6),('s20',2.0),('s21',0.15),('s22',0.5),('s23',0.3),('s24',0.4),('s27',1.6),('s28',0.15),('s29',0.15),('s30',0.2),('s33',1.7),('s35',1.3)]
track=np.zeros(int(90*SR),dtype=np.float32); cues=[]
fade=lambda x:(x*np.minimum(1,np.minimum(np.arange(len(x))/240,(len(x)-np.arange(len(x)))/240))).astype(np.float32)
def put(n,x,at): i=int(at*SR); xx=fade(x); track[i:i+len(xx)]+=xx; cues.append((n,round(at,2),round(at+len(xx)/SR,2)))
put('opening',ref,0.2); t=0.2+len(ref)/SR
for k,gap in SCHED: t+=gap; put(k,prep[k],t); t+=len(prep[k])/SR
END=max(b for _,_,b in cues)
total=END+1.3   # hold the vote card briefly after the question
track=track[:int(total*SR)]; sf.write('voice_track_v6_raw.wav',track,SR)
print('last line ends at',round(END,2),'; video length with vote-card hold',round(total,2))
print(norm14('voice_track_v6_raw.wav','../output/dex_voice_track_v6.wav'))
json.dump(dict(cues=[dict(line=n,start=a,end=b) for n,a,b in cues],total=round(total,2),choice=choice),open('voice_cues_v6.json','w'),indent=1)
for n,a,b in cues: print(f'{a:6.2f} - {b:6.2f}  {n}  {choice.get(n,"")}')
os.makedirs('voice_takes/v6',exist_ok=True)
for k,x in prep.items(): sf.write(f'voice_takes/v6/{k}.wav',x,SR)
