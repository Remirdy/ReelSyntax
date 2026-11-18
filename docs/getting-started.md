# Getting started

This guide walks through installing ReelSyntax, verifying media tools with `reelsyntax doctor`, configuring optional local language-model and speech runtimes, and rendering a first verified video on macOS, Linux, or Windows.

## Install ReelSyntax

ReelSyntax requires Python 3.11 or newer. The core CLI (`reelsyntax skills`, `validate`, `plan`, `config`, `lang`, `formats`) has zero required third-party Python dependencies. Installing the `[render]` extra adds Pillow for procedural 2D and typographic rendering:

=== "macOS / Linux"

    ```sh
    python3 -m venv .venv
    . .venv/bin/activate
    python -m pip install "reelsyntax[render]"
    ```

=== "Windows (PowerShell)"

    ```powershell
    py -3 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install "reelsyntax[render]"
    ```

=== "From a source checkout"

    ```sh
    python3 -m venv .venv
    . .venv/bin/activate
    python -m pip install -e ".[render]"
    ```

Enable shell tab-completion if desired:

```sh
reelsyntax completion zsh > ~/.zfunc/_reelsyntax
```

(`bash`, `zsh`, `fish`, and `powershell` are supported.)

## FFmpeg and FFprobe

Video encoding, audio mastering, and objective quality control (`reelsyntax qc`) require both `ffmpeg` and `ffprobe`. Because codec builds carry separate licensing terms, ReelSyntax discovers your installed binaries rather than bundling them.

=== "macOS"

    ```sh
    brew install ffmpeg
    ```

=== "Debian / Ubuntu"

    ```sh
    sudo apt update && sudo apt install -y ffmpeg
    ```

=== "Windows (PowerShell)"

    ```powershell
    winget install Gyan.FFmpeg
    ```

If `ffmpeg` and `ffprobe` are installed outside `PATH` (common in GUI hosts), configure `[paths]` in `reelsyntax.toml`:

```sh
reelsyntax config init --user
```

```toml
config_version = 1

[paths]
ffmpeg = "/opt/homebrew/bin/ffmpeg"
ffprobe = "/opt/homebrew/bin/ffprobe"
```

Environment variables `REELSYNTAX_FFMPEG` and `REELSYNTAX_FFPROBE` override `[paths]` when set to absolute executable paths.

## Verify your setup with `doctor`

Run `reelsyntax doctor` before rendering:

```sh
reelsyntax doctor
reelsyntax doctor --providers --blender --json
```

When `render_available` is `true`, Pillow, FFmpeg, and FFprobe are ready. To share environment details in a bug report without exposing local home-directory usernames or endpoint credentials, pass `--report`:

```sh
reelsyntax doctor --report --json
```

## Local language model setup

`reelsyntax make` works immediately offline with zero model downloads via the built-in `offline_rules` provider (`provider.name = "offline_rules"`).

For richer scriptwriting and beat structuring on your own machine, connect a local structured-JSON server on loopback (`127.0.0.1`):

1. Install a local inference server such as [Ollama](https://ollama.com) (`http://127.0.0.1:11434`) or any local server exposing a `/v1/chat/completions` JSON endpoint on `127.0.0.1`.
2. Pull an instruction-tuned model suited to your available memory and set `[provider]` in `reelsyntax.toml`:

```toml
[provider]
name = "ollama"
model = "local-instruct:7b-q4"
endpoint = "http://127.0.0.1:11434"
timeout_sec = 60
max_repairs = 3
```

### Hardware sizing reference (adjustable baseline)

Memory usage depends on quantization, context window length, and runtime version. Treat the table below as an adjustable starting baseline and verify exact memory requirements against your local runtime's current official documentation:

| Parameter tier (4-bit quantized) | Typical RAM / unified memory | Dedicated GPU VRAM | Recommended use in ReelSyntax |
| --- | --- | --- | --- |
| Zero-model (`offline_rules`) | < 256 MiB | None | Deterministic templates, CI smoke tests, instant previews |
| Small (`1B – 3B`, Q4) | 4 – 6 GiB | 3 – 4 GiB (or CPU) | Short hooks, kinetic typography, fast draft iteration; relies on ReelSyntax's 3-turn schema repair loop |
| Medium (`7B – 8B`, Q4) | 8 – 12 GiB | 6 – 8 GiB | General-purpose multilingual scripts (`en`, `tr`, `de`), explainer slides, revisions |
| Large (`14B`, Q4) | 16 – 24 GiB | 10 – 12 GiB | Multi-scene data stories, nuanced tone/formality control, cutscene dialogue |
| Workstation (`32B+`, Q4) | 32+ GiB | 20 – 24+ GiB | Complex multi-format campaigns when turnaround latency is secondary |

Remote non-loopback endpoints are blocked by default and require explicit `--allow-network` (or `general.allow_network = true` in `reelsyntax.toml`).

## Speech and captions

Formats that include narration check for a local speech synthesis runtime per target language. When local speech synthesis is not installed for the requested `--lang`, ReelSyntax automatically falls back to timed kinetic captions and procedural music beds so every first-run project still produces a complete, reviewable video with audio.

## Optional browser and 3D engines

Most formats render through Pillow and FFmpeg alone. Two optional local engines unlock shader/DOM scenes and native 3D scenes:

- **Headless Chromium (`browser` / `webgl`):**
  ```sh
  python -m pip install "reelsyntax[browser]"
  python -m playwright install chromium
  ```
- **Headless Blender (`blender`):**
  Install [Blender](https://www.blender.org/download/) 4.2 LTS or newer (Blender 5.1+ for optical `aperture` scenes) and verify headless scripting with `reelsyntax doctor --blender`. Set `[paths].blender` or `REELSYNTAX_BLENDER` if installed in a non-standard path.

## First video walkthrough

1. **Estimate render budget without writing files:**
   ```sh
   reelsyntax make "12s vertical reel on reproducible local video builds" --dry-run
   ```
2. **Start an interactive approval-gated project:**
   ```sh
   reelsyntax make "12s vertical reel on reproducible local video builds" --out ./my-first-reel
   ```
3. **Approve, edit, or step back through gates:**
   ```sh
   reelsyntax step ./my-first-reel idea --approve
   reelsyntax step ./my-first-reel script --edit "Add a concrete cache-hit metric in scene 2"
   ```
   Pass `--yes` on `make` or `resume` when you want unattended execution through draft, hero, and QC:
   ```sh
   reelsyntax resume ./my-first-reel --yes
   ```
4. **Apply a targeted revision while preserving unchanged scene caches:**
   ```sh
   reelsyntax revise ./my-first-reel "scene 2 heading: Instant Cache Reuse" --render
   ```
