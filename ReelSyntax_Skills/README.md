# ReelSyntax Skills

A modular, headless starter library of 500 filmmaking and engineering skills, with a local dependency-free metadata router. Intended for integration into `Remirdy/ReelSyntax` under its existing MIT license. The 500 files are production guidance (not 500 tested renderer implementations); the router is an executable prototype.

## Start

From this directory, with Python 3 installed:

```sh
python tools/route.py "psd animasyon seslendirme senkronu alt bar sabit"
python tools/route.py "github tanıtım terminal animasyonu logo animasyonu beat sync" --json
python tools/route.py "öğretmenler günü storyboard kamera sabit yazı olmasın" --load
python -m unittest discover -s tests -v
```

On systems where `python` points elsewhere, use `python3` or `py -3`. `--json` returns only candidate metadata; `--load` is explicitly opt-in and prints selected bodies. `--available ffmpeg,threejs` filters skills with declared requirements; an omitted flag does not certify installed capabilities. Use `--stage`, `--category`, `--include`, `--exclude`, `--word-budget` and `--limit` as needed. The heuristic may miss paraphrased intents; split tasks, use clear aliases or explicitly select required IDs.

## Layout

- `.agents/skills/reelsyntax-router/SKILL.md`: single host entry skill; keep 500 specialist bodies out of native automatic discovery.
- `library/`: 25 categories, each containing 20 distinct SKILL.md files.
- `registry/index.json`: metadata index used by router; keep out of model context.
- `registry/catalog.csv`, `CATALOG.md`: searchable human-facing inventories.
- `tools/route.py`: working offline selection and optional loading.
- `tools/reindex.py`: rebuild metadata after changing skill files; supports the seed's restricted scalar frontmatter convention, not arbitrary YAML.
- `tests/`: router and catalog checks; router checks; a separate limited motion fixture is included; no host integration tests yet.
- `SKILL_SYSTEM.md`: production implementation specification and further research mandate.
- `RESEARCH.md`: source audit and limitations.

To integrate, preserve the original master development specification and MIT license; incorporate this pack under a dedicated directory, then expose only the router at the verified host discovery location. Do not overwrite existing agent files. See `SKILL_SYSTEM.md` for the complete migration plan. The pack has no bundled external code, models, media, GUI or paid API dependency. The exact license notices for future dependencies must be reviewed independently.

## Production-grade v2 update

All 500 skills now contain individually authored technical production recipes, measurable or reviewable acceptance criteria, evidence and repair steps. Keep them outside automatic discovery. Read `QUALITY_STANDARD.md` once for the production, not once per skill. Use `draft`, `production` or `hero` profile as appropriate. `PRODUCTION_INTEGRATION_PROMPT.md` is the new integration prompt. `registry/technical-recipes.json` supports maintainers, not model context. `tools/quality_audit.py` probes and scans an actual video; it does not score aesthetics. `examples/hero-fixture/` contains a runnable original motion fixture, actual preview and positive/negative audit reports. The original seven router tests passed again; see `TEST_RESULTS.txt`. The 500 skills remain production guidance, not executed implementations. Actual host integration, additional backend testing and full creative review remain outstanding.

## Integrated runtime

The repository now exposes this same router through `python3 -m reelsyntax skills` from the checkout root. See the root README and `docs/development-status.md` for actual implementation and verification status. The supplied instructions and all 500 specialist bodies are retained. Index v2 adds hashes, dependency/conflict/resource relations and separate index-maintenance accounting. Body loading remains explicit; the full catalog stays outside host context.

## Scoped production references

Nine optional references document the core's implemented subsets for `j-cut`, `l-cut`, `psd-to-video`, `shader-effects`, `otio-export`, `fcpxml-export`, `render-cache`, `partial-render` and `ffmpeg-trimming`. They cover actual parameters, capability boundaries, source/frame units, failure conditions and verification paths. They do not upgrade general guidance into a claim that every external-engine technique has been executed. All 517 current `SKILL.md` files remain byte-identical to the prior published catalog.

Use `reelsyntax skills load ID` to discover a skill's declared resource paths, then request one explicitly with `--resource PATH`. Resource files stay inside their owning skill directories. Search reads metadata only; a resource read returns its verified `sha256`, consumes its own context budget and is never executed automatically. Session deduplication keys include the selected content hash, so changing a reference without changing `SKILL.md` correctly triggers a fresh budgeted load. Previously loaded reference versions retain their existing budget charge.

`reelsyntax skills reindex` and `tools/reindex.py` now both refresh the index and CSV catalog from current relation overrides. CSV output preserves UTF-8 BOM/CRLF compatibility and is replaced atomically. The native core OTIO writer has no optional SDK requirement in its routing metadata; external OTIO adapters remain separate capabilities.
