"""Episode 1 revision 2: new shot schedule (new angle about every 2 s), IK grips, crash + dodge, split screen, reframed street shots."""
import json, numpy as np, soundfile as sf
FPS=12; SR=24000
meta6=json.load(open('voice_cues_v6.json')); cues={c['line']:(c['start'],c['end']) for c in meta6['cues']}; TOTAL=meta6['total']
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
def mouth_any(T,lines,default='mouth_smile'):
    for l in lines:
        a,b=cues[l]
        if a<=T<b+0.05: return mouth(T,l,default)
    return default
# ---- world timeline
T_M=24.3; T0=35.25; T_GR=38.0; T_IMP=57.3; ACC=0.30
vzf=lambda tt: -(1.5*tt+0.00424*tt**3)
OFF_GR=-16.4+vzf(T_GR-T0); V_GR=1.5+3*0.00424*(T_GR-T0)**2
def off(T):
    if T<T0: return -1.5*(T-T_M)
    if T<T_GR: return -16.4+vzf(T-T0)
    u=T-T_GR
    if T<T_IMP: return OFF_GR-(V_GR*u+0.5*ACC*u*u)
    tau=min(1,(T-T_IMP)/0.5); return OFF_IMP-0.22*(1-(1-tau)**2)
OFF_IMP=OFF_GR-(V_GR*(T_IMP-T_GR)+0.5*ACC*(T_IMP-T_GR)**2)
VZ_IMP=-6+OFF_IMP; SZ=round(VZ_IMP-2.9-0.47,2)
print('stand z',SZ,'impact speed',round(V_GR+ACC*(T_IMP-T_GR),2),'m/s')
vz=lambda T:-6+off(T)
LS={"scene":"lab_street","standZ":SZ}; CAB={"scene":"cab"}; CALL={"scene":"call"}; LOT={"scene":"lot","vanX":0.9}
def cab(T,t0,what,cam=None): return CAB,{"anim":"cab","what":what,"t":T-t0,"cam":cam or {"rel":True,"pos":[-0.55,0.45,-0.75],"look":[0,-0.05,0],"fov":44}}
def lena(T,t0,off0=0.0,dur=4.0): return CALL,{"anim":"lena","t":T-t0+off0,"dur":dur,"cam":{"pos":[0,1.3,2.0-0.3*min(1,(T-t0)/2.0)],"look":[0,1.1,0],"fov":30}}
def street_cam_act(T,m,cam,**kw):
    return LS,{"anim":"act","m":m,"vanZ":off(T),"vanG":T,"cam":cam,**kw}
