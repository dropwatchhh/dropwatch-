"""Flat overlays (LIVE badge, chat, pinned message, captions) over the 3D frames, then mux with the mixed audio."""
import sys, os, subprocess
from PIL import Image, ImageDraw, ImageFont
F=lambda w,s: ImageFont.truetype(f"/usr/share/fonts/opentype/inter/Inter-{w}.otf", s)
FR='frames'; OUT='ov'; os.makedirs(OUT,exist_ok=True)
LOT={'S1','S9','S8','S2','S3','S4','S6','S7'}
CHAT=[(2.6,"mia.moon",(255,150,200),"he said ANYTHING lol"),(4.1,"bigmaple44",(255,210,90),"wait what is behind him"),(7.3,"noodle_nate",(255,170,110),"DEX BEHIND U"),(9.2,"mia.moon",(255,150,200),"THE VAN")]
def pill(d,b,fill): d.rounded_rectangle(b,radius=(b[3]-b[1])//2,fill=fill)
def shot_of(g):
    for s,a,b in [('S1',0,1.9),('S9',1.9,2.9),('S8',2.9,3.6),('S2',3.6,5.1),('S3',5.1,6.6),('S4',6.6,8.3),('S7',8.3,9.7),('S5',9.7,11.3),('S6',11.3,12.1)]:
        if a<=g<b: return s
def draw(im,g):
    W,H=im.size; ov=Image.new('RGBA',im.size,(0,0,0,0)); d=ImageDraw.Draw(ov); s=shot_of(g)
    if s in LOT:
        x,y=440,150; pill(d,(x,y,x+150,y+62),(230,30,60,255)); d.ellipse((x+18,y+22,x+36,y+40),fill=(255,255,255,255)); d.text((x+48,y+8),"LIVE",font=F("ExtraBold",36),fill=(255,255,255,255))
        pill(d,(x+164,y,x+374,y+62),(20,16,30,190)); ex,ey=x+190,y+31; d.ellipse((ex-16,ey-9,ex+16,ey+9),outline=(255,255,255,255),width=3); d.ellipse((ex-5,ey-5,ex+5,ey+5),fill=(255,255,255,255))
        d.text((x+222,y+11),f"{12481+int(g*37):,}",font=F("Bold",36),fill=(255,255,255,255))
        rows=[c for c in CHAT if c[0]<=g][-3:]; cy=250; fn,fm=F("Bold",28),F("Medium",28)
        for i,(t0,u,col,m) in enumerate(rows):
            age=g-t0; pop=min(1,age/0.18); a=int(255*(0.55+0.45*(i+1)/len(rows)))*1
            tw=d.textlength(u+"  ",font=fn)+d.textlength(m,font=fm); w=int(tw+86); cx=1044-w; off=int((1-pop)*40)
            pill(d,(cx+off,cy,cx+w+off,cy+62),(16,12,26,int(a*0.72*pop))); d.ellipse((cx+10+off,cy+10,cx+52+off,cy+52),fill=col+(int(a*pop),))
            d.text((cx+22+off,cy+13),u[0].upper(),font=fn,fill=(20,12,30,int(a*pop))); d.text((cx+64+off,cy+15),u+"  ",font=fn,fill=col+(int(a*pop),)); d.text((cx+64+off+d.textlength(u+"  ",font=fn),cy+15),m,font=fm,fill=(255,255,255,int(a*pop))); cy+=74
    # pinned message from Lena (the stakes) 2.85-4.9, slides up from below
    if 3.68<=g<5.4:
        k=min(1,(g-3.68)/0.2); k=1-(1-k)**3; fade=min(1,(5.4-g)/0.25); y0=int(1330+(1-k)*120); a=int(255*fade)
        d.rounded_rectangle((60,y0,1020,y0+230),radius=34,fill=(18,14,32,int(235*fade)),outline=(255,63,176,a),width=5)
        d.ellipse((92,y0+24,132,y0+64),fill=(255,63,176,a)); d.text((150,y0+22),"PINNED  ·  LENA CHO",font=F("Bold",30),fill=(255,150,215,a))
        d.text((92,y0+82),"HEADLINE SHOW IN 30 DAYS.",font=F("ExtraBold",46),fill=(255,255,255,a)); d.text((92,y0+142),"NO GUITAR = NO HEADLINE SHOW",font=F("ExtraBold",46),fill=(255,214,70,a))
    cap=None
    if 3.1<=g<3.95: cap=("ANYTHING",3.1)
    elif 9.85<=g<10.8: cap=("THAT'S MY VAN?!",9.85)
    elif 10.8<=g<11.4: cap=("GIG IS DRIVING",10.8)
    if cap:
        txt,t0=cap; pop=min(1,(g-t0)/0.12); sc=0.8+0.2*(1-(1-pop)**2); size=150
        while d.textlength(txt,font=F("ExtraBold",size))>900: size-=6
        size=int(size*sc); font=F("ExtraBold",size); tw=d.textlength(txt,font=font); d.text(((W-tw)/2,1560),txt,font=font,fill=(255,63,176,255),stroke_width=16,stroke_fill=(26,13,51,255))
    return Image.alpha_composite(im.convert('RGBA'),ov).convert('RGB')
import glob
files=sorted(glob.glob(f'{FR}/f*.png')); print(len(files),'rendered frames (12 fps)')
for k,p in enumerate(files):
    n=int(os.path.basename(p)[1:5]); draw(Image.open(p),n/24).save(f'{OUT}/{k:04d}.png')
subprocess.run(['ffmpeg','-y','-v','error','-framerate','12','-i',f'{OUT}/%04d.png','-i','audio_final.wav','-vf','framerate=fps=24:interp_start=0:interp_end=255:scene=100','-c:v','libx264','-pix_fmt','yuv420p','-crf','17','-preset','medium','-c:a','aac','-b:a','192k','-t','12','../output/dex_test_v4_12fps_blend.mp4'])
print('done')
