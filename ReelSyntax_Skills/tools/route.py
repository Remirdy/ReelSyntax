#!/usr/bin/env python3
import argparse
import collections
import difflib
import json
import math
from pathlib import Path
import re
import sys
import unicodedata

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ReelSyntax_Skills.tools.registry import ROOT, STAGES, load_index, load_skill, skill_path, validate_rows

STAGE_ORDER = ('plan', 'ingest', 'build', 'edit', 'render', 'review', 'export', 'operate')
STOP = set(
    'a an and are as at be by for from in is it of on or the to use using with video create make please want me my this that '
    'bir ve ile icin bana yap olustur video olsun olan olarak bu su gore then sonra ardindan forbidden istemiyorum olmasin yasak without no'.split()
)
LOCK_CAMERA = (
    'no camera movement', 'locked camera', 'camera locked', 'static camera',
    'kamera sabit', 'kamera hareket etmesin', 'kamera hareketi olmasın', 'kamerayı oynatma', 'no zoom',
)
LOCK_TEXT = ('no text', 'without text', 'textless', 'yazı olmasın', 'yazısız', 'metin olmasın', 'metinsiz')
CAMERA_MOVES = {
    'slow-dolly', 'tracking-shot', 'orbit-camera', 'crane-shot', 'whip-pan', 'handheld-motion',
    'dolly-zoom', 'aerial-shot', 'pov-camera', 'match-zoom', 'seamless-camera-bridge',
    'camera-inertia-rig', 'procedural-camera-shake',
}
TEXT_ADDITIONS = {
    'kinetic-typography', 'word-reveal', 'character-reveal', 'text-mask-reveal', 'text-on-path',
    'extruded-type', 'lower-thirds', 'word-timed-captions', 'end-card', 'variable-font-animation',
}
STEMS = {
    'kameras': 'kamera', 'schwarzbildern': 'schwarzbilder', 'camaras': 'camara',
    'fotogramas': 'fotograma', 'negras': 'negra', 'cameras': 'camera',
    'fixes': 'fixe', 'cadences': 'cadence', 'quadros': 'quadro', 'taxas': 'taxa',
    'kamerayi': 'kamera', 'kameranin': 'kamera', 'kameralar': 'kamera',
    'sahneleri': 'sahne', 'sahneler': 'sahne', 'sahnenin': 'sahne', 'sahneyi': 'sahne',
    'yazilari': 'yazi', 'yazilar': 'yazi',
    'seslendirmeyi': 'seslendirme', 'seslendirmenin': 'seslendirme', 'seslendirmeyle': 'seslendirme',
    'eslestir': 'eslestirme', 'eslestirin': 'eslestirme', 'eslestirmek': 'eslestirme',
    'animasyonu': 'animasyon', 'animasyonunu': 'animasyon', 'animasyonlar': 'animasyon',
    'altyazilari': 'altyazi', 'altyazilar': 'altyazi',
    'dosyalarini': 'dosya', 'dosyalari': 'dosya', 'dosyalar': 'dosya',
    'kontrolu': 'kontrol', 'kontrolleri': 'kontrol',
    'gecisleri': 'gecis', 'gecisi': 'gecis',
    'rendering': 'render', 'renders': 'render', 'rendered': 'render',
    'frames': 'frame', 'captions': 'caption', 'layers': 'layer', 'nodes': 'node',
}
SYNONYMS = {
    'glyph': ('glif',),
    'glif': ('glyph',),
    'narration': ('voiceover', 'seslendirme'),
    'seslendirme': ('voiceover',),
    'voiceover': ('seslendirme',),
    'sync': ('senkron', 'alignment'),
    'senkron': ('sync', 'alignment'),
    'senkronu': ('senkron', 'sync', 'alignment'),
    'eksik': ('missing', 'hatasi'),
}
TR_SUFFIXES = (
    'larindan', 'lerinden', 'larinin', 'lerinin', 'lariyla', 'leriyle',
    'larini', 'lerini', 'lardan', 'lerden', 'larin', 'lerin', 'larla', 'lerle',
    'sinda', 'sinde', 'sindan', 'sinden', 'masi', 'mesi', 'acak', 'ecek', 'arak', 'erek',
    'lari', 'leri', 'ndan', 'nden', 'nin', 'nun', 'yla', 'yle', 'dan', 'den', 'tan', 'ten',
    'siz', 'suz', 'lar', 'ler', 'ini', 'unu', 'ina', 'une', 'yi', 'yu', 'in', 'un', 'da', 'de', 'ta', 'te', 'la', 'le',
)
AUDIO_DRONE_PHRASES = ('cinematic drone', 'ambient drone', 'bass drone', 'audio drone', 'music drone', 'drone muzik', 'sound drone')
AERIAL_CUES = {'aerial', 'havadan', 'ucus', 'flight', 'camera', 'kamera', 'shot', 'cekim', 'gimbal'}
AUDIT_CUES = {'audit', 'detect', 'detection', 'scan', 'check', 'kontrol', 'denetim', 'tarama', 'qa', 'analiz'}


