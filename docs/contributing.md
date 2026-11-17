# Contributing

Keep changes small and preserve MIT and required third-party notices. Never copy incompatible competitor source, skills or media into the core. Keep the default runtime free of models, paid services, GUIs and mandatory external engines.

Run `python3 -m unittest discover -s tests -v`, `python3 -m unittest discover -s ReelSyntax_Skills/tests -v`, `python3 -m compileall -q reelsyntax ReelSyntax_Skills/tools`, and `python3 -m reelsyntax skills validate`. Media behavior changes require actual enabled integration tests and representative artifact review, or an explicit blocked verification report. Do not substitute skipped tests for evidence.

Specialists belong in `ReelSyntax_Skills/library`, not native discovery. Keep one distinct intent per skill. Add bounded aliases, sources, acceptance/recovery steps and actual executable evidence where applicable. `registry/relations.json` owns dependency/conflict/resource/capability relations. Reindex after reviewing source changes. Do not mark guidance as implemented or validated on the strength of documentation alone.

The frontmatter reader deliberately supports the pack's string metadata subset; it is not a general YAML parser. Do not introduce arbitrary YAML tags or new parser behavior without tests. Skill dependency depth is capped at 64; selection is capped at 20. Search metadata stays local; do not paste the full registry or catalog into a host session.

Package builds use `uv build` or an equivalent PEP 517 frontend. No public package/release, Git commit/push, repository setting change or paid infrastructure is authorized by local development alone.

## First contributions

A small fixture for a translated label, a caption timing edge case, or a new routing alias makes a good first contribution. Document the expected frame range or ranked skill before changing the implementation. Browse [issues labeled good first issue](https://github.com/Remirdy/ReelSyntax/issues?q=is%3Aissue%20is%3Aopen%20label%3A%22good%20first%20issue%22) for assigned scope.
