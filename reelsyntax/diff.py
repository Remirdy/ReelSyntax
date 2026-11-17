import math
from pathlib import Path

from ReelSyntax_Skills.tools.registry import atomic_json, contained_path, read_json
from .project import load


def _image_metrics(img_a, img_b) -> dict:
    from PIL import Image
    if img_a.size != img_b.size:
        img_b = img_b.resize(img_a.size, Image.Resampling.LANCZOS)
    bytes_a = img_a.convert('RGB').tobytes()
    bytes_b = img_b.convert('RGB').tobytes()
    n = len(bytes_a)
    abs_sum = 0
    sq_sum = 0
    for a, b in zip(bytes_a, bytes_b):
        d = a - b
        abs_sum += abs(d)
        sq_sum += d * d
    mae = abs_sum / max(1, n)
    mse = sq_sum / max(1, n)
    psnr = 99.0 if mse < 1e-9 else round(10.0 * math.log10((255.0 * 255.0) / mse), 3)
    return {'mae_rgb8': round(mae, 4), 'psnr_db': psnr, 'identical': sq_sum == 0}


def compare_profiles(project_dir: str | Path, base_profile: str = 'draft', target_profile: str = 'production') -> dict:
    from PIL import Image, ImageChops, ImageOps
    root, plan, _ = load(project_dir)
    base_manifest = read_json(contained_path(root, f'output/{base_profile}-manifest.json'))
    target_manifest = read_json(contained_path(root, f'output/{target_profile}-manifest.json'))

    comparisons = []
    strip_rows = []
    for base_rel, target_rel in zip(base_manifest.get('snapshots', []), target_manifest.get('snapshots', [])):
        with Image.open(root / base_rel) as im_a, Image.open(root / target_rel) as im_b:
            metrics = _image_metrics(im_b, im_a)
            comparisons.append({'base': base_rel, 'target': target_rel, **metrics})
            ta = ImageOps.contain(im_a.convert('RGB'), (320, 180))
            tb = ImageOps.contain(im_b.convert('RGB'), (320, 180))
            diff_vis = ImageChops.difference(ta, tb).point(lambda p: min(255, p * 4))
            strip_rows.append((ta, tb, diff_vis))

    diff_sheet_rel = None
    if strip_rows:
        sheet = Image.new('RGB', (960, 180 * len(strip_rows)), '#181a1d')
        for row_idx, (ta, tb, td) in enumerate(strip_rows):
            y = row_idx * 180
            sheet.paste(ta, (0, y))
            sheet.paste(tb, (320, y))
            sheet.paste(td, (640, y))
        sheet_path = contained_path(root, f'review/diff-{base_profile}-vs-{target_profile}.png', must_exist=False)
        sheet_path.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(sheet_path)
        diff_sheet_rel = sheet_path.relative_to(root).as_posix()

    sound_a = base_manifest.get('sound') or {}
    sound_b = target_manifest.get('sound') or {}
    rms_delta = None
    if sound_a.get('rms_dbfs') is not None and sound_b.get('rms_dbfs') is not None:
        rms_delta = round(sound_b['rms_dbfs'] - sound_a['rms_dbfs'], 4)

    report = {
        'schema_version': 1,
        'project': plan['id'],
        'base_profile': base_profile,
        'target_profile': target_profile,
        'plan_changed': base_manifest.get('plan_sha256') != target_manifest.get('plan_sha256'),
        'dimensions': [base_manifest.get('output_settings'), target_manifest.get('output_settings')],
        'bytes': [base_manifest.get('bytes'), target_manifest.get('bytes')],
        'audio_rms_delta_db': rms_delta,
        'sample_comparisons': comparisons,
        'diff_contact_sheet': diff_sheet_rel,
    }
    atomic_json(contained_path(root, f'review/diff-{base_profile}-vs-{target_profile}.json', must_exist=False), report)
    return report
