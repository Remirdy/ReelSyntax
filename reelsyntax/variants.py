import copy
from fractions import Fraction
import os
from pathlib import Path
import re
import shutil
import tempfile

from ReelSyntax_Skills.tools.registry import atomic_json, canonical, contained_path, digest, read_json
from .ingest import asset_hashes
from .project import fields, validate

TARGETS = {
    'youtube': ('16:9', '8M', -14, 0.05),
    'shorts': ('9:16', '8M', -14, 0.12),
    'tiktok': ('9:16', '6M', -14, 0.14),
    'reels': ('9:16', '6M', -14, 0.14),
    'x': ('16:9', '5M', -16, 0.06),
    'linkedin': ('1:1', '6M', -16, 0.08),
}
LANGUAGES = {
    'en': 'eng',
    'tr': 'tur',
    'de': 'deu',
    'es': 'spa',
    'fr': 'fra',
    'pt': 'por',
    'fi': 'fin',
    'pl': 'pol',
    'vi': 'vie',
    'ar': 'ara',
    'zh': 'zho',
    'ja': 'jpn',
    'ko': 'kor',
}


def set_text(plan, values):
    if not isinstance(values, dict):
        raise ValueError('Expected an object of scene.field text overrides')
    for key, value in values.items():
        scene_id, _, field = key.rpartition('.')
        if field not in ('heading', 'subheading', 'kicker') or not isinstance(value, str):
            raise ValueError(f'Unknown text override {key}')
        matches = [
            s for s in plan['scenes'] if (not scene_id or scene_id == s['id']) and field in s['params']
        ]
        if not matches:
            raise ValueError(f'No matching scene field for {key}')
        for scene in matches:
            scene['params'][field] = value


def aspect_size(width, height, aspect):
    if not isinstance(aspect, str) or not re.fullmatch(r'[1-9]\d{0,2}:[1-9]\d{0,2}', aspect):
        raise ValueError('Expected an aspect ratio such as 9:16')
    ratio = Fraction(*map(int, aspect.split(':')))
    scale = max(width, height) // (2 * max(ratio.numerator, ratio.denominator))
    return 2 * scale * ratio.numerator, 2 * scale * ratio.denominator


def materialize(root, original, *, aspect=None, locale=None, values=None, target=None, brand=None):
    from .render import check_locks

    plan = copy.deepcopy(original)
    if target:
        if target not in TARGETS:
            raise ValueError('Unknown delivery target')
        aspect = aspect or TARGETS[target][0]
        plan['delivery'] = {**plan.get('delivery', {}), 'target': target}
    if aspect:
        out = plan['output']
        out['width'], out['height'] = aspect_size(out['width'], out['height'], aspect)
    if locale:
        if not isinstance(locale, str) or not re.fullmatch(r'[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*', locale):
            raise ValueError('Invalid locale')
        language = LANGUAGES.get(locale.split('-')[0])
        if language is None:
            raise ValueError('Unsupported stream language for locale ' + locale)
        set_text(plan, read_json(contained_path(root, f'strings.{locale}.json'), max_bytes=200000))
        plan['delivery'] = {**plan.get('delivery', {}), 'language': language}
    if values:
        set_text(plan, values)
    if brand:
        kit = read_json(contained_path(root, brand), max_bytes=16000)
        fields(kit, {'foreground', 'background', 'accent', 'logo', 'font', 'margin'}, set(), 'brand')
        for scene in plan['scenes']:
            for key in ('background', 'foreground', 'accent'):
                if key in kit and (
                    key == 'background' or scene['recipe'] not in ('footage', 'layer-stack', 'shape-field')
                ):
                    scene['params'][key] = kit[key]
        plan['delivery'] = {
            **plan.get('delivery', {}),
            **{k: kit[k] for k in ('logo', 'font', 'margin') if k in kit},
        }
    plan.pop('$schema', None)
    validate(plan)
    locked = check_locks(root, plan)
    if locked and plan.get('delivery', {}) != original.get('delivery', {}):
        raise ValueError('Delivery settings would alter an approved scene')
    assets = asset_hashes(root, plan)
    locks = {}
    for name in ('scene-locks', 'roi-locks-draft', 'roi-locks-production', 'roi-locks-hero'):
        rel = f'.reelsyntax/{name}.json'
        path = contained_path(root, rel, must_exist=False)
        if path.exists():
            locks[rel] = read_json(path)
    key = digest(canonical([plan, assets, locks]))
    destination = contained_path(root, f'.reelsyntax/variants/{key}', must_exist=False)
    if destination.exists():
        if (
            read_json(contained_path(destination, 'reel.json')) != plan
            or asset_hashes(destination, plan) != assets
        ):
            raise ValueError('Stored variant has changed')
        if any(read_json(contained_path(destination, rel)) != record for rel, record in locks.items()):
            raise ValueError('Stored variant approvals have changed')
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as directory:
        staged = Path(directory) / 'project'
        staged.mkdir()
        for rel in assets:
            path = contained_path(staged, rel, must_exist=False)
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(contained_path(root, rel), path)
        if asset_hashes(staged, plan) != assets:
            raise ValueError('Source changed while preparing variant')
        atomic_json(staged / 'reel.json', plan)
        for rel, record in locks.items():
            atomic_json(contained_path(staged, rel, must_exist=False), record)
        try:
            os.rename(staged, destination)
        except OSError:
            if not destination.is_dir():
                raise
    return destination


