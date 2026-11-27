"""Assemble the v5 voice track: approved opening + per-shot lines (voice A), tightened, level-matched, placed at shot times, -14 LUFS."""
import numpy as np, soundfile as sf, subprocess, json, sys
sys.path.insert(0,'.')
from tighten import find, tighten, norm14
SR=24000; TOTAL=66.0
SLOTS={ 's09':(11.3,12.3),'s10':(12.3,13.8),'s11':(13.8,15.4),'s12':(15.4,17.0),'s13':(17.0,20.6),'s14':(20.6,22.4),'s15':(22.4,23.8),'s16':(23.8,28.2),'s17':(28.2,29.4),'s19':(30.6,31.8),'s20':(31.8,33.8),'s21':(33.8,35.0),'s22':(35.0,36.4),'s23':(36.4,40.4),'s24':(40.4,42.4),'s25':(42.4,44.2),'s27':(45.2,46.6),'s28':(46.6,48.6),'s29':(48.6,50.6),'s30':(50.6,52.0),'s33':(54.0,55.8),'s35':(57.0,66.0)}
def rms_active(x):
    h=240; e=np.array([np.sqrt(np.mean(x[i:i+h]**2)) for i in range(0,len(x)-h,h)]); return np.sqrt(np.mean(e[e>e.max()*0.2]**2))
ref,sr=sf.read('voice_takes/dex_natural_2_tight.wav'); ref=ref.astype(np.float32); assert sr==SR; R=rms_active(ref)
track=np.zeros(int(80*SR),dtype=np.float32); cues=[]; shift=0.0; GAP=0.15; plan_shift={}
fade=lambda x:(x*np.minimum(1,np.minimum(np.arange(len(x))/240,(len(x)-np.arange(len(x)))/240))).astype(np.float32)
def put(name,x,at):
    i=int(at*SR); x=fade(x); track[i:i+len(x)]+=x[:len(track)-i]; cues.append((name,round(at,2),round(at+len(x)/SR,2)))
put('opening (approved sample 2)',ref*1.0,0.2); prev_end=0.2+len(ref)/SR
for k,(a,b) in SLOTS.items():
    x,s=sf.read(f'/tmp/v5_{k}.wav'); x=x.astype(np.float32); assert s==SR
    runs=[r for r in find(x,s) if r[1]-r[0]>=int(0.12*s)]
    if runs:
        gaps=[(q-p)/s for p,q in runs]; tg=[(0.08 if i==len(runs)-1 else (0.4 if (g>0.45) else 0.2)) for i,g in enumerate(gaps)]
        try: x=tighten(x,s,[min(g,t) for g,t in zip(gaps,tg)])
        except AssertionError: pass
    # trim leading/trailing silence
    e=np.abs(x); idx=np.where(e>e.max()*0.03)[0]; x=x[max(0,idx[0]-int(0.03*SR)):idx[-1]+int(0.06*SR)]
    x=x*(R/max(rms_active(x),1e-6))*1.0; x=np.clip(x,-0.98,0.98)
    dur=len(x)/SR; planned=a+0.08 if k!='s35' else 57.3
    start=max(planned+shift, prev_end+GAP); shift=start-planned; put(k,x,start); prev_end=start+dur; plan_shift[k]=round(shift,2)
end=max(b for _,_,b in cues)+0.3; track=track[:int((end+0.5)*SR)]
sf.write('voice_track_raw.wav',track,SR); print('voice ends at',round(end,2),'s; shift of the vote line vs plan',plan_shift['s35'],'s')
print(norm14('voice_track_raw.wav','../output/dex_voice_track_v5.wav'))
json.dump(dict(cues=[dict(line=n,start=a,end=b) for n,a,b in cues],shift_vs_plan=plan_shift),open('voice_cues_v5.json','w'),indent=1)
for n,a,b in cues: print(f'{a:6.2f} - {b:6.2f}  {n}')
