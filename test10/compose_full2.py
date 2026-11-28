"""Overlays (LIVE badge, chat, pinned banner, captions, call cards, reported-speech bubbles, split screen, vote card) + 12 fps -> 24 fps blend + audio."""
import json, os, glob, subprocess, sys, textwrap
from PIL import Image, ImageDraw, ImageFont
F=lambda w,s: ImageFont.truetype(f"/usr/share/fonts/opentype/inter/Inter-{w}.otf", s)
meta=json.load(open('full_meta.json')); TOTAL=meta['total']; FPS=12; NG=int(TOTAL*FPS)+1; FIRST=meta['first']; LAST=meta['last']
OUT='/tmp/full_ov'; os.makedirs(OUT,exist_ok=True)
CALLS=[(17.3,19.3,'LENA CHO'),(26.3,28.3,'NANA DOT'),(52.6,54.3,'LENA CHO')]
CHAT=[(1.6,"mia.moon",(255,150,200),"he said ANYTHING lol"),(3.1,"bigmaple44",(255,210,90),"wait what is behind him"),(4.8,"noodle_nate",(255,170,110),"DEX BEHIND U"),(7.3,"mia.moon",(255,150,200),"THE VAN"),
      (22.4,"kai_k",(160,220,255),"BOOT"),(33.9,"priya_noodles",(255,190,120),"Dex your order's been ready for an hour"),(46.6,"mia.moon",(255,150,200),"NOT THE TULIPS"),(54.8,"bigmaple44",(255,210,90),"CHASE OR PLAY??")]