def stem_token(token):
    if token in STEMS:
        return STEMS[token]
    if len(token) >= 6:
        for suf in TR_SUFFIXES:
            if token.endswith(suf) and len(token) - len(suf) >= 4:
                root = token[:-len(suf)]
                return STEMS.get(root, root)
        for suf in ('ings', 'ing', 'ions', 'ion', 'ments', 'ment'):
            if token.endswith(suf) and len(token) - len(suf) >= 4:
                return token[:-len(suf)]
    if len(token) >= 5 and token.endswith('s') and not token.endswith(('ss', 'us', 'is', 'os', 'fps', 'lufs', 'aces')):
        cand = token[:-1]
        if cand in {'frame', 'scene', 'layer', 'node', 'shader', 'preset', 'asset', 'clip', 'track', 'stem', 'font', 'glyph', 'pass'}:
            return cand
    return token


def norm(value):
    value = unicodedata.normalize('NFKD', value.casefold().replace('ı', 'i'))
    value = ''.join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r'\bps\s+d\b', 'psd', value)
    value = re.sub(r'\bseslendirmeyle\b', 'seslendirme', value)
    return ' '.join(STEMS.get(t, t) for t in re.findall(r'[a-z0-9]+', value))


def terms(value):
    base = set()
    for raw in norm(value).split():
        if raw in STOP:
            continue
        stemmed = stem_token(raw)
        if stemmed not in STOP:
            base.add(stemmed)
    return base


def extract_negated_phrases(query):
    clean = unicodedata.normalize('NFKD', query.casefold().replace('ı', 'i'))
    clean = ''.join(c for c in clean if not unicodedata.combining(c))
    negated = []
    patterns = [
        r'\b([a-z0-9]+(?:\s+[a-z0-9]+){0,2})\s+(?:is\s+forbidden|forbidden|yasak|istemiyorum|olmasin|haric)\b',
        r'\b(?:without|no|exclude)\s+([a-z0-9]+(?:\s+[a-z0-9]+){0,2})(?:[.,;]|$|\band\b)',
    ]
    for pat in patterns:
        for match in re.finditer(pat, clean):
            phrase = norm(match.group(1))
            if phrase:
                negated.append(phrase)
    return negated


def contains(haystack, needle):
    return bool(needle) and f' {needle} ' in f' {haystack} '


def safe_path(row):
    return skill_path(row)


def split_intents(query):
    return [x.strip() for x in re.split(r'\s*(?:;|\n|\bthen\b|\bsonra\b|\bardından\b)\s*', query, flags=re.I) if x.strip()][:8]


def estimate_tokens(row):
    return row.get('estimated_tokens', row['estimated_words'] * 3) + 120


def _mcp_namespace_hint(row):
    reqs = set(row.get('requires', []))
    if 'after-effects-mcp' in reqs:
        return 'after_effects'
    if 'blender-mcp' in reqs or 'blender' in reqs:
        return 'blender'
    if row['id'] == 'blender-ae-interchange':
        return 'blender+after_effects'
    return None


