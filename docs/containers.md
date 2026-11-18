# Containers and Codespaces

ReelSyntax ships a production container image, a Compose file for local use, and a dev container for GitHub Codespaces. All of them keep the offline, local-first defaults of the CLI.

| File | Purpose |
| --- | --- |
| `Dockerfile` | Multi-stage build: `base` (pinned `python:3.12-slim` + FFmpeg + DejaVu fonts), `build` (wheel), `dev` (Codespaces tooling), `runtime` (default, published image). |
| `.dockerignore` | Keeps VCS metadata, virtual environments, secrets (`.env*`), submodules, caches, renders and docs out of the build context. |
| `docker-compose.yml` | Hardened local services: `reelsyntax` (one-shot CLI) and `mcp` (stdio MCP gateway, `mcp` profile). |
| `.devcontainer/devcontainer.json` | Codespaces / VS Code Dev Containers using the `dev` stage. |
| `.devcontainer/Dockerfile` | Full media image (Blender + Chromium) used by the `container` job in `.github/workflows/check.yml`. |
| `.github/workflows/container.yml` | Builds and smoke-tests the image on every pull request and push; publishes to GHCR only for `v*` tags or manual dispatch. |

## Runtime image

The `runtime` stage installs the ReelSyntax wheel with the `render` extra (Pillow, pinned in `pyproject.toml`) on top of FFmpeg. It runs as the unprivileged `reelsyntax` user (UID/GID `10001`), uses `/workspace` as its working directory and volume, and its entrypoint is the CLI:

```dockerfile
ENTRYPOINT ["python3", "-m", "reelsyntax"]
```

Pull the published image or build it locally:

```sh
docker pull ghcr.io/remirdy/reelsyntax:latest
docker build -t reelsyntax .
```

Run any CLI command against a mounted project directory:

```sh
docker run --rm ghcr.io/remirdy/reelsyntax doctor --json
docker run --rm --network none \
  -u "$(id -u):$(id -g)" -e HOME=/tmp/home \
  -v "$PWD/workspace:/workspace" \
  ghcr.io/remirdy/reelsyntax make "12s vertical kinetic reel about local builds" --provider offline_rules --out reel --yes
docker run --rm -u "$(id -u):$(id -g)" -e HOME=/tmp/home -v "$PWD/workspace:/workspace" \
  ghcr.io/remirdy/reelsyntax qc reel --profile draft
```

Blender, Chromium and After Effects are not part of the slim runtime image. `doctor --json` reports them as unavailable, and scenes that need those engines must be rendered on a host or with `.devcontainer/Dockerfile`.

## Docker Compose

```sh
mkdir -p workspace
REELSYNTAX_UID="$(id -u)" REELSYNTAX_GID="$(id -g)" docker compose run --rm reelsyntax doctor --json
REELSYNTAX_UID="$(id -u)" REELSYNTAX_GID="$(id -g)" docker compose run --rm reelsyntax init demo
REELSYNTAX_UID="$(id -u)" REELSYNTAX_GID="$(id -g)" docker compose run --rm reelsyntax render demo --profile draft
```

Compose defaults are deliberately strict:

- `network_mode: none` keeps rendering and the `offline_rules` provider fully offline. Remove it in a `docker-compose.override.yml` only when you opt in to network providers or `formats install --allow-network`.
- `read_only: true`, a `/tmp` tmpfs, `cap_drop: [ALL]` and `no-new-privileges` limit what the container can change. `HOME` points into the tmpfs so arbitrary `REELSYNTAX_UID` values work.
- `REELSYNTAX_WORKSPACE` (default `./workspace`) is bind-mounted at `/workspace`. Set `REELSYNTAX_UID`/`REELSYNTAX_GID` to your host IDs so rendered files stay owned by you.
- `REELSYNTAX_TAG` selects the image tag (default `latest`); `docker compose build` builds the `runtime` stage locally instead.

### MCP gateway in a container

The `mcp` service runs `reelsyntax mcp --workspace /workspace` with stdin attached. Register it with an MCP host as a stdio command:

```json
{
  "mcpServers": {
    "reelsyntax": {
      "command": "docker",
      "args": ["compose", "-f", "/absolute/path/to/ReelSyntax/docker-compose.yml", "run", "--rm", "-T", "mcp"]
    }
  }
}
```

Project and format tools stay contained inside `/workspace`. First-party BlenderMCP and AfterEffectsMCP integrations are not available inside the slim image.

## GitHub Codespaces and Dev Containers

Open the repository in Codespaces (or **Dev Containers: Reopen in Container** locally). The dev container builds the `dev` stage, which adds Git, Pillow, `ruff`, `mypy` and `coverage` on top of the same FFmpeg base and runs as the non-root `editor` user. After creation it installs ReelSyntax in editable mode and prints `reelsyntax doctor`.

```sh
python3 -m unittest discover -s tests
ruff check reelsyntax ReelSyntax_Skills/tools tests tools
mypy
```

Initialize the optional first-party submodules only when you need them: `git submodule update --init --recursive`.

## Continuous integration and releases

`.github/workflows/container.yml` has two jobs:

1. **verify** runs on pull requests, pushes to `main`, tags and manual dispatch with read-only permissions. It builds the `runtime` stage, runs `python3 -m reelsyntax doctor --json` with networking disabled, checks the non-root user, entrypoint and `/workspace` working directory, performs an offline `make --dry-run` against a mounted workspace, validates `docker compose config`, and builds the `dev` stage.
2. **publish** runs only when `startsWith(github.ref, 'refs/tags/v') || github.event_name == 'workflow_dispatch'`, so pull request checks never need registry permissions. It logs in to GHCR with the workflow token, pushes `ghcr.io/remirdy/reelsyntax` (`X.Y.Z`, `latest` and `sha-<commit>` for tags; `sha-<commit>` and `edge` for manual runs), and records a build provenance attestation.

The base image is pinned by tag and digest; Dependabot's `docker` ecosystem proposes updates.