CAPS=[(3.1,3.95,"ANYTHING"),(9.85,10.8,"THAT'S MY VAN?!"),(10.8,11.4,"GIG IS DRIVING"),(14.6,16.3,"NANA DOT'S FLOWERS"),(38.0,38.9,"GOT IT!"),(46.55,47.9,"OH NO"),(48.9,50.4,"OH YES")]
BUBBLES=[(17.6,21.0,"LENA","Why is my headliner's guitar driving away?"),(26.4,29.8,"NANA DOT","That's HIS van? Oh, that boy."),(39.0,42.5,"LENA","Twelve seconds until that van meets a florist."),(43.0,44.9,"NANA DOT","BRAKE, you little bandit!"),(52.8,54.3,"LENA","Whatever you do, do it now.")]
def pill(d,b,fill): d.rounded_rectangle(b,radius=(b[3]-b[1])//2,fill=fill)
def in_call(T): return next((c for c in CALLS if c[0]<=T<c[1]),None)
def hud(d,T):
    x,y=440,150; pill(d,(x,y,x+150,y+62),(230,30,60,255)); d.ellipse((x+18,y+22,x+36,y+40),fill=(255,255,255,255)); d.text((x+48,y+8),"LIVE",font=F("ExtraBold",36),fill=(255,255,255,255))
    pill(d,(x+164,y,x+374,y+62),(20,16,30,190)); ex,ey=x+190,y+31; d.ellipse((ex-16,ey-9,ex+16,ey+9),outline=(255,255,255,255),width=3); d.ellipse((ex-5,ey-5,ex+5,ey+5),fill=(255,255,255,255))
    d.text((x+222,y+11),f"{12481+int(T*37):,}",font=F("Bold",36),fill=(255,255,255,255))
def chat(d,T):
    if any(t0<=T<t1 for t0,t1,_,_ in BUBBLES) or 55.9<=T<57.0: return
    rows=[c for c in CHAT if c[0]<=T<c[0]+5.0][-2:]; cy=240; fn,fm=F("Bold",24),F("Medium",24)
    for i,(t0,u,col,m) in enumerate(rows):
        pop=min(1,(T-t0)/0.18); a=int(255*(0.6+0.4*(i+1)/len(rows))); fade=min(1,(t0+5.0-T)/0.4); a=int(a*fade)
        mm=m if len(m)<26 else m[:25]+'…'; tw=d.textlength(u+"  ",font=fn)+d.textlength(mm,font=fm); w=int(tw+64); cx=1050-w; off=int((1-pop)*40)
        pill(d,(cx+off,cy,cx+w+off,cy+50),(16,12,26,int(a*0.6*pop))); d.ellipse((cx+8+off,cy+8,cx+42+off,cy+42),fill=col+(int(a*pop),))
        d.text((cx+17+off,cy+10),u[0].upper(),font=F("Bold",20),fill=(20,12,30,int(a*pop))); d.text((cx+52+off,cy+11),u+"  ",font=fn,fill=col+(int(a*pop),)); d.text((cx+52+off+d.textlength(u+"  ",font=fn),cy+11),mm,font=fm,fill=(255,255,255,int(a*pop))); cy+=58
def banner(d,T,flash=False):
    if 3.68<=T<5.4 or flash:
        t0,t1=(3.68,5.4) if not flash else (52.6,54.3)
        k=min(1,(T-t0)/0.2); k=1-(1-k)**3; fade=min(1,(t1-T)/0.25); y0=int(1330+(1-k)*120); a=int(255*fade)
        if flash and int((T-52.6)*8)%2: a=int(a*0.55)
        d.rounded_rectangle((60,y0,1020,y0+230),radius=34,fill=(18,14,32,int(235*fade)),outline=(255,63,176,a),width=5)
        d.ellipse((92,y0+24,132,y0+64),fill=(255,63,176,a)); d.text((150,y0+22),"PINNED  ·  LENA CHO",font=F("Bold",30),fill=(255,150,215,a))
        d.text((92,y0+82),"HEADLINE SHOW IN 30 DAYS.",font=F("ExtraBold",46),fill=(255,255,255,a)); d.text((92,y0+142),"NO GUITAR = NO HEADLINE SHOW",font=F("ExtraBold",46),fill=(255,214,70,a))
def caption(d,T):
    for t0,t1,txt in CAPS:
        if t0<=T<t1:
            pop=min(1,(T-t0)/0.12); sc=0.8+0.2*(1-(1-pop)**2); size=120
            while d.textlength(txt,font=F("ExtraBold",size))>860: size-=6
            size=int(size*sc); font=F("ExtraBold",size); tw=d.textlength(txt,font=font); d.text(((1080-tw)/2,1680),txt,font=font,fill=(255,63,176,255),stroke_width=14,stroke_fill=(26,13,51,255)); return
def bubble(d,T):
    for t0,t1,who,txt in BUBBLES:
        if t0<=T<t1:
            pop=min(1,(T-t0)/0.15); fade=min(1,(t1-T)/0.2); a=int(255*fade*pop)
            call=in_call(T) is not None; lines=textwrap.wrap(txt,26 if call else 22); fnt=F("Bold",40 if call else 34); lh=52 if call else 44; h=60+len(lines)*lh
            x0,x1,y0=(70,1010,1560-int((1-pop)*20)) if call else (36,36+600,236-int((1-pop)*20))
            d.rounded_rectangle((x0,y0,x1,y0+h),radius=30,fill=(18,14,32,int(215*fade*pop)),outline=(255,214,70,a),width=3)
            d.text((x0+26,y0+10),who,font=F("ExtraBold",26),fill=(255,150,215,a))
            for i,l in enumerate(lines): d.text((x0+26,y0+46+i*lh),l,font=fnt,fill=(255,255,255,a))
            return
def callcard(d,c,T):
    d.rounded_rectangle((18,18,1062,1902),radius=56,outline=(255,63,176,255),width=10)
    pill(d,(60,120,60+int(d.textlength(c[2]+"  ·  LIVE CALL",font=F("ExtraBold",34)))+60,190),(16,12,26,230)); d.ellipse((78,142,100,164),fill=(60,230,120,255)); d.text((116,134),c[2]+"  ·  LIVE CALL",font=F("ExtraBold",34),fill=(255,255,255,255))
def vote(im,T):
    W,H=im.size; ov=Image.new('RGBA',im.size,(0,0,0,0)); d=ImageDraw.Draw(ov); k=min(1,(T-59.1)/0.35)
    d.rectangle((0,0,W//2,H),fill=(255,40,150,int(110*k))); d.rectangle((W//2,0,W,H),fill=(30,220,200,int(110*k))); d.rectangle((W//2-4,0,W//2+4,H),fill=(255,255,255,int(230*k)))
    for x,txt,col in ((W//4,"CHASE",(255,255,255)),(3*W//4,"PLAY",(255,255,255))):
        f=F("ExtraBold",150 if txt=="PLAY" else 140); w=d.textlength(txt,font=f); d.text((x-w/2,820),txt,font=f,fill=col+(int(255*k),),stroke_width=14,stroke_fill=(26,13,51,int(255*k)))
    d.text((W//4-190,1000),"grab the bumper",font=F("Bold",38),fill=(255,255,255,int(230*k))); d.text((3*W//4-170,1000),"grab the guitar",font=F("Bold",38),fill=(255,255,255,int(230*k)))
    lines=[(60.34,"CHASE or PLAY?",1.6),(62.0,"COMMENT ONE WORD",1.45),(63.45,"YOUR CALL, CREW!",99)]
    for t0,txt,dur in lines:
        if t0<=T<t0+dur:
            pop=min(1,(T-t0)/0.14); sc=0.75+0.25*(1-(1-pop)**2); size=130
            while d.textlength(txt,font=F("ExtraBold",size))>940: size-=4
            f=F("ExtraBold",int(size*sc)); w=d.textlength(txt,font=f); d.text(((W-w)/2,1480),txt,font=f,fill=(255,214,70,255) if txt.startswith('YOUR') else (255,255,255,255),stroke_width=14,stroke_fill=(26,13,51,255))
    return Image.alpha_composite(im.convert('RGBA'),ov)
def hudlayer(im,T):
    W,H=im.size; ov=Image.new('RGBA',im.size,(0,0,0,0)); d=ImageDraw.Draw(ov); c=in_call(T)
    if c: callcard(d,c,T)
    else: hud(d,T)
    if not c: chat(d,T)
    banner(d,T,flash=(52.6<=T<54.3)); caption(d,T); bubble(d,T)
    return Image.alpha_composite(im.convert('RGBA'),ov)
def base_path(g,suffix=''):
    if g<FIRST: return f'/tmp/open_out/f{2*g:04d}.png'
    gg=min(g,LAST)
    for i in range(4):
        p=f'/tmp/hi2_out_{i}/f{gg:05d}{suffix}.png'
        if os.path.exists(p): return p
    return None
def split(T,g):
    Lp=f'/tmp/split_out/f{g:05d}L.png'; Rp=f'/tmp/split_out/f{g:05d}R.png'
    L=Image.open(Lp).convert('RGB'); R=Image.open(Rp).convert('RGB')
    S=Image.new('RGB',(1080,1920)); S.paste(L,(0,0)); S.paste(R,(540,0)); d=ImageDraw.Draw(S); d.rectangle((536,0,544,1920),fill=(255,255,255))
    for x,txt,sub in ((270,"CHASE","grab the bumper"),(810,"PLAY","grab the guitar")):
        f=F("ExtraBold",100); w=d.textlength(txt,font=f); d.text((x-w/2,1560),txt,font=f,fill=(255,255,255),stroke_width=12,stroke_fill=(26,13,51))
        f2=F("Bold",36); w2=d.textlength(sub,font=f2); d.text((x-w2/2,1690),sub,font=f2,fill=(255,255,255),stroke_width=6,stroke_fill=(26,13,51))
    return S
SPLIT=True
if __name__=='__main__':
    for f in glob.glob(OUT+'/*.png'): os.remove(f)
    missing=0
    for g in range(NG):
        T=g/FPS
        if 50.0<=T<52.6 and SPLIT: im=split(T,g)
        else:
            p=base_path(g)
            if p is None or not os.path.exists(p): missing+=1; p=base_path(max(g-1,0))
            im=Image.open(p).convert('RGB')
            if im.size!=(1080,1920): im=im.resize((1080,1920))
        if T>=59.1: im=vote(im,T)
        hudlayer(im,T).convert('RGB').save(f'{OUT}/{g:05d}.png')
    print('missing frames:',missing)
    subprocess.run(['ffmpeg','-y','-v','error','-framerate','12','-i',f'{OUT}/%05d.png','-i','audio_full_final.wav','-vf','framerate=fps=24:interp_start=0:interp_end=255:scene=100','-af','alimiter=limit=0.85:level=false','-c:v','libx264','-pix_fmt','yuv420p','-crf','17','-preset','medium','-c:a','aac','-b:a','192k','-t',str(TOTAL),'../output/episode1_v6_12fps_blend.mp4'])
    print('encoded')
