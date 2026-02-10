# Use the official uv image with Python 3.12 (Bookworm Slim)
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Configure uv: compile bytecode for faster startup, use copy mode for safety
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Add the virtual environment to PATH so we can run `uvicorn` directly
ENV PATH="/app/.venv/bin:$PATH"

# Set data location for the app
ENV XDG_DATA_HOME=/data

WORKDIR /app

# --- LAYER 1: Dependency Installation (Cached) ---
# Copy the root workspace definitions
COPY pyproject.toml uv.lock ./

# Copy member manifests (Maintain directory structure exactly as in repo)
# We must copy ALL workspace members defined in uv.lock, otherwise sync will fail
COPY packages/transactions-core/pyproject.toml ./packages/transactions-core/
COPY apps/transactions-web/pyproject.toml ./apps/transactions-web/
COPY apps/transactions-cli/pyproject.toml ./apps/transactions-cli/

# Install dependencies only (no project code yet)
RUN uv sync --frozen --no-install-project

# --- LAYER 2: Application Code ---
# Copy the actual source code
COPY packages ./packages
COPY apps ./apps

# Install the project itself
RUN uv sync --frozen

# --- LAYER 3: Runtime Setup ---
# Create volume mount point for SQLite DB
RUN mkdir -p /data/transactions-web && chmod 777 /data/transactions-web

EXPOSE 8000

# Run the web application
CMD ["uvicorn", "transactions_web.main:app", "--host", "0.0.0.0", "--port", "8000"]