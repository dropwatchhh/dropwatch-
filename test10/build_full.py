"""Full Episode 1 (v5, one voice): builds per-frame render jobs for shots after the approved opening, from the voice cue times."""
import json, numpy as np, soundfile as sf
FPS=12; SR=24000
cues={c['line']:(c['start'],c['end']) for c in json.load(open('voice_cues_v6.json'))['cues']}
TOTAL=json.load(open('voice_cues_v6.json'))['total']
T6={k:sf.read(f'voice_takes/v6/{k}.wav')[0].astype(np.float32) for k in cues if k!='opening'}
def viseme(x,fps=FPS):
    h=SR//fps; out=[]
    for i in range(int(len(x)/h)+1):
        c=int((i+0.5)*h); w=x[max(0,c-600):c+600]
        if len(w)<64: out.append('mouth_smile'); continue
        r=np.sqrt(np.mean(w**2)); S=np.abs(np.fft.rfft(w*np.hanning(len(w)))); fr=np.fft.rfftfreq(len(w),1/SR); cen=(S*fr).sum()/(S.sum()+1e-9)
        l=np.clip((20*np.log10(r+1e-6)+48)/32,0,1)
        out.append('mouth_smile' if l<0.22 else ('mouth_E' if cen>2600 else 'mouth_O') if l<0.45 else 'mouth_A' if l<0.85 else 'mouth_shout')
    return out
VIS={k:viseme(v) for k,v in T6.items()}
def mouth(T,line,default='mouth_smile'):
    a,b=cues[line]
    if a<=T<b+0.05:
        v=VIS[line]; i=int((T-(a-0.03))*FPS); return v[min(max(i,0),len(v)-1)]
    return default
