"""Synced animation preview reel: animation frames + voice lines (voice A) + simple SFX, all timed from the v6 takes."""
import numpy as np, soundfile as sf, json, subprocess, sys
FPS=12; SR=24000
T={k:sf.read(f'voice_takes/v6/{k}.wav')[0].astype(np.float32) for k in ['s10','s13','s14','s16','s22','s23','s24','s27','s28']}
dur={k:len(v)/SR for k,v in T.items()}
LS={"scene":"lab_street"}; CAB={"scene":"cab"}; CALL={"scene":"call"}
items=[]; audio=np.zeros(int(70*SR),dtype=np.float32); segs=[]
rng=np.random.default_rng(4)
def lp(x,k): return np.convolve(x,np.ones(k)/k,'same')
def viseme(x,fps=FPS):
    h=SR//fps; out=[]
    for i in range(int(len(x)/h)+1):
        c=int((i+0.5)*h); w=x[max(0,c-600):c+600]
        if len(w)<64: out.append('mouth_smile'); continue
        r=np.sqrt(np.mean(w**2)); S=np.abs(np.fft.rfft(w*np.hanning(len(w)))); fr=np.fft.rfftfreq(len(w),1/SR); cen=(S*fr).sum()/(S.sum()+1e-9)
        l=np.clip((20*np.log10(r+1e-6)+48)/32,0,1)
        out.append('mouth_smile' if l<0.22 else ('mouth_E' if cen>2600 else 'mouth_O') if l<0.45 else 'mouth_A' if l<0.85 else 'mouth_shout')
    return out
def addvoice(k,at): 
    x=T[k]; i=int(at*SR); audio[i:i+len(x)]+=x
    return viseme(x)
def sfx(kind,at,dur=0.5,vol=0.5):
    n=int(SR*dur); t=np.arange(n)/SR; i=int(at*SR)
    if kind=='horn': y=(np.sign(np.sin(2*np.pi*330*t))+np.sign(np.sin(2*np.pi*415*t)))*0.3; y=lp(y,6)*np.minimum(1,t/0.01)*np.minimum(1,(dur-t)/0.03)
    elif kind=='clang': y=sum(np.sin(2*np.pi*f*t)*np.exp(-t*d) for f,d in ((800,9),(1230,12),(1700,16),(2310,22)))*0.35
    elif kind=='thud': y=np.sin(2*np.pi*(40+60*np.exp(-t*30))*t)*np.exp(-t*12)+lp(rng.standard_normal(n),30)*np.exp(-t*20)*0.8
    elif kind=='wings': env=(np.sin(2*np.pi*9*t)>0.2)*np.minimum(1,t/0.05)*np.minimum(1,(dur-t)/0.2); y=(lp(rng.standard_normal(n),5)-lp(rng.standard_normal(n),40))*env*1.4
    elif kind=='squeak': f=1700+900*np.minimum(1,t/dur); y=np.sin(2*np.pi*np.cumsum(f)/SR)*np.sin(np.pi*np.minimum(1,t/dur))*0.5
    elif kind=='whoosh': y=(lp(rng.standard_normal(n),12)-lp(rng.standard_normal(n),80))*np.sin(np.pi*np.minimum(1,t/dur))*1.2
    audio[i:i+n]+=(y*vol).astype(np.float32)
def seg(name,dur_s,mk):
    n=int(round(dur_s*FPS)); start=len(items)
    for i in range(n): items.append({"name":f"f{len(items):05d}","scene":mk['scene'],"spec":mk['spec'](i/FPS,i/max(1,n-1),i)})
    segs.append((name,start,len(items)-start))
