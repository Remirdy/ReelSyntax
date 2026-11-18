# Installation

For a step-by-step first-run walkthrough—including `pip install "reelsyntax[render]"`, cross-platform FFmpeg discovery, local language-model hardware sizing, and `reelsyntax doctor` remediation—see [Getting started](getting-started.md).

Run `reelsyntax --help` (or `python -m reelsyntax --help` on Linux/macOS, `py -m reelsyntax --help` on Windows) with Python 3.11 or newer. No third-party dependency is needed for the core router, project validation, configuration, or state operations. For an installed CLI, create a virtual environment and install the package:

- **macOS / Linux:** `python3 -m venv .venv && . .venv/bin/activate && python -m pip install ".[render]"`
- **Windows (PowerShell):** `py -3 -m venv .venv; .\.venv\Scripts\Activate.ps1; python -m pip install ".[render]"`
- **Container:** `docker run --rm ghcr.io/remirdy/reelsyntax doctor --json` runs the published non-root image with FFmpeg and Pillow preinstalled; see [Containers and Codespaces](containers.md) for Compose, MCP and GitHub Codespaces setup.

The optional render extra installs Pillow (`".[render]"`). The optional browser extra installs Pillow and Playwright (`".[browser]"`). FFmpeg and FFprobe must be installed separately from a distribution linked by the [FFmpeg project](https://ffmpeg.org/download.html) (for example `brew install ffmpeg` on macOS, `apt install ffmpeg` on Debian/Ubuntu, or `winget install Gyan.FFmpeg` / `choco install ffmpeg` on Windows); builds and codecs have separate licensing implications. Do not bundle binaries under the MIT core license.

Use an existing PATH installation, `[paths]` in `reelsyntax.toml`, or explicit executable paths through `REELSYNTAX_FFMPEG`, `REELSYNTAX_FFPROBE`, and `REELSYNTAX_BLENDER`. Those values must be absolute executable paths. The runtime uses argument arrays, not shell command strings, and probes standard macOS, Windows, and Linux install locations when launched from GUI hosts with a minimal `PATH`.

After separately authorizing a browser binary download, run `python -m playwright install chromium`. Playwright requires a matching browser build; see its [browser setup documentation](https://playwright.dev/python/docs/browsers). For a project-local browser cache, set `PLAYWRIGHT_BROWSERS_PATH` to an absolute directory inside `.tools/` before installation and when invoking the CLI. On Windows, set environment variables using PowerShell syntax. The runtime keeps Chromium's sandbox enabled. It does not silently fall back to an unsafe launch.

`doctor` reports whether tools/packages are available. Browser binary presence is not a successful launch test. Validate launch and offline capture with the explicitly enabled browser integration test. No installed optional tool is advertised as an implemented adapter merely because its executable exists.

Host discovery paths were checked against [Codex documentation](https://learn.chatgpt.com/docs/build-skills), [Claude Code documentation](https://code.claude.com/docs/en/skills) and [Cursor documentation](https://cursor.com/docs/skills) on 2026-11-17. Temporary-directory installation tests verify file behavior, not native activation or context telemetry. No user-level host configuration is modified.

For optional uv-based setup, `uv.lock` records resolved Python extras with hashes. After authorizing the selected extra, `uv sync --locked --extra render` or `uv sync --locked --extra browser` creates the project environment. This does not install FFmpeg or Chromium binaries. The base installed CLI has no third-party runtime dependencies.