LS={"scene":"lab_street"}; CAB={"scene":"cab"}; CALL={"scene":"call"}; LOT={"scene":"lot","vanX":0.9}
T0=35.25                                   # chase starts here (grab at tt=2.75 -> 38.0, matching "Got it!")
vzf=lambda tt: -(1.5*tt+0.00424*tt**3) if tt>=0 else -1.5*tt
def street(**kw): return {**LS,"standZ":-100}
def spec_at(T):
    tt=T-T0
    # ---- lot shots
    if T<12.30:   # 9: profile, van leaves, Dex starts to run
        u=T-11.30; return LOT,{"anim":"gait","mode":"jog","t":u,"dir":[1,0],"p0":[-1.5,2.0],"vanX":5.0+3.0*u,"keepVan":True,"mouth":mouth(T,'s09'),"cam":{"rel":True,"pos":[0.2,0.6,8.0],"look":[1.2,0.8,0.0],"fov":44}}
    if T<14.50:   # 10: sprint, low tracking
        u=T-11.30; return LOT,{"anim":"gait","mode":"jog","t":u,"dir":[1,0],"p0":[-1.5,2.0],"vanX":5.0+3.0*u,"keepVan":True,"mouth":mouth(T,'s10','mouth_shout'),"cam":{"rel":True,"pos":[0.2,0.5,7.2],"look":[1.2,0.8,0.0],"fov":44}}
    if T<16.30:   # 11: cab, Gig mashes the GPS
        return CAB,{"anim":"cab","what":"drive","t":T-14.5,"cam":{"rel":True,"pos":[-0.55,0.45,-0.75],"look":[0,-0.05,0],"fov":44}}
    if T<17.45:   # 12: high angle, Dex tiny
        u=T-11.30; return LOT,{"anim":"gait","mode":"jog","t":u,"dir":[1,0],"p0":[-1.5,2.0],"vanX":5.0+3.0*u,"keepVan":True,"mouth":mouth(T,'s12','mouth_shout'),"cam":{"rel":True,"pos":[-1.5,6.5,6.0],"look":[3.0,0,0],"fov":46}}
    if T<21.50:   # 13: Lena call card
        return CALL,{"anim":"lena","t":T-17.45,"dur":4.0,"cam":{"pos":[0,1.3,2.0-0.3*(T-17.45)/4.05],"look":[0,1.1,0],"fov":30}}
    if T<24.30:   # 14: boot flies off
        u=T-21.50; k=min(1,u/2.8); return LOT,{"anim":"boot2","k":k,"t":u,"dur":2.0,"dir":[1,0],"p0":[-3.0,2.0],"vanX":9.0+2.5*u,"keepVan":True,"mouth":mouth(T,'s14','mouth_shout'),"cam":{"rel":True,"pos":[0.2,0.6,7.4],"look":[1.1,0.8,0.0],"fov":44}}
    # ---- Maple Street shots
    if T<25.80:   # 15: van turns onto Maple Street, wide front
        return street(),{"anim":"van","vanZ":vzf(tt),"vanG":T,"cam":{"pos":[1.0,1.2,-14.0],"look":[0,1.0,-6.0],"fov":44}}
    if T<29.30:   # 16: Nana Dot watching (call card)
        return street(),{"anim":"nana","what":"watch","t":T-25.8,"g":T-25.8,"cam":{"rel":True,"pos":[1.1,0.95,3.0],"look":[0,0.05,0],"fov":34}}
    if T<30.60:   # 17: high angle down the hill, van speeds up
        return street(),{"anim":"van","vanZ":vzf(tt),"vanG":T,"cam":{"pos":[3.0,8.0,6.0],"look":[0,0,-14.0],"fov":42}}
    if T<31.90:   # 18: Gig on the horn
        return CAB,{"anim":"cab","what":"horn","t":T-30.6,"cam":{"rel":True,"pos":[-0.55,0.45,-0.75],"look":[0,-0.05,0],"fov":44}}
    if T<33.80:   # 19: pigeons scatter
        u=T-31.9; return street(),{"anim":"van","vanZ":-6+vzf(tt)*0+(-1.0*u)+0,"vanG":T,"pigeonT":u*0.9,"cam":{"pos":[0.4,1.3,-26.0],"look":[0,1.3,-15.0],"fov":50}}
    if T<T0:      # 20: Dex jogs behind the van with his phone
        u=T-33.8; return street(),{"anim":"gait","mode":"jog","phone":True,"t":u,"dir":[0,-1],"p0":[0,0.12+2.7*(T0-33.8)],"vanZ":vzf(tt),"vanG":T,"keepVan":True,"mouth":mouth(T,'s20'),"cam":{"rel":True,"pos":[4.2,0.9,0.4],"look":[0,0.1,0],"fov":34}}
    # ---- chase: jog, plant, jump, grab the bumper, drag (22-23), then hang/reach (27-28)
    if tt<7.55:
        m='mouth_shout'
        if cues['s21'][0]<=T<cues['s21'][1]: m=mouth(T,'s21','mouth_shout')
        elif cues['s22'][0]<=T<cues['s22'][1]+0.1: m=mouth(T,'s22','mouth_shout')
        elif cues['s23'][0]<=T: m='mouth_closed_worried'
        if tt<2.4: cam={"rel":True,"pos":[7.5-1.0*min(1,max(0,(tt-1.4)/0.8)),1.1,2.6-2.8*min(1,max(0,(tt-1.4)/0.8))],"look":[0,0.4,-0.9],"fov":44}
        elif T<40.6: cam={"rel":True,"pos":[7.5-1.0+3.8*min(1,max(0,(tt-2.4)/0.5)),1.0,-0.2],"look":[0,0.4,-0.9],"fov":44}
        else: cam={"rel":True,"pos":[5.5,0.6,-1.0],"look":[0,0.3,0],"fov":44}
        return street(),{"anim":"chase","tt":tt,"vanZ":vzf(tt),"vanZ0":0,"vanG":T,"mouth":m,"cam":cam}
    if T<44.90:   # 24: Nana braces at the stand
        return street(),{"anim":"nana","what":"brace","t":min(1,(T-42.8)/0.6),"g":T-42.8,"cam":{"rel":True,"pos":[1.1,0.95,3.0],"look":[0,0.05,0],"fov":34}}
    if T<46.50:   # 25: Gig leans on the horn twice
        return CAB,{"anim":"cab","what":"horn","t":T-44.9,"cam":{"rel":True,"pos":[-0.55,0.45,-0.75],"look":[0,-0.05,0],"fov":44}}
    if T<48.00:   # 27: hanging on
        return street(),{"anim":"hang","g":T,"vanZ":vzf(tt),"vanG":T,"mouth":mouth(T,'s27','mouth_closed_worried'),"cam":{"rel":True,"pos":[4.4,1.0,0.8],"look":[0,0.6,-0.6],"fov":40}}
    if T<50.50:   # 28: reaches for the guitar neck
        return street(),{"anim":"reach","t":min(1,(T-48.0)/2.0),"g":T,"vanZ":vzf(tt),"vanG":T,"mouth":mouth(T,'s28','mouth_closed_worried'),"cam":{"rel":True,"pos":[3.0,1.1,1.0],"look":[0,0.5,-0.7],"fov":42}}
    if T<52.60:   # 29: split screen (two crops of one wide frame, composed later)
        return street(),{"anim":"reach","t":1.0,"g":T,"vanZ":vzf(tt),"vanG":T,"mouth":'mouth_closed_worried',"cam":{"rel":True,"pos":[3.4,1.0,1.2],"look":[0,0.5,-0.7],"fov":42}}
    if T<54.30:   # 30: Lena leans in
        return CALL,{"anim":"lena","t":2.4+(T-52.6),"dur":4.0,"cam":{"pos":[0,1.3,1.75],"look":[0,1.1,0],"fov":30}}
    if T<55.90:   # 31: Gig covers his eyes
        return CAB,{"anim":"cab","what":"cover","t":(T-54.3)/1.6,"cam":{"rel":True,"pos":[-0.55,0.45,-0.75],"look":[0,-0.05,0],"fov":44}}
    if T<59.10:   # 33: extreme close-up grin
        return street(),{"anim":"face","t":T-55.9,"mouth":mouth(T,'s33','mouth_grin_open'),"eyes":"eyes_wide","brows":"brows_smirk","cam":{"rel":True,"pos":[0.4,0.1,1.25],"look":[0,0,0],"fov":30}}
    u=T-59.1    # 34: tulips fly (then the freeze frame for the vote card)
    return street(),{"anim":"van","vanZ":-90.0-1.2*u+0,"vanG":T,"tulipT":u*0.9,"cam":{"pos":[6.0,1.3,-98.0],"look":[0,0.9,-98.0],"fov":44}}
items=[]; G0=136; G1=int(59.1*FPS)
for g in range(G0,G1+1):
    T=g/FPS; sc,sp=spec_at(T); items.append({"name":f"f{g:05d}","scene":sc,"spec":sp})
json.dump({"w":540,"h":960,"items":items},open('/tmp/full_items.json','w'))
json.dump({"total":TOTAL,"cues":cues,"T0":T0,"first":G0,"last":G1},open('full_meta.json','w'))
print(len(items),'lab frames; movie length',TOTAL)
