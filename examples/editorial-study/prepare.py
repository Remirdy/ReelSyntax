import argparse
from pathlib import Path
import shutil

from PIL import Image, ImageDraw
from reelsyntax.media import executable, run


parser = argparse.ArgumentParser(description='Prepare local source assets from an existing rendered Aperture master')
parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1] / 'aperture-film/output/hero.mp4')
args = parser.parse_args()
source = args.source.resolve(strict=True)
assets = Path(__file__).resolve().parent / '.reelsyntax/inputs'
assets.mkdir(parents=True, exist_ok=True)
destination = assets / 'source.mp4'
if destination.exists():
    raise SystemExit('Example inputs already exist; keep or move them before preparing another source')
shutil.copyfile(source, destination)
run([executable('ffmpeg'), '-v', 'error', '-nostdin', '-y', '-i', str(destination), '-vf', 'select=eq(n\\,126),scale=480:270', '-frames:v', '1', str(assets / 'still.png')])
frame = Image.new('RGBA', (640, 360))
draw = ImageDraw.Draw(frame)
draw.rectangle((70, 35, 570, 325), outline=(189, 154, 102, 190), width=2)
frame.save(assets / 'frame.png')
print('Prepared local source footage and two raster layers; source audio remains in source.mp4.')