def shot(T):
    # ---------- lot
    if T<13.3: u=T-11.3; return LOT,{"anim":"gait","mode":"jog","t":u,"dir":[1,0],"p0":[-1.5,2.0],"vanX":5.0+3.0*u,"keepVan":True,"mouth":mouth_any(T,['s09','s10'],'mouth_shout'),"eyes":"eyes_wide","cam":{"rel":True,"pos":[2.0,1.0,3.3],"look":[0,0.9,0],"fov":44}}
    if T<15.3: return cab(T,13.3,"drive")
    if T<17.3: u=T-15.3; return LOT,{"anim":"gait","mode":"jog","t":u+1.0,"dir":[1,0],"p0":[-1.0,2.0],"vanX":6.0+3.0*u,"keepVan":True,"mouth":mouth_any(T,['s12'],'mouth_shout'),"cam":{"rel":True,"pos":[-2.8,3.2,3.6],"look":[0.8,0.8,0],"fov":44}}
    if T<19.3: return lena(T,17.3)
    if T<21.3: u=T-19.3; return LOT,{"anim":"gait","mode":"jog","phone":True,"t":u,"dir":[1,0],"p0":[-3.0,2.0],"vanX":4.0+2.0*u,"keepVan":True,"mouth":"mouth_closed_worried","cam":{"rel":True,"pos":[2.4,1.3,2.4],"look":[0,0.95,0],"fov":42}}
    if T<24.3:
        u=T-21.3; k=u/3.0; cam={"rel":True,"pos":[2.6,0.8,4.0],"look":[0,0.8,0],"fov":44} if T<22.8 else {"rel":True,"pos":[-1.8,1.0,3.2],"look":[0,0.8,0],"fov":44}
        return LOT,{"anim":"boot2","k":k,"t":u,"dur":2.0,"dir":[1,0],"p0":[-3.0,2.0],"vanX":9.0+2.5*u,"keepVan":True,"mouth":mouth(T,'s14','mouth_shout'),"cam":cam}
    # ---------- Maple Street
    if T<26.3: return LS,{"anim":"van","vanZ":off(T),"vanG":T,"hideDex":True,"cam":{"rel":True,"pos":[3.6,1.2,-4.6],"look":[0,1.0,0.6],"fov":46}}
    if T<28.3: return LS,{"anim":"nana","what":"watch","t":T-26.3,"g":T-26.3,"hideDex":True,"cam":{"rel":True,"pos":[1.1,0.95,3.0],"look":[0,0.05,0],"fov":34}}
    if T<30.3: return cab(T,28.3,"horn")
    if T<32.3: u=T-30.3; return LS,{"anim":"van","vanZ":off(T),"vanG":T,"hideDex":True,"pigeonZ":vz(30.3)-5.5,"pigeonT":u*0.95-0.1,"cam":{"pos":[0.9,1.25,vz(30.3)-11.0],"look":[0,1.1,vz(30.3)-3.0],"fov":52}}
    zJ=lambda T:vz(T0)+5.88-2.7*(T-T0)
    if T<34.3: return street_cam_act(T,"jog",{"rel":True,"pos":[4.4,1.0,0.8],"look":[0,0.6,-1.8],"fov":50},tt=T-T0,dz=zJ(T),focusDz=-2.2,phone=True,eyes="eyes_open",brows="brows_up",mouth=mouth_any(T,['s20'],'mouth_smile'))
    if T<36.3: return street_cam_act(T,"jog",{"rel":True,"pos":[2.1,1.4,-2.4],"look":[0,1.0,0.3],"fov":42},tt=T-T0,dz=zJ(T),phone=True,eyes="eyes_open",brows="brows_up",mouth=mouth_any(T,['s20','s21'],'mouth_smile'))
    if T<36.85: return street_cam_act(T,"jog",{"rel":True,"pos":[5.2,1.0,-0.2],"look":[0,0.3,0],"fov":42},tt=T-T0,dz=zJ(T),mouth=mouth(T,'s21','mouth_shout'))
    if T<T_GR:
        a=(T-36.85)/1.15; zP0=zJ(36.85); dz=zP0-2.7*min(T-36.85,0.345)*0.8
        return street_cam_act(T,"jump",{"rel":True,"pos":[5.2,1.0,-0.2],"look":[0,0.3,0],"fov":42},a=a,dz=dz,mouth=mouth(T,'s22','mouth_shout'))
    g=T
    if T<40.0: return street_cam_act(T,"drag",{"rel":True,"pos":[3.4,0.9,0.6],"look":[0,0,0],"fov":42},g=g,mouth=mouth(T,'s22','mouth_shout'))
    if T<42.0: return street_cam_act(T,"drag",{"rel":True,"pos":[1.7,1.0,0.6],"look":[0,0.05,-0.1],"fov":30},g=g,mouth="mouth_closed_worried")
    if T<44.0: return LS,{"anim":"nana","what":"brace","t":min(1,(T-42.0)/0.6),"g":T-42.0,"hideDex":True,"cam":{"rel":True,"pos":[1.1,0.95,3.0],"look":[0,0.05,0],"fov":34}}
    if T<46.0: return cab(T,44.0,"horn")
    if T<48.0: return street_cam_act(T,"drag",{"rel":True,"pos":[-2.8,1.7,3.4],"look":[0,0.4,-0.4],"fov":48},g=g,mouth=mouth(T,'s27','mouth_closed_worried'))
    if T<50.0: return street_cam_act(T,"reach",{"rel":True,"pos":[2.6,1.0,1.7],"look":[0.1,0.25,0],"fov":40},g=g,k=min(1,(T-48.0)/1.2),mouth=mouth(T,'s28','mouth_closed_worried'))
    if T<52.6: return None   # split screen handled separately
    if T<54.3: return lena(T,52.6,off0=2.4)
    if T<55.9: return cab(T,54.3,"cover")
    if T<57.0: return LS,{"anim":"face","t":T-55.9,"mouth":mouth(T,'s33','mouth_grin_open'),"eyes":"eyes_wide","brows":"brows_smirk","cam":{"rel":True,"pos":[0.4,0.1,1.25],"look":[0,0,0],"fov":30}}
    ti=T-T_IMP
    if T<58.1: return LS,{"anim":"act","m":"crash","ti":ti,"g":T,"vanZ":off(T),"vanG":T,"mouth":mouth(T,'s33','mouth_grin_open'),"cam":{"pos":[-4.6,1.7,SZ+6.4],"look":[-1.0,0.9,SZ+0.4],"fov":56}}
    return LS,{"anim":"act","m":"crash","ti":min(ti,1.8),"g":T,"vanZ":off(T),"vanG":T,"mouth":mouth(T,'s33','mouth_grin_open'),"cam":{"pos":[5.2,1.7,SZ+11.5],"look":[0,1.0,SZ+3.6],"fov":50}}
def split_items(g):
    T=g/FPS; sp=dict(anim="act",m="reach",k=1.0,g=T,vanZ=off(T),vanG=T,mouth=mouth(T,'s29','mouth_closed_worried'))
    sc={**LS,"w":540,"h":1920}
    L={**sp,"cam":{"rel":True,"pos":[2.3,0.1,0.25],"look":[0.24,0.05,-0.1],"fov":34}}
    R={**sp,"cam":{"rel":True,"pos":[-2.3,-0.05,-0.15],"look":[-0.3,-0.08,-0.15],"fov":34},"focusOverride":"neck"}
    return [{"name":f"f{g:05d}L","scene":sc,"spec":L},{"name":f"f{g:05d}R","scene":sc,"spec":R}]
items=[]; G0=136; G1=int(59.1*FPS)
for g in range(G0,G1+1):
    T=g/FPS; r=shot(T)
    if r is None: items+=split_items(g); continue
    sc,sp=r; items.append({"name":f"f{g:05d}","scene":sc,"spec":sp})
json.dump({"w":1080,"h":1920,"items":items},open('/tmp/full2_items.json','w'))
sp=[x for x in items if x['name'].endswith(('L','R'))]; json.dump({"w":540,"h":1920,"items":[x for x in sp if x['name'].endswith('L')]+[x for x in sp if x['name'].endswith('R')]},open('/tmp/split_items.json','w'))
json.dump({"total":TOTAL,"cues":cues,"T0":T0,"first":G0,"last":G1,"SZ":SZ,"T_IMP":T_IMP},open('full_meta.json','w'))
print(len(items),'items')
