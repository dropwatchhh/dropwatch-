"""Builds the 10 s test timeline: Dex audio edit, lip-sync visemes, frames.json for the renderer."""
import numpy as np, subprocess, json, soundfile as sf
FPS=24; SR=24000
src,sr0=sf.read('/tmp/dexline_s2.wav'); src=src.astype(np.float32)
cut=lambda a,b: src[int(a*sr0):int(b*sr0)]
fade=lambda x:(x*np.minimum(1,np.minimum(np.arange(len(x))/240,(len(x)-np.arange(len(x)))/240))).astype(np.float32)
segs=[(0.10,cut(0.0,2.70)),(4.30,cut(3.28,5.62)),(6.70,cut(5.88,7.28))]
dex=np.zeros(int(10.0*sr0),dtype=np.float32)
for t0,x in segs: x=fade(x); i=int(t0*sr0); dex[i:i+len(x)]+=x
sf.write('dex_voice_raw.wav',dex,sr0)
# lip-sync: loudness + brightness per frame -> mouth shape
n=int(10*FPS); hop=sr0//FPS; win=int(sr0*0.05)
rms=[];cen=[]
for i in range(n):
    c=int((i+0.5)*hop); x=dex[max(0,c-win):c+win]
    if len(x)<64: rms.append(0);cen.append(0);continue
    rms.append(np.sqrt(np.mean(x**2)))
    S=np.abs(np.fft.rfft(x*np.hanning(len(x)))); fr=np.fft.rfftfreq(len(x),1/sr0); cen.append((S*fr).sum()/(S.sum()+1e-9))
rms=np.array(rms); l=np.clip((20*np.log10(rms+1e-6)+50)/35,0,1); l[rms<1e-3]=0
lip=[]
for i in range(n):
    v=l[i]
    if v<0.18: m='mouth_smile'
    elif v<0.4: m='mouth_E' if cen[i]>2600 else 'mouth_O'
    elif v<0.78: m='mouth_A'
    else: m='mouth_shout'
    lip.append(m)
for i in range(1,n-1):          # no one-frame flicker
    if lip[i]!=lip[i-1] and lip[i]!=lip[i+1] and lip[i-1]==lip[i+1]: lip[i]=lip[i-1]
amp=np.convolve(l,np.ones(3)/3,'same'); emph=np.clip((np.convolve(l,np.ones(5)/5,'same')-0.55)/0.25,0,1)
shots=[('S1',0.0,2.8),('S2',2.8,4.3),('S3',4.3,6.6),('S4',6.6,8.2),('S5',8.2,9.3),('S6',9.3,10.0)]
blink={int(t*FPS)+k for t in (0.9,3.6,5.6,7.4,8.6) for k in range(3)}
lot={"job":{"scene":"lot","vanX":0}}; cab={"job":{"scene":"cab"}}
fr=[]
for i in range(n):
    g=i/FPS
    s=[x for x in shots if x[1]<=g<x[2]][0]
    fr.append(dict(n=i,shot=s[0],t=round(g-s[1],4),g=round(g,4),dur=round(s[2]-s[1],4),lip=lip[i],blink=i in blink,amp=round(float(amp[i]),3),emph=round(float(emph[i]),3)))
json.dump(dict(w=1080,h=1920,shots={k:(cab if k=='S5' else lot) for k,_,_ in shots},frames=fr,shotlist=shots),open('frames.json','w'))
print(len(fr),'frames; visemes',{m:lip.count(m) for m in set(lip)})
