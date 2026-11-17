#!/usr/bin/env python3
import argparse, json, pathlib, re, shutil, subprocess, sys, os
from fractions import Fraction

def run(args):
    environment = {key: value for key, value in os.environ.items() if key in {'PATH','SystemRoot','WINDIR','TEMP','TMP','TMPDIR','LANG','LC_ALL'}}
    return subprocess.run(args, text=True, capture_output=True, timeout=180, check=False, env=environment)

def audit(path, expected, allowed=None, tools=None):
    allowed=allowed or {}; checks=[]
    tools = tools or {name: shutil.which(name) for name in ['ffmpeg', 'ffprobe']}
    def invoke(args):
        args = [tools[args[0]], *args[1:]]
        return run(args)
    def add(name,status,observed,expected=None):
        checks.append(dict(id=name,status=status,observed=observed,expected=expected))
    if not pathlib.Path(path).is_file():
        add('file','fail','missing','existing file'); return checks
    for cmd in ['ffmpeg','ffprobe']:
        if not tools.get(cmd): add(cmd,'blocked','not installed','installed')
    if checks:return checks
    p=invoke(['ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(path)])
    if p.returncode:
        add('probe','fail',p.stderr[-1000:],'valid media');return checks
    d=json.loads(p.stdout); vs=next((x for x in d.get('streams',[]) if x['codec_type']=='video'),None); au=next((x for x in d.get('streams',[]) if x['codec_type']=='audio'),None)
    if not vs:
        add('video','fail','no stream','video stream');return checks
    for key, observed in [('width',vs.get('width')),('height',vs.get('height')),('frames',int(vs['nb_read_frames']) if str(vs.get('nb_read_frames','')).isdigit() else None),('codec',vs.get('codec_name'))]:
        if key in expected:add(key,'pass' if observed==expected[key] else 'fail',observed,expected[key])
    if 'fps' in expected:
        a=Fraction(vs['avg_frame_rate']); b=Fraction(str(expected['fps'])); add('fps','pass' if a==b else 'fail',str(a),str(b))
    if 'duration' in expected:
        a=float(d['format']['duration']); b=float(expected['duration']); tol=1/float(Fraction(str(expected.get('fps','30')))); add('duration','pass' if abs(a-b)<=tol+1e-6 else 'fail',a,{'seconds':b,'tolerance':tol})
    if expected.get('audio_required'):add('audio_stream','pass' if au else 'fail',bool(au),True)
    elif expected.get('audio_forbidden'):add('audio_stream','fail' if au else 'pass',bool(au),False)
    if au and 'sample_rate' in expected:add('sample_rate','pass' if int(au['sample_rate'])==expected['sample_rate'] else 'fail',int(au['sample_rate']),expected['sample_rate'])
    decode=invoke(['ffmpeg','-v','error','-xerror','-i',str(path),'-map','0:v:0','-map','0:a?','-f','null','-']);add('decode','pass' if decode.returncode==0 else 'fail',decode.stderr[-1000:] or 'decoded','no decode errors')
    scan=invoke(['ffmpeg','-hide_banner','-nostats','-i',str(path),'-an','-vf','blackdetect=d=0.25:pix_th=0.10,freezedetect=n=-50dB:d=0.6','-f','null','-'])
    def exempt(a,b,key):return any(a>=float(x[0])-.05 and b<=float(x[1])+.05 for x in allowed.get(key,[]))
    if scan.returncode:add('visual_scan','blocked',scan.stderr[-1000:],'completed')
    else:
        black=[(float(a),float(b)) for a,b in re.findall(r'black_start:([\d.]+)\s+black_end:([\d.]+)',scan.stderr)]
        starts=[float(a) for a in re.findall(r'freeze_start:\s*([\d.]+)',scan.stderr)]; ends=[float(a) for a in re.findall(r'freeze_end:\s*([\d.]+)',scan.stderr)]
        duration=float(d['format'].get('duration',0));freeze=[(s,next((e for e in ends if e>=s),duration)) for s in starts]
        for key, intervals in [('black',black),('freeze',freeze)]:
            unexplained=[x for x in intervals if not exempt(*x,key)]; add(key,'review' if unexplained else 'pass',{'intervals':intervals,'unexplained':unexplained},'no unexplained intervals')
    if au:
        target=float(expected.get('lufs_target',-14)); peak=float(expected.get('true_peak_max',-1)); normtarget=max(-70,min(-5,target)); normpeak=max(-9,min(0,peak))
        a=invoke(['ffmpeg','-hide_banner','-nostats','-i',str(path),'-vn','-af',f'silencedetect=n=-50dB:d=0.5,loudnorm=I={normtarget}:TP={normpeak}:LRA=11:print_format=json','-f','null','-'])
        if a.returncode:add('audio_scan','blocked',a.stderr[-1000:],'completed')
        else:
            starts=[float(x) for x in re.findall(r'silence_start: ([\d.]+)',a.stderr)]; ends=[float(x) for x in re.findall(r'silence_end: ([\d.]+)',a.stderr)]; dur=float(d['format']['duration']); intervals=[(s,next((e for e in ends if e>=s),dur)) for s in starts]; unexplained=[x for x in intervals if not exempt(*x,'silence')];add('silence','review' if unexplained else 'pass',{'intervals':intervals,'unexplained':unexplained},'no unexplained silence')
            match=re.search(r'\{\s*"input_i".*?\}',a.stderr,re.S)
            if match:
                q=json.loads(match.group()); measured=float(q['input_i']); tp=float(q['input_tp']); import math
                add('loudness','pass' if 'lufs_target' in expected and math.isfinite(measured) and abs(measured-target)<=expected.get('lufs_tolerance',1) else 'fail' if 'lufs_target' in expected else 'measured',q['input_i'],expected.get('lufs_target'))
                add('true_peak','pass' if tp<=peak else 'fail',q['input_tp'],peak)
            else:add('loudness','blocked','meter output missing','measurement')
    add('creative_review','review','not automatically measured','visual/audio reviewer required')
    return checks

def main():
    p=argparse.ArgumentParser();p.add_argument('video',type=pathlib.Path);p.add_argument('--profile',required=True,type=pathlib.Path);p.add_argument('--output',type=pathlib.Path);args=p.parse_args();profile=json.loads(args.profile.read_text());checks=audit(args.video,profile['expected'],profile.get('allowed')); report={'file':args.video.name,'checks':checks,'technical_status':'fail' if any(x['status']=='fail' for x in checks) else 'blocked' if any(x['status']=='blocked' for x in checks) else 'review' if any(x['status']=='review' and x['id']!='creative_review' for x in checks) else 'pass','release_status':'requires creative review'};out=json.dumps(report,indent=2,allow_nan=False)+'\n';print(out,end='');
    if args.output:args.output.write_text(out)
    return 0 if report['technical_status']=='pass' else 2
if __name__=='__main__':sys.exit(main())