side=lambda t:{"rel":True,"pos":[5.0,0.95,0.6],"look":[0,0.05,-0.2],"fov":36}
mouthf=lambda vis,i: vis[i] if i<len(vis) else 'mouth_smile'
cur=0.0
# R1 run + "Brake, Gig! BRAKE!"
d=0.3+dur['s10']+0.5; vis=addvoice('s10',cur+0.3); sfx('thud',cur+0.1,0.3,0.15)
seg('R1 run',d,{"scene":LS,"spec":lambda t,u,i:{"anim":"gait","mode":"jog","t":t,"mouth":mouthf(vis,int((t-0.3)*FPS)) if t>=0.3 else 'mouth_smile',"cam":{"rel":True,"pos":[4.2,0.9,0.4],"look":[0,0.1,0],"fov":34}}}); cur+=d
# R2 boot loss + catchphrase
d=0.3+dur['s14']+0.6; vis=addvoice('s14',cur+0.3); sfx('clang',cur+0.3+d*0.0+0.9,0.6,0.5)
seg('R2 boot',d,{"scene":LS,"spec":lambda t,u,i:{"anim":"boot2","k":min(1,t/d),"t":t,"dur":d*0.7,"mouth":mouthf(vis,int((t-0.3)*FPS)) if t>=0.3 else 'mouth_smile',"cam":{"rel":True,"pos":[5.2,1.0,0.5],"look":[0,0.1,-1.2],"fov":42}}}); cur+=d
# R3 chase: run, plant, jump, grab ("Got it!"), drag (Lena report)
gt=2.62; ld=gt+dur['s22']+0.3; d23=ld+dur['s23']+0.7; vis22=addvoice('s22',cur+gt); addvoice('s23',cur+ld)
sfx('thud',cur+2.78,0.4,0.6); sfx('thud',cur+3.0,0.3,0.25)
vzf=lambda tt:-(1.5*tt+0.2*tt*tt)
def chase(t,u,i):
    cam={"rel":True,"pos":[7.5-1.0*min(1,max(0,(t-1.4)/0.8))+3.8*min(1,max(0,(t-2.4)/0.5)),1.1-0.1*min(1,max(0,(t-1.4)/0.8)),2.6-2.8*min(1,max(0,(t-1.4)/0.8))],"look":[0,0.4,-0.9],"fov":44}
    m='mouth_shout' if t<gt-0.4 else (mouthf(vis22,int((t-gt)*FPS)) if t<gt+dur['s22'] else 'mouth_closed_worried')
    return {"anim":"chase","tt":t,"vanZ":vzf(t),"vanZ0":0,"vanG":t,"mouth":m,"cam":cam}
seg('R3 chase grab drag',d23,{"scene":LS,"spec":chase}); cur+=d23
# R4 hang + reach ("Oh no." / "Oh. Oh no. Oh YES.")
d4a=0.25+dur['s27']+0.4; vis27=addvoice('s27',cur+0.25)
seg('R4a hang',d4a,{"scene":LS,"spec":lambda t,u,i:{"anim":"hang","g":t,"vanZ":-(1.5*t),"vanG":t,"mouth":mouthf(vis27,int((t-0.25)*FPS)) if t>=0.25 else 'mouth_closed_worried',"cam":{"rel":True,"pos":[4.4,1.0,0.8],"look":[0,0.6,-0.6],"fov":40}}}); cur+=d4a
d4b=0.2+dur['s28']+0.4; vis28=addvoice('s28',cur+0.2)
seg('R4b reach',d4b,{"scene":LS,"spec":lambda t,u,i:{"anim":"reach","t":min(1,t/(d4b*0.8)),"g":t,"vanZ":-(1.5*t),"vanG":t,"mouth":mouthf(vis28,int((t-0.2)*FPS)) if t>=0.2 else 'mouth_closed_worried',"cam":{"rel":True,"pos":[3.0,1.1,1.0],"look":[0,0.5,-0.7],"fov":42}}}); cur+=d4b
# R5 Nana: watching (s16, reported, closed mouth), brace (s24), wave, duck
nc={"rel":True,"pos":[1.1,0.95,3.0],"look":[0,0.05,0],"fov":34}
d=0.3+dur['s16']+0.3; addvoice('s16',cur+0.3)
seg('R5a Nana watching',d,{"scene":LS,"spec":lambda t,u,i:{"anim":"nana","what":"watch","t":t,"g":t,"cam":nc}}); cur+=d
d=0.3+dur['s13']+0.5; addvoice('s13',cur+0.3)
seg('R5L Lena (voice reports her)',d,{"scene":CALL,"spec":lambda t,u,i:{"anim":"lena","t":t,"dur":d,"cam":{"pos":[0,1.3,2.0-0.3*u],"look":[0,1.1,0],"fov":30}}}); cur+=d
d=0.25+dur['s24']+0.4; addvoice('s24',cur+0.25)
seg('R5b Nana brace',d,{"scene":LS,"spec":lambda t,u,i:{"anim":"nana","what":"brace","t":min(1,t/0.6),"g":t,"cam":nc}}); cur+=d
d=1.2; seg('R5c Nana wave',d,{"scene":LS,"spec":lambda t,u,i:{"anim":"nana","what":"wave","t":0.5,"g":t,"cam":nc}}); cur+=d
d=1.6; sfx('whoosh',cur+0.1,0.6,0.5); seg('R5d Nana duck',d,{"scene":LS,"spec":lambda t,u,i:{"anim":"nana","what":"duck","t":min(1,t/0.5),"g":t,"cam":nc}}); cur+=d
# R6 Gig horn, cover, look; pigeons; tulips
gc={"rel":True,"pos":[-0.55,0.45,-0.75],"look":[0,-0.05,0],"fov":44}
d=2.2
for tt in (0.25,1.0): sfx('horn',cur+tt,0.45,0.5)
seg('R6a Gig horn',d,{"scene":CAB,"spec":lambda t,u,i:{"anim":"cab","what":"horn","t":t,"cam":gc}}); cur+=d
d=1.1; sfx('squeak',cur+0.2,0.35,0.5); seg('R6b Gig covers eyes',d,{"scene":CAB,"spec":lambda t,u,i:{"anim":"cab","what":"cover","t":u,"cam":gc}}); cur+=d
d=1.0; seg('R6c Gig looks',d,{"scene":CAB,"spec":lambda t,u,i:{"anim":"cab","what":"look","t":u,"cam":gc}}); cur+=d
d=2.2; sfx('wings',cur+0.1,1.8,0.6); seg('R6d Pigeons scatter',d,{"scene":LS,"spec":lambda t,u,i:{"anim":"van","vanZ":-6+1.0*t,"vanG":t,"pigeonT":t*0.9,"cam":{"pos":[0.4,1.3,-26.0],"look":[0,1.3,-15.0],"fov":50}}}); cur+=d
d=2.0; sfx('whoosh',cur+0.1,0.8,0.5); seg('R6e Tulips fly',d,{"scene":LS,"spec":lambda t,u,i:{"anim":"van","vanZ":-19.5-1.2*t,"vanG":2+t,"tulipT":t*0.9,"cam":{"pos":[6.0,1.3,-28.0],"look":[0,0.9,-28.0],"fov":44}}}); cur+=d
audio=audio[:int((cur+0.3)*SR)]; sf.write('reel_audio_raw.wav',audio,SR)
json.dump({"w":540,"h":960,"items":items},open('/tmp/reel.json','w')); json.dump(segs,open('reel_segments.json','w'))
print('reel',round(cur,1),'s',len(items),'frames'); [print(s) for s in segs]