def render_variants(args, options):
    from .project import load
    from .render import render

    root, plan, _ = load(args.project)
    values = {}
    for change in args.set:
        key, sep, value = change.partition('=')
        if not sep or key in values:
            raise ValueError('Expected a unique field=value for --set')
        values[key] = value
    jobs = [
        {
            'aspect': aspect,
            'target': args.target,
            'locale': args.locale,
            'values': values,
            'brand': args.brand,
        }
        for aspect in (args.aspect.split(',') if args.aspect else [None])
    ]
    if args.queue:
        if any((args.aspect, args.target, args.locale, values, args.brand)):
            raise ValueError('Specify variant settings inside the queue')
        jobs = read_json(contained_path(root, args.queue), max_bytes=200000)
    if not isinstance(jobs, list) or not 1 <= len(jobs) <= 64:
        raise ValueError('Expected 1–64 delivery jobs')
    prepared = []
    for job in jobs:
        fields(job, {'aspect', 'target', 'locale', 'values', 'brand'}, set(), 'delivery job')
        prepared.append(materialize(root, plan, **job))
    results = []
    for directory in dict.fromkeys(prepared):
        result = render(directory, **options)
        results.append(
            {
                'project': directory.relative_to(root).as_posix(),
                'artifact': result['artifact'],
                'frames': result['frames'],
                'profile': args.profile,
            }
        )
    return {'deliveries': results}


def apply_brand(directory, count, delivery, root):
    from PIL import Image, ImageOps

    target = delivery.get('target')
    margin = delivery.get('margin', TARGETS[target][3] if target else 0)
    if not margin and 'logo' not in delivery:
        return
    logo = None
    if 'logo' in delivery:
        with Image.open(contained_path(root, delivery['logo'])) as source:
            logo = source.convert('RGBA')
    for index in range(count):
        path = directory / f'{index:06d}.png'
        with Image.open(path) as original:
            frame = original.convert('RGB')
        w, h = frame.size
        dx, dy = round(w * margin), round(h * margin)
        if dx or dy:
            fitted = frame.resize((w - 2 * dx, h - 2 * dy), Image.Resampling.LANCZOS)
            frame = Image.new('RGB', (w, h), frame.getpixel((0, 0)))
            frame.paste(fitted, (dx, dy))
        if logo is not None:
            mark = ImageOps.contain(logo, (max(1, w // 8), max(1, h // 8)))
            frame.paste(mark, (w - dx - mark.width, dy), mark)
        frame.save(path)