def route(query, rows, limit=6, stage=None, categories=(), available=None, exclude=(), include=(), min_score=2.5, word_budget=2400, context_budget=6000, constraints=None, assets=(), preferred_engines=(), root=ROOT, include_diagnostics=False):
    if not isinstance(query, str) or len(query) > 16000:
        raise ValueError('Intent must be a string of at most 16000 characters')
    if type(limit) is not int or not 1 <= limit <= 20 or type(context_budget) is not int or not 1 <= context_budget <= 64000:
        raise ValueError('Invalid skill limit or context budget')
    if type(word_budget) is not int or not 1 <= word_budget <= 10000 or not math.isfinite(min_score) or min_score < 0:
        raise ValueError('Invalid word budget or minimum score')
    if stage is not None and stage not in STAGES:
        raise ValueError('Unknown production stage')
    validate_rows(rows, root, verify_files=False)
    constraints = constraints or {}
    if not isinstance(constraints, dict) or set(constraints) - {'no_text', 'camera_locked', 'no_audio', 'no_voice', 'no_music', 'offline', 'no_paid_services'} or any(type(v) is not bool for v in constraints.values()):
        raise ValueError('Unsupported or invalid routing constraints')
    normalized, q = norm(query), terms(query)
    negated_phrases = extract_negated_phrases(query)
    excluded, forced = set(exclude), set(include)
    known = {r['id']: r for r in rows}
    if (excluded | forced) - known.keys():
        raise ValueError('Unknown requested skill: ' + ', '.join(sorted((excluded | forced) - known.keys())))
    if categories and set(categories) - {r['category'] for r in rows}:
        raise ValueError('Unknown skill category')
    locks = dict(constraints)
    if any(contains(normalized, norm(p)) for p in LOCK_CAMERA):
        locks['camera_locked'] = True
    if any(contains(normalized, norm(p)) for p in LOCK_TEXT):
        locks['no_text'] = True
    for key, phrases in {
        'no_audio': ('no audio', 'silent video', 'sessiz video', 'ses olmasın'),
        'no_voice': ('no voice', 'no narration', 'seslendirme olmasın'),
        'no_music': ('no music', 'müzik olmasın', 'müziksiz'),
    }.items():
        if any(contains(normalized, norm(p)) for p in phrases):
            locks[key] = True
    required_locks = []
    if locks.get('camera_locked'):
        required_locks.append('locked-camera')
        excluded.update(CAMERA_MOVES)
    if locks.get('no_text'):
        required_locks.append('textless-visual-design')
        excluded.update(TEXT_ADDITIONS)
        excluded.update(r['id'] for r in rows if r['category'] == 'typography' and r['id'] != 'textless-visual-design')
    if locks.get('no_audio'):
        excluded.update(r['id'] for r in rows if r['category'] in {'audio', 'music'})
        if not (q & AUDIT_CUES):
            excluded.add('silence-audit')
    elif locks.get('no_music'):
        excluded.update(r['id'] for r in rows if r['category'] == 'music')
    if locks.get('no_voice'):
        excluded.update(sid for sid in known if any(x in sid for x in ('voiceover', 'narration', 'text-to-speech', 'tts')))
    for row in rows:
        sid = row['id']
        if sid in forced or sid in required_locks:
            continue
        row_phrases = [norm(sid), *(norm(a) for a in row['aliases'])]
        if any(p and len(p.split()) >= 2 and any(contains(neg, p) or neg == p for neg in negated_phrases) for p in row_phrases):
            excluded.add(sid)
    audio_drone_context = any(contains(normalized, p) for p in AUDIO_DRONE_PHRASES) and not (q & AERIAL_CUES)
    if audio_drone_context:
        excluded.add('aerial-shot')
    forced.update(sid for sid in required_locks if sid in known)
    if forced & excluded:
        raise ValueError('Conflicting include/exclude or brief lock: ' + ', '.join(sorted(forced & excluded)))

    docs = {r['id']: terms(' '.join([r['id'], *r['aliases']])) for r in rows}
    df = collections.Counter(t for d in docs.values() for t in d)
    vocabulary = set(df)
    expanded = set(q)
    synonym_hits = {}
    for token in sorted(q):
        for syn in SYNONYMS.get(token, ()):
            if syn in vocabulary and syn not in expanded:
                expanded.add(syn)
                synonym_hits.setdefault(token, []).append(syn)
    fuzzy = {}
    for token in sorted(q - vocabulary):
        if len(token) >= 5:
            matches = difflib.get_close_matches(token, sorted(vocabulary), n=1, cutoff=0.84)
            if matches:
                expanded.add(matches[0])
                fuzzy[token] = matches[0]
    assets = {str(x).lower().lstrip('.') for x in assets}
    capabilities = None if available is None else set(available)
    hits, unavailable, filtered, score_diagnostics = [], [], [], []
    n = len(rows)

    def item(row, score, matched=(), exact=(), reason='intent'):
        entry = {
            'id': row['id'], 'category': row['category'], 'stage': row['stage'], 'score': round(score, 3),
            'matched': sorted(matched), 'phrases': exact, 'path': row['path'], 'description': row['description'][:240],
            'requires': row['requires'], 'estimated_words': row['estimated_words'], 'estimated_tokens': estimate_tokens(row),
            'status': row['status'], 'version': row['version'], 'sha256': row.get('sha256'), 'reason': reason,
            'capability_status': 'unknown' if row['requires'] and capabilities is None else 'verified' if row['requires'] else 'not-required',
        }
        mcp_hint = _mcp_namespace_hint(row)
        if mcp_hint:
            entry['mcp_namespace'] = mcp_hint
        return entry

    def rejection(row):
        if row['id'] in excluded:
            return 'excluded-or-locked'
        if row['status'] in {'deprecated', 'blocked'}:
            return row['status']
        if capabilities is not None and not set(row['requires']) <= capabilities:
            return 'missing-capabilities'
        return None

    for row in rows:
        sid = row['id']
        phrases = [norm(sid), *(norm(alias) for alias in row['aliases'])]
        exact = [p for p in phrases if contains(normalized, p)]
        matched = expanded & docs[sid]
        asset_overlap = assets & set(row.get('asset_types', []))
        token_score = sum(min(4.0, math.log((n + 1) / (df[t] + 1))) * (0.72 if t not in q else 1.0) for t in matched)
        phrase_score = max((8 + 2 * len(p.split()) for p in exact), default=0)
        score = token_score + phrase_score
        if not exact and len(matched) < 2 and not (len(matched) >= 1 and asset_overlap):
            score = 0
        asset_bonus = 3.0 if asset_overlap and (score > 0 or sid in forced) else 0.0
        engine_bonus = 1.5 if preferred_engines and set(preferred_engines) & set(row['requires']) and score > 0 else 0.0
        score += asset_bonus + engine_bonus
        if sid in forced:
            score += 1000
        if score < min_score:
            continue
        candidate = item(row, score, matched, exact, 'explicit-or-lock' if sid in forced else 'intent')
        reason = rejection(row)
        if not reason and sid not in forced and ((stage and stage != row['stage']) or (categories and row['category'] not in categories)):
            reason = 'stage-or-category'
        if include_diagnostics:
            score_diagnostics.append({
                'id': sid, 'score': round(score, 3), 'token_score': round(token_score, 3),
                'phrase_score': phrase_score, 'asset_bonus': asset_bonus, 'engine_bonus': engine_bonus,
                'matched_terms': sorted(matched), 'exact_phrases': exact, 'filter_reason': reason,
            })
        if reason:
            if reason == 'missing-capabilities':
                candidate['missing'] = sorted(set(row['requires']) - capabilities)
                unavailable.append(candidate)
            else:
                filtered.append({'id': sid, 'reason': reason, 'score': candidate['score']})
            continue
        hits.append(candidate)

    hits.sort(key=lambda x: (-x['score'], x['id']))
    unavailable.sort(key=lambda x: (-x['score'], x['id']))
    filtered.sort(key=lambda x: (-x['score'], x['id']))
    score_diagnostics.sort(key=lambda x: (-x['score'], x['id']))
    chosen, selected_ids = [], set()
    words = tokens = 0

    def closure(sid, visiting=None):
        visiting = set() if visiting is None else visiting
        if len(visiting) >= 64:
            raise ValueError('Skill dependency depth exceeds the 64-skill safety limit')
        if sid in visiting:
            raise ValueError('Skill dependency cycle: ' + sid)
        visiting.add(sid)
        result = []
        for dep in known[sid].get('dependencies', []):
            result.extend(closure(dep, visiting))
        visiting.remove(sid)
        return list(dict.fromkeys([*result, sid]))

    def conflict(a, b):
        return b in known[a].get('conflicts', []) or a in known[b].get('conflicts', [])

    for candidate in hits:
        sid = candidate['id']
        if sid in selected_ids:
            continue
        chain = [x for x in closure(sid) if x not in selected_ids]
        reasons = [(x, rejection(known[x])) for x in chain if rejection(known[x])]
        all_ids = [*sorted(selected_ids), *chain]
        collisions = [(a, b) for i, a in enumerate(all_ids) for b in all_ids[i + 1:] if conflict(a, b)]
        if reasons or collisions:
            filtered.append({'id': sid, 'reason': 'dependency-unavailable' if reasons else 'skill-conflict', 'details': reasons or collisions})
            continue
        extra_words = sum(known[x]['estimated_words'] for x in chain)
        extra_tokens = sum(estimate_tokens(known[x]) for x in chain)
        if len(chosen) + len(chain) > limit or words + extra_words > word_budget or tokens + extra_tokens > context_budget:
            filtered.append({'id': sid, 'reason': 'context-budget'})
            continue
        for dependency in chain:
            skill_path(known[dependency], root)
            chosen.append(candidate if dependency == sid else item(known[dependency], candidate['score'], reason='dependency-of:' + sid))
            selected_ids.add(dependency)
        words += extra_words
        tokens += extra_tokens

    missing = sorted(forced - selected_ids)
    next_ids = sorted({sid for x in chosen for sid in known[x['id']].get('recommended_next', [])} - selected_ids - excluded)
    stage_buckets = collections.defaultdict(list)
    for sel in chosen:
        stage_buckets[sel['stage']].append(sel['id'])
    stage_plan = [{'stage': st, 'skills': stage_buckets[st]} for st in STAGE_ORDER if stage_buckets[st]]
    envelope = {
        'schema_version': 2, 'query': query, 'work_items': split_intents(query), 'selected': chosen,
        'stage_plan': stage_plan, 'locked_requirements': required_locks, 'constraints': locks,
        'unavailable': unavailable[:limit], 'filtered': filtered[:20],
        'unfulfilled_explicit_ids': missing, 'estimated_loaded_words_if_all_selected': words,
        'estimated_loaded_tokens_if_all_selected': tokens,
        'token_estimate_method': 'ceil(UTF-8 bytes / 3) + 120 per skill; not a tokenizer measurement',
        'context_budget': context_budget, 'catalog_size': n, 'skill_bodies_read': 0,
        'fuzzy_expansions': fuzzy, 'recommended_next': next_ids[:limit],
        'needs_refinement': not bool(chosen) or bool(missing),
        'fallback': 'Split by production stage, provide verified capabilities or explicitly include a known skill.' if not chosen or missing else None,
        'method': 'offline weighted intent/alias retrieval; host must review semantic relevance and capability uncertainty',
    }
    if include_diagnostics:
        envelope['explanation'] = {
            'normalized_query': normalized,
            'query_terms': sorted(q),
            'synonym_expansions': synonym_hits,
            'negated_phrases': negated_phrases,
            'audio_drone_disambiguated': audio_drone_context,
            'candidate_breakdown': score_diagnostics[:25],
        }
    return envelope


