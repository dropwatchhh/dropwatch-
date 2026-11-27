"""Short animation preview clips at 12 fps (540x960), rendered with render_lab.mjs then blended to 24 fps."""
import json
FPS=12; LS={"scene":"lab_street"}; CAB={"scene":"cab"}
clips={}
def seq(name,dur,fn):
    n=int(dur*FPS); clips.setdefault(name,[])
    for i in range(n): clips[name].append(fn(i/FPS, i/max(1,n-1)))
def item(name,scene,spec): return {"name":name,"scene":scene,"spec":spec}
def clip(cname):
    fr=len(clips[cname]); return fr
frames={}
def add(cname,scene,mk,dur):
    n=int(dur*FPS); L=frames.setdefault(cname,[])
    for i in range(n):
        t=i/FPS; u=i/max(1,n-1); L.append(item(f"{cname}_{len(L):04d}",scene,mk(t,u)))
# ---- C1 Dex running
side=lambda sp: {"rel":True,"pos":[5.0,0.95,0.6],"look":[0,0.05,-0.2],"fov":36}
add("c1_dex_run",LS,lambda t,u:{"anim":"run","t":t,"cam":side(4.6)},3.0)
add("c1_dex_run",LS,lambda t,u:{"anim":"selfie","t":t,"amp":1.15,"cam":{"rel":True,"pos":[3.4,1.2,2.6],"look":[0,0.2,-0.3],"fov":36}},2.0)
add("c1_dex_run",LS,lambda t,u:{"anim":"boot","k":u,"t":t,"dur":2.5,"cam":{"rel":True,"pos":[5.2,1.0,0.5],"look":[0,0.1,-1.2],"fov":42}},2.5)
# ---- C2 chase and grab
def van(t,sp=5.0): return {"vanZ":-sp*t,"vanG":t}
add("c2_dive_drag_hang_reach",LS,lambda t,u:{**van(t),"anim":"dive","t":u,"cam":{"rel":True,"pos":[7.5,1.3,2.8],"look":[0,0.4,-0.6],"fov":42}},2.5)
add("c2_dive_drag_hang_reach",LS,lambda t,u:{**van(2.5+t),"anim":"drag","g":t,"cam":{"rel":True,"pos":[3.0,0.8,3.4],"look":[0,0.2,-1.5],"fov":42}},2.0)
add("c2_dive_drag_hang_reach",LS,lambda t,u:{**van(4.5+t),"anim":"hang","g":t,"cam":{"rel":True,"pos":[4.4,1.0,0.8],"look":[0,0.6,-0.6],"fov":40}},1.5)
add("c2_dive_drag_hang_reach",LS,lambda t,u:{**van(6.0+t),"anim":"reach","t":u,"g":t,"cam":{"rel":True,"pos":[3.0,1.1,1.0],"look":[0,0.5,-0.7],"fov":42}},1.5)
# ---- C3 Nana Dot
nc={"rel":True,"pos":[1.1,0.95,3.0],"look":[0,0.05,0],"fov":34}
for fn,d in (("watch",1.5),("put",2.2),("brace",2.0),("wave",1.5),("duck",1.5)):
    add("c3_nana_dot",LS,lambda t,u,fn=fn,d=d:{"anim":"nana","what":fn,"t":u,"g":t,"cam":nc},d)
# ---- C4 Gig, pigeons, tulips
gc={"rel":True,"pos":[-0.55,0.45,-0.75],"look":[0,-0.05,0],"fov":44}
add("c4_gig_pigeons_tulips",CAB,lambda t,u:{"anim":"cab","what":"horn","t":t,"cam":gc},2.4)
add("c4_gig_pigeons_tulips",CAB,lambda t,u:{"anim":"cab","what":"cover","t":u,"cam":gc},1.2)
add("c4_gig_pigeons_tulips",CAB,lambda t,u:{"anim":"cab","what":"look","t":u,"cam":gc},1.2)
add("c4_gig_pigeons_tulips",LS,lambda t,u:{"anim":"van","vanZ":-6+1.0*t,"vanG":t,"pigeonT":t*0.9,"cam":{"pos":[0.4,1.3,-26.0],"look":[0,1.3,-15.0],"fov":50}},2.2)
add("c4_gig_pigeons_tulips",LS,lambda t,u:{"anim":"van","vanZ":-19.5-1.2*t,"vanG":2+t,"tulipT":t*0.9,"cam":{"pos":[6.0,1.3,-28.0],"look":[0,0.9,-28.0],"fov":44}},2.0)
for k,L in frames.items():
    for i,it in enumerate(L): it["name"]=f"{k}_{i:04d}"
    json.dump({"w":540,"h":960,"items":L},open(f"/tmp/{k}.json","w")); print(k,len(L))
