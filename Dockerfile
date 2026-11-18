ARG PYTHON_IMAGE=python:3.12.16-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df

FROM ${PYTHON_IMAGE} AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    LANG=C.UTF-8
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core ca-certificates \
    && rm -rf /var/lib/apt/lists/*

FROM base AS build
WORKDIR /src
COPY pyproject.toml README.md LICENSE MANIFEST.in ./
COPY reelsyntax ./reelsyntax
COPY ReelSyntax_Skills ./ReelSyntax_Skills
RUN python3 -m pip wheel --no-deps --wheel-dir /wheels .

FROM base AS dev
RUN apt-get update \
    && apt-get install -y --no-install-recommends git openssh-client sudo \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 editor \
    && useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash editor \
    && echo "editor ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/editor \
    && chmod 0440 /etc/sudoers.d/editor \
    && python3 -m pip install "Pillow==13.0.0" ruff mypy coverage
USER editor
ENV PATH=/home/editor/.local/bin:$PATH
WORKDIR /workspaces/ReelSyntax

FROM base AS runtime
ARG VERSION=0.1.0
ARG REVISION=unknown
LABEL org.opencontainers.image.title="ReelSyntax" \
      org.opencontainers.image.description="Local skill routing and deterministic headless motion production" \
      org.opencontainers.image.source="https://github.com/Remirdy/ReelSyntax" \
      org.opencontainers.image.url="https://remirdy.github.io/ReelSyntax/" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${REVISION}"
COPY --from=build /wheels /wheels
RUN set -eu; \
    wheel="$(ls /wheels/reelsyntax-*.whl)"; \
    python3 -m pip install "${wheel}[render]"; \
    rm -rf /wheels; \
    groupadd --gid 10001 reelsyntax; \
    useradd --uid 10001 --gid 10001 --create-home --home-dir /home/reelsyntax --shell /usr/sbin/nologin reelsyntax; \
    mkdir -p /workspace; \
    chown reelsyntax:reelsyntax /workspace
ENV HOME=/home/reelsyntax
USER 10001:10001
WORKDIR /workspace
VOLUME ["/workspace"]
ENTRYPOINT ["python3", "-m", "reelsyntax"]
CMD ["--help"]
