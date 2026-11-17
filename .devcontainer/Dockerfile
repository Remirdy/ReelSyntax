FROM python:3.13-bookworm
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/reelsyntax/chromium
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg blender fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/reelsyntax/source
COPY . .
RUN python -m pip install --no-cache-dir '.[browser]' && python -m playwright install --with-deps chromium
WORKDIR /workspaces
RUN useradd --create-home --uid 1000 editor && chmod -R a+rX /opt/reelsyntax/chromium
USER editor
ENV PATH=/home/editor/.local/bin:$PATH