# ---- extra clips: phone grip close-ups, walk and jog from the side and front
def clipjson(name,items_,w=540,h=960): json.dump({"w":w,"h":h,"items":items_},open(f"/tmp/{name}.json","w"))
PH=[0.45,1.1,1.12,1.14,1.15]
p1=[]
for i in range(36):
    t=i/FPS; u=i/35; e=u*u*(3-2*u)
    pose={"yaw":0,"spine":[2+3*e,0,0],"head":[0,0,0],"L":{"sh":[6,10],"el":14,"curl":[0.35,0.45,0.5,0.55,0.6]},"R":{"sh":[20+52*e,14],"el":96+16*e+3*np.sin(t*6),"curl":PH,"phone":True,"roll":-10-40*e},"legL":{"hip":[4,3],"knee":8},"legR":{"hip":[-3,3],"knee":4}}
    p1.append({"name":f"p1_{len(p1):04d}","scene":{"scene":"character","who":"dex"},"spec":{"anim":"hand","pose":pose,"cam":{"rel":True,"pos":[0.7+0.1*np.sin(t),0.2,0.9],"look":[0,0,0],"fov":24}}})
for i in range(30):
    t=i/FPS; p1.append({"name":f"p1_{len(p1):04d}","scene":LS,"spec":{"anim":"gait","mode":"walk","phone":True,"t":t,"cam":{"rel":True,"pos":[3.6,0.8,0.8],"look":[0,0.1,0],"fov":34}}})
clipjson("p1_phone",p1)
p2=[]
for mode,T in (("walk",2.4),("jog",2.4)):
    for view,cam,fy in (("side",{"rel":True,"pos":[4.2,0.9,0.4],"look":[0,0.1,0],"fov":34},0),("front",{"rel":True,"pos":[0.3,1.0,-4.2],"look":[0,0.1,0],"fov":34},0)):
        for i in range(int(T*FPS)): p2.append({"name":f"p2_{len(p2):04d}","scene":LS,"spec":{"anim":"gait","mode":mode,"t":i/FPS,"faceYaw":fy,"cam":cam}})
clipjson("p2_walk_jog",p2)
print('p1',len(p1),'p2',len(p2))
