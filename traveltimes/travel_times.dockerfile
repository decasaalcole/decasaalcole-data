FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

COPY pyproject.toml /app/pyproject.toml
COPY uv.lock /app/uv.lock

# Install the project's dependencies using the lockfile and settings
RUN uv sync --frozen --no-install-project

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"