def route_task(task, rows, root=ROOT, include_diagnostics=False):
    allowed = {'intent', 'language', 'stage', 'assets', 'constraints', 'capabilities', 'preferred_engines', 'include', 'exclude', 'categories', 'max_skills', 'context_budget', 'word_budget'}
    if not isinstance(task, dict) or set(task) - allowed or 'intent' not in task:
        raise ValueError('Invalid task envelope or unknown fields')
    for key in ('assets', 'capabilities', 'preferred_engines', 'include', 'exclude', 'categories'):
        if key in task and (not isinstance(task[key], list) or any(not isinstance(x, str) for x in task[key])):
            raise ValueError(f'{key} must be a string array')
    if 'language' in task and not isinstance(task['language'], str):
        raise ValueError('language must be a string')
    return route(
        task['intent'], rows, limit=task.get('max_skills', 6), stage=task.get('stage'),
        categories=task.get('categories', []), available=task.get('capabilities'), include=task.get('include', []),
        exclude=task.get('exclude', []), word_budget=task.get('word_budget', 2400), context_budget=task.get('context_budget', 6000),
        constraints=task.get('constraints'), assets=task.get('assets', []), preferred_engines=task.get('preferred_engines', []),
        root=root, include_diagnostics=include_diagnostics,
    )


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description='Route a work item using local metadata; bodies load only with --load.')
    parser.add_argument('query', nargs='?', default='')
    parser.add_argument('--limit', type=int, default=6)
    parser.add_argument('--stage', choices=sorted(STAGES))
    parser.add_argument('--category', action='append', default=[])
    parser.add_argument('--available', help='Comma-separated verified capability allowlist; omitted means unknown')
    parser.add_argument('--exclude', action='append', default=[])
    parser.add_argument('--include', action='append', default=[])
    parser.add_argument('--min-score', type=float, default=2.5)
    parser.add_argument('--word-budget', type=int, default=2400)
    parser.add_argument('--context-budget', type=int, default=6000)
    parser.add_argument('--explain', action='store_true')
    parser.add_argument('--load', action='store_true')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    try:
        document = load_index()
        result = route(
            args.query, document['skills'], args.limit, args.stage, args.category,
            None if args.available is None else args.available.split(','), args.exclude, args.include,
            args.min_score, args.word_budget, args.context_budget, include_diagnostics=args.explain,
        )
        if args.load:
            rows = {r['id']: r for r in document['skills']}
            for selected in result['selected']:
                selected['instructions'] = load_skill(rows[selected['id']], token_budget=args.context_budget)
            result['skill_bodies_read'] = len(result['selected'])
    except (ValueError, OSError, KeyError) as error:
        parser.error(str(error))
    if args.json or args.load or args.explain:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Selected {len(result['selected'])}/{result['catalog_size']} skills; {result['skill_bodies_read']} bodies opened; estimated {result['estimated_loaded_tokens_if_all_selected']} tokens if loaded.")
        for selected in result['selected']:
            print(f"{selected['id']} [{selected['score']}] {selected['path']}")
        if result['needs_refinement']:
            print(result['fallback'])


if __name__ == '__main__':
    main()
