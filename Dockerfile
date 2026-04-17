# === Stage 1: Builder ===
FROM --platform=linux/amd64 ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    HF_HOME=/app/hf-cache \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Build toolchain for C++ wheels (scikit-network via ragas). Stays in
# builder stage only — runtime image does not receive these packages.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        g++ \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first (cache-friendly layer ordering)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Bake KURE-v1 (~400MB) into the image so Cloud Run cold-start does not
# fetch from HuggingFace Hub (which would blow past the 10s startup
# probe and repeat per-instance). The download script warms the
# KURE-v1 cache under HF_HOME (/app/hf-cache), which we COPY into the
# runtime stage.
#
# scripts/ is gitignored from the normal source COPY (see .dockerignore),
# so we bind-mount the prefetch script here rather than relying on
# `COPY . /app`.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=scripts/download_kure_model.py,target=/app/scripts/download_kure_model.py \
    /app/.venv/bin/python /app/scripts/download_kure_model.py

# Copy app source and install project
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev \
    && python -m compileall -q src/

# === Stage 2: Runtime ===
FROM --platform=linux/amd64 python:3.14-slim-bookworm

RUN groupadd --system --gid 999 nonroot \
    && useradd --system --gid 999 --uid 999 --create-home nonroot

COPY --from=builder --chown=nonroot:nonroot /app /app

# Point SentenceTransformer / transformers at the baked HF cache so no
# network fetch happens at cold-start.
ENV PATH="/app/.venv/bin:$PATH" \
    HF_HOME=/app/hf-cache
USER nonroot
WORKDIR /app

EXPOSE 8501

ENTRYPOINT ["streamlit", "run", "src/pillcare/app.py", \
    "--server.port=8501", \
    "--server.address=0.0.0.0", \
    "--server.headless=true", \
    "--server.enableXsrfProtection=true", \
    "--server.enableWebsocketCompression=false"]
