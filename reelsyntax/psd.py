import json
import os
from pathlib import Path
import tempfile

from ReelSyntax_Skills.tools.registry import atomic_json, contained_path
from .gateway import resolve_integration
from .media import run
from .project import load


PSD_EXTRACT = r'''
const fs = require('fs');
const path = require('path');
const {createRequire} = require('module');
const [moduleRoot, source, output] = process.argv.slice(1);
const localRequire = createRequire(path.join(moduleRoot, 'package.json'));
const {readPsd, initializeCanvas} = localRequire('ag-psd');
let allocatedPixels = 0;
initializeCanvas(() => {throw new Error('PSD operation requires unsupported canvas rasterization');}, undefined,
  (width,height) => {
    allocatedPixels += width * height;
    if (width < 1 || height < 1 || width > 16384 || height > 16384 || allocatedPixels > 33554432) throw new Error('PSD exceeds decoded pixel budget');
    return {width,height,data:new Uint8ClampedArray(width*height*4)};
  });
const sharp = localRequire('sharp');
async function main() {
  const psd = readPsd(fs.readFileSync(source), {useImageData:true, skipCompositeImageData:true, skipThumbnail:true});
  if (psd.width * psd.height > 16777216) throw new Error('PSD exceeds 16 megapixel canvas budget');
  const layers = [];
  let pixels = 0;
  function walk(nodes) {
    for (const layer of nodes || []) {
      if (layer.hidden || layer.opacity === 0) continue;
      const blend = layer.blendMode || 'normal';
      if (!['normal','pass through'].includes(blend) || layer.mask || layer.realMask || layer.vectorMask || layer.effects || layer.adjustment || layer.clipping || (layer.fillOpacity !== undefined && layer.fillOpacity !== 1)) {
        throw new Error(`Unsupported PSD compositing on layer '${layer.name || 'unnamed'}'; rasterize its appearance before ingest`);
      }
      if (layer.children) {
        if (layer.opacity !== undefined && layer.opacity !== 1) throw new Error('PSD group opacity requires rasterization');
        walk(layer.children);
        continue;
      }
      const data = layer.imageData;
      if (!data || !data.width || !data.height) continue;
      pixels += data.width * data.height;
      if (pixels > 33554432 || layers.length >= 128) throw new Error('PSD exceeds decoded layer budget');
      if (data.data.length !== data.width * data.height * 4) throw new Error('PSD layer is not 8-bit RGBA');
      layers.push({name:(layer.name || 'Layer').replace(/[\x00-\x1f]/g,' ').slice(0,120), x:layer.left || 0, y:layer.top || 0, width:data.width, height:data.height, opacity:layer.opacity === undefined ? 1 : layer.opacity, data});
    }
  }
  walk(psd.children);
  if (!layers.length) throw new Error('PSD has no supported visible raster layers');
  const result = [];
  for (let index=0; index<layers.length; index++) {
    const {data,...layer} = layers[index];
    const file = `${String(index).padStart(3,'0')}.png`;
    await sharp(Buffer.from(data.data.buffer, data.data.byteOffset, data.data.byteLength), {raw:{width:data.width,height:data.height,channels:4}}).png().toFile(path.join(output,file));
    result.push({...layer, file});
  }
  process.stdout.write(JSON.stringify({width:psd.width,height:psd.height,layers:result,order:'bottom-to-top'}));
}
main().catch(error => {process.stderr.write(error.message); process.exitCode=1;});
'''


def ingest_psd(project, source: str, destination: str, timeout=60):
    root, _, _ = load(project)
    src = contained_path(root, source)
    target = contained_path(root, destination, must_exist=False)
    if target.exists():
        raise ValueError('PSD destination must be a new directory; existing assets are preserved')
    if src.stat().st_size > 64 * 1024 * 1024:
        raise ValueError('PSD exceeds 64 MiB input budget')
    with src.open('rb') as stream:
        header = stream.read(26)
    if len(header) != 26 or header[:6] != b'8BPS\x00\x01' or header[22:26] != b'\x00\x08\x00\x03':
        raise ValueError('PSD ingest supports 8-bit RGB PSD files; convert PSB/CMYK/16-bit sources explicitly')
    height, width = int.from_bytes(header[14:18], 'big'), int.from_bytes(header[18:22], 'big')
    if not 1 <= width <= 16384 or not 1 <= height <= 16384 or width * height > 16777216:
        raise ValueError('PSD exceeds canvas dimension/pixel budget')
    integration = resolve_integration('after-effects')
    command = integration['command']
    if not command or not integration['cwd']:
        raise ValueError('PSD ingest requires an existing optional AfterEffectsMCP Node runtime with ag-psd and sharp; no installation occurs')
    module_root = Path(integration['env_overrides'].get('NODE_PATH', str(Path(integration['cwd']) / 'node_modules'))).parent
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='psd-', dir=target.parent) as tmp:
        payload = json.loads(run([command[0], '--max-old-space-size=512', '-e', PSD_EXTRACT, str(module_root), str(src), tmp], timeout=timeout).stdout)
        layers = [{**{k: v for k, v in layer.items() if k != 'file'}, 'source': (target / layer['file']).relative_to(root).as_posix()} for layer in payload['layers']]
        report = {'source': source, 'dimensions': [payload['width'], payload['height']], 'order': payload['order'], 'params': {'layers': layers}, 'limitations': 'raster appearances and normal alpha compositing; masks, effects, adjustments and non-normal blend modes require explicit rasterization'}
        atomic_json(Path(tmp) / 'layers.json', report)
        staged = Path(tmp) / 'delivery'
        staged.mkdir()
        for file in list(Path(tmp).iterdir()):
            if file.is_file():
                os.replace(file, staged / file.name)
        os.replace(staged, target)
    return {'artifact': (target / 'layers.json').relative_to(root).as_posix(), 'layers': len(layers), 'dimensions': report['dimensions'], 'source_modified': False}
