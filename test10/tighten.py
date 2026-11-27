"""Tighten pauses in Dex's lines without touching the words: cut the middle of each silence, crossfade, keep words at original speed."""
import numpy as np, soundfile as sf, subprocess, json, sys
def find(x,sr,minlen=10):
    h=int(sr*0.01); e=np.array([np.sqrt(np.mean(x[i:i+h]**2)) for i in range(0,len(x)-h,h)]); db=20*np.log10(e+1e-7); sil=db<db.max()-38; runs=[];i=0
    while i<len(sil):
        if sil[i]:
            j=i
            while j<len(sil) and sil[j]: j+=1
            if j-i>=minlen: runs.append((i*h,j*h))
            i=j
        else: i+=1
    return runs
def tighten(x,sr,targets):
    runs=[r for r in find(x,sr) if r[1]-r[0]>=int(0.1*sr)]
    assert len(runs)==len(targets),(len(runs),len(targets))
    out=[];pos=0;cf=int(sr*0.012); marks=[]
    for (a,b),tg in zip(runs,targets):
        keep=int(tg*sr); L=b-a
        if L<=keep: continue
        cut=L-keep; a2=a+keep//2; seg=x[pos:a2]; out.append(seg); pos=a2+cut
        marks.append((sum(len(s) for s in out)/sr,tg))
    out.append(x[pos:]); y=out[0]
    for s in out[1:]:
        w=np.linspace(0,1,cf); y=np.concatenate([y[:-cf],y[-cf:]*(1-w)+s[:cf]*w,s[cf:]])
    return y
def norm14(inp,outp):
    m=subprocess.run(['ffmpeg','-i',inp,'-af','loudnorm=I=-14:TP=-1.5:print_format=json','-f','null','-'],capture_output=True,text=True).stderr
    g=-14-float(json.loads(m[m.rindex('{'):])['input_i'])
    subprocess.run(['ffmpeg','-y','-v','error','-i',inp,'-af',f'volume={g}dB,alimiter=limit=0.95:level=false,aresample=44100','-ac','2',outp])
    r=subprocess.run(['ffmpeg','-i',outp,'-af','ebur128','-f','null','-'],capture_output=True,text=True).stderr
    I=float([l for l in r.splitlines() if l.strip().startswith('I:')][-1].split()[1])
    subprocess.run(['ffmpeg','-y','-v','error','-i',outp,'-af',f'volume={-14-I}dB,alimiter=limit=0.95:level=false','/tmp/n14.wav']); subprocess.run(['mv','/tmp/n14.wav',outp])
    r=subprocess.run(['ffmpeg','-i',outp,'-af','ebur128','-f','null','-'],capture_output=True,text=True).stderr; return [l.strip() for l in r.splitlines() if l.strip().startswith('I:')][-1]
if __name__=='__main__':
    x,sr=sf.read('/tmp/dexline_s2.wav'); x=x.astype(np.float32)
    ya=tighten(x,sr,[0.12,0.20,0.30,0.08]); sf.write('/tmp/tA.wav',ya,sr)       # after "Chat,", after "ANYTHING!", before the punchline
    x,sr=sf.read('/tmp/dexline_b3.wav'); x=x.astype(np.float32); print('b3 runs',[(round(a/sr,2),round((b-a)/sr,2)) for a,b in find(x,sr) if b-a>=0.1*sr])
