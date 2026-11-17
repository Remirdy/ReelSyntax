#!/usr/bin/env python3
"""Original, deterministic motion-design fixture. Requires Pillow, FFmpeg and a local font."""
import argparse, math, pathlib, shutil, subprocess, tempfile, wave, struct
from PIL import Image, ImageDraw, ImageFont
W,H,FPS,N=960,540,30,180

def smooth(x):
    x=max(0,min(1,x));return x*x*(3-2*x)

def main():
    p=argparse.ArgumentParser();p.add_argument('--font',required=True,type=pathlib.Path);p.add_argument('--output',required=True,type=pathlib.Path);args=p.parse_args()
    output=args.output.resolve();output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists(): raise SystemExit('Output exists; use a new path.')
    if not shutil.which('ffmpeg'):raise SystemExit('FFmpeg required')
    fonts={s:ImageFont.truetype(str(args.font),s) for s in (14,17,20,38,60,76)}
    bg=Image.new('RGB',(W,H)); px=bg.load()
    for y in range(H):
        for x in range(W):
            a=max(0,1-math.hypot((x-650)/720,(y-270)/500));px[x,y]=(int(15+14*a),int(22+17*a),int(30+21*a))
    white='#f1eee6'; muted='#9ca8ac'; accent='#edb478'
    with tempfile.TemporaryDirectory() as tmp:
        tmp=pathlib.Path(tmp)
        for i in range(N):
            t=i/FPS; img=bg.copy();d=ImageDraw.Draw(img); u=t/6
            d.line((58,56,902,56),fill='#39434a',width=1); d.line((58,479,902,479),fill='#39434a',width=1)
            d.text((58,30),'REELSYNTAX  /  MOTION STUDIES',font=fonts[14],fill=muted);d.text((902,30),f'{i+1:03d} / {N}',font=fonts[14],fill=muted,anchor='ra')
            cx,cy=677,267; tilt=.24*math.sin(t*.8); scale=.85+.15*smooth(t/1.1)
            # Parametric wire rings with depth/occlusion order; aesthetic and deterministic test fixture.
            for k in range(12):
                r=65+k*9; yoff=(k-5.5)*8; phase=t*.68+k*.13
                pts=[]
                for j in range(121):
                    a=j*math.tau/120; xx=math.cos(a+phase)*r*scale; yy=math.sin(a+phase)*r*(.46+.1*math.sin(t))*scale
                    pts.append((cx+xx*math.cos(tilt)-yy*math.sin(tilt),cy+yoff+xx*math.sin(tilt)+yy*math.cos(tilt)))
                for j in range(120):
                    q=(math.sin(j*math.tau/120+phase)+1)/2; c=(int(66+171*q),int(83+97*q),int(89+31*q));d.line((pts[j],pts[j+1]),fill=c,width=2 if k%4 else 3)
            stage=0 if t<2 else 1 if t<4 else 2; local=t-2*stage; fade=smooth(local/.28) if stage else smooth((local+.15)/.4)
            offset=int(18*(1-fade)); lines=[('Form','in motion.'),('Time','by design.'),('Every frame','intentional.')][stage]
            color=tuple(round(a+(b-a)*fade) for a,b in zip((23,31,39),(241,238,230)))
            d.text((58+offset,153),f'0{stage+1}  /  '+['GEOMETRY','TIMING','COMPOSITION'][stage],font=fonts[17],fill=accent)
            for n,txt in enumerate(lines):d.text((56+offset,192+n*66),txt,font=fonts[60],fill=color)
            d.text((58,350),'A deterministic, code-rendered study.',font=fonts[20],fill=muted)
            d.text((58,496),'STUDY 001    /    FRAME-DRIVEN ANIMATION',font=fonts[14],fill=muted)
            d.line((700,506,902,506),fill='#39434a',width=2);d.line((700,506,700+202*u,506),fill=accent,width=2)
            img.save(tmp/f'{i:05d}.png')
        # Original simple synthesized cue; no music samples or external services.
        with wave.open(str(tmp/'cue.wav'),'wb') as f:
            f.setparams((1,2,48000,0,'NONE','not compressed')); data=bytearray()
            for j in range(48000*6):
                t=j/48000; env=min(1,(t+.02)/.12,(6-t)/.18); z=.13*math.sin(math.tau*110*t)+.055*math.sin(math.tau*165*t+.3*math.sin(t*3))+.035*math.sin(math.tau*220*t)
                for hit in (.1,2.02,4.02):
                    dt=t-hit
                    if 0<=dt<.55:z+=.11*math.exp(-7*dt)*math.sin(math.tau*(240*dt-60*dt*dt))
                data+=struct.pack('<h',max(-32767,min(32767,int(z*env*32767))))
            f.writeframes(data)
        subprocess.run(['ffmpeg','-v','error','-n','-framerate','30','-i',str(tmp/'%05d.png'),'-i',str(tmp/'cue.wav'),'-c:v','libx264','-preset','fast','-crf','17','-pix_fmt','yuv420p','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-af','loudnorm=I=-14:TP=-1.5:LRA=7,aresample=48000','-c:a','aac','-b:a','192k','-ar','48000','-t','6','-movflags','+faststart',str(output)],check=True)
if __name__=='__main__':main()
