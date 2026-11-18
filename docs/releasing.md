# Versioning, releases, and deprecation policy

## Semantic versioning

ReelSyntax follows [Semantic Versioning 2.0.0](https://semver.org/):

- **Patch (`x.y.Z`)**: Bug fixes, documentation updates, routing alias additions, and non-breaking quality checks.
- **Minor (`x.Y.0`)**: Backward-compatible CLI commands, optional `reel.json` or `reelsyntax.toml` fields, new formats, and new validated skills. While major version `0` is active (`0.y.z`), breaking changes are still avoided whenever possible and paired with `reelsyntax migrate`.
- **Major (`X.0.0`)**: Intentional incompatibilities in `reel.json` (`schema_version` increment), CLI exit/JSON envelope contracts, or MCP meta-tool signatures.
- **Pre-releases (`vX.Y.Z-rc.1`, `vX.Y.Z-beta.1`)**: Tagged pre-releases automatically mark the GitHub Release as `--prerelease`. Clean `vX.Y.Z` tags publish stable releases.

## Deprecation policy

1. Public CLI flags, `reelsyntax.toml` keys, MCP tool arguments, and `reel.json` fields remain supported for at least **one minor release** after deprecation is announced in `CHANGELOG.md`.
2. Deprecated `reel.json` fields gain an automated upgrade path in `reelsyntax migrate <project>` before removal.
3. Deprecated skill IDs retain routing alias forwarding or explicit `deprecated` status metadata rather than disappearing silently.

## Automated release pipeline

Pushing a version tag matching `v*` triggers `.github/workflows/release.yml`:

1. `python tools/release_prepare.py verify --tag "$GITHUB_REF_NAME"` confirms exact version alignment across `pyproject.toml`, `reelsyntax/__init__.py`, `server.json`, and `CHANGELOG.md`.
2. `python -m build` builds the wheel (`.whl`) and source distribution (`.tar.gz`), and a clean virtual environment outside the checkout smoke-tests `pip install dist/*.whl` (`reelsyntax --version`, `skills validate`, `schema`, `config show`).
3. `tools/build_mcpb.py` packages `dist/reelsyntax.mcpb`, and `tools/release_prepare.py stamp-mcpb` writes its actual SHA-256 digest into `dist/server.json`.
4. `tools/release_prepare.py notes` extracts the release's exact section from `CHANGELOG.md`, generates `SHA256SUMS.txt`, signs build provenance attestations, creates the GitHub Release, and publishes the package to PyPI via OIDC Trusted Publishing.

## One-time PyPI Trusted Publisher setup

Before pushing the first PyPI release tag, configure a Trusted Publisher on [pypi.org](https://pypi.org/manage/account/publishing/):

- **PyPI project name:** `reelsyntax`
- **Owner:** `Remirdy`
- **Repository:** `ReelSyntax`
- **Workflow filename:** `release.yml`
- **Environment name:** `pypi`

No long-lived `PYPI_API_TOKEN` secret is needed when OIDC Trusted Publishing is enabled.
