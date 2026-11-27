import json, subprocess, glob, os, re, numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont
F=lambda s: ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Bold.otf", s)
os.makedirs('../output/overhaul',exist_ok=True)
def label(im,txt):
    im=im.convert('RGB'); d=ImageDraw.Draw(im); w=d.textlength(txt,font=F(22)); d.rounded_rectangle((8,8,w+28,48),radius=14,fill=(16,12,26)); d.text((18,14),txt,font=F(22),fill=(255,255,255)); return im
def video(frames,labels,out,audio=None,fps=12,maxdur=None):
    d=f'/tmp/asm_{os.path.basename(out)}'; os.makedirs(d,exist_ok=True)
    for f in glob.glob(d+'/*'): os.remove(f)
    for i,(p,l) in enumerate(zip(frames,labels)): label(Image.open(p),l).save(f'{d}/{i:05d}.png')
    cmd=['ffmpeg','-y','-v','error','-framerate',str(fps),'-i',f'{d}/%05d.png']
    if audio: cmd+=['-i',audio]
    cmd+=['-vf','framerate=fps=24:interp_start=0:interp_end=255:scene=100','-c:v','libx264','-pix_fmt','yuv420p','-crf','18']
    if audio: cmd+=['-c:a','aac','-b:a','192k','-shortest']
    subprocess.run(cmd+[out]); return out
# reel
T=json.load(open('/tmp/reel.json')); segs=json.load(open('reel_segments.json'))
names=[it['name'] for it in T['items']]; lab=[]
for n,s0,c in segs: lab+= [n]*c
fr=[(f'/tmp/out_reel_a/{n}.png' if os.path.exists(f'/tmp/out_reel_a/{n}.png') else f'/tmp/out_reel_b/{n}.png') for n in names]
a,sr=sf.read('reel_audio_raw.wav'); n=int(len(names)/12*sr); a=a[:n] if len(a)>=n else np.pad(a,(0,n-len(a)))
sf.write('/tmp/reel_audio.wav',a.astype(np.float32),sr)
r=subprocess.run(['ffmpeg','-i','/tmp/reel_audio.wav','-af','loudnorm=I=-14:TP=-1.5:print_format=json','-f','null','-'],capture_output=True,text=True).stderr
g=-14-float(json.loads(r[r.rindex('{'):])['input_i']); subprocess.run(['ffmpeg','-y','-v','error','-i','/tmp/reel_audio.wav','-af',f'volume={g}dB,alimiter=limit=0.9:level=false','/tmp/reel_audio14.wav'])
video(fr,lab,'../output/overhaul/action_reel_synced.mp4','/tmp/reel_audio14.wav')
# phone + walk/jog
P=json.load(open('/tmp/p12.json'))['items']
p1=[f'/tmp/out_p12/{it["name"]}.png' for it in P if it['name'].startswith('p1_')]
l1=['Phone grip: raising the phone to his face']*36+['Walking with the phone in hand (side)']*30
video(p1,l1,'../output/overhaul/phone_grip.mp4')
p2=[f'/tmp/out_p12/{it["name"]}.png' for it in P if it['name'].startswith('p2_')]
names2=[]
for m in ('Walk','Jog'):
    for v in ('side','front'): names2+= [f'{m}, {v} view']*28
video(p2,names2[:len(p2)],'../output/overhaul/walk_and_jog.mp4')
print('videos done')
