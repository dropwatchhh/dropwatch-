"""Builds the 10 s test timeline: Dex audio edit, lip-sync visemes, frames.json for the renderer."""
import numpy as np, subprocess, json, soundfile as sf
FPS=24; SR=24000
sr0=24000; DUR=12.0
V,sV=sf.read('voice_takes/dex_natural_2_tight.wav'); V=V.astype(np.float32); assert sV==sr0
fade=lambda x:(x*np.minimum(1,np.minimum(np.arange(len(x))/240,(len(x)-np.arange(len(x)))/240))).astype(np.float32)
dex=np.zeros(int(DUR*sr0),dtype=np.float32); x=fade(V); i=int(0.2*sr0); dex[i:i+len(x)]+=x
sf.write('dex_voice_raw.wav',dex,sr0)
# lip-sync: loudness + brightness per frame -> mouth shape
n=int(DUR*FPS); hop=sr0//FPS; win=int(sr0*0.05)
rms=[];cen=[]
for i in range(n):
    c=int((i+0.5)*hop); x=dex[max(0,c-win):c+win]
    if len(x)<64: rms.append(0);cen.append(0);continue
    rms.append(np.sqrt(np.mean(x**2)))
    S=np.abs(np.fft.rfft(x*np.hanning(len(x)))); fr=np.fft.rfftfreq(len(x),1/sr0); cen.append((S*fr).sum()/(S.sum()+1e-9))
rms=np.array(rms); dbv=20*np.log10(rms+1e-6); hi=np.percentile(dbv[rms>1e-3],97); l=np.clip((dbv-(hi-28))/28,0,1); l[rms<1e-3]=0
lip=[]
for i in range(n):
    v=l[i]
    if v<0.22: m='mouth_smile'
    elif v<0.45: m='mouth_E' if cen[i]>2600 else 'mouth_O'
    elif v<0.88: m='mouth_A'
    else: m='mouth_shout'
    lip.append(m)
for i in range(1,n-1):          # no one-frame flicker
    if lip[i]!=lip[i-1] and lip[i]!=lip[i+1] and lip[i-1]==lip[i+1]: lip[i]=lip[i-1]
amp=np.convolve(l,np.ones(3)/3,'same'); emph=np.clip((np.convolve(l,np.ones(5)/5,'same')-0.55)/0.25,0,1)
shots=[('S1',0.0,2.2),('S8',2.2,3.6),('S2',3.6,5.1),('S3',5.1,6.6),('S4',6.6,8.3),('S7',8.3,9.7),('S5',9.7,11.3),('S6',11.3,12.0)]
blink={int(t*FPS)+k for t in (1.1,2.9,4.6,6.2,7.4,8.9,10.2) for k in range(3)}
lot={"job":{"scene":"lot","vanX":0}}; cab={"job":{"scene":"cab"}}
fr=[]
for i in range(n):
    g=i/FPS
    s=[x for x in shots if x[1]<=g<x[2]][0]
    fr.append(dict(n=i,shot=s[0],t=round(g-s[1],4),g=round(g,4),dur=round(s[2]-s[1],4),lip=lip[i],blink=i in blink,amp=round(float(amp[i]),3),emph=round(float(emph[i]),3)))
json.dump(dict(w=1080,h=1920,shots={k:(cab if k=='S5' else lot) for k,_,_ in shots},frames=fr,shotlist=shots),open('frames.json','w'))
print(len(fr),'frames; visemes',{m:lip.count(m) for m in set(lip)})
