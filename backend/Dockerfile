# Multi-stage build: dependencies compiled in a build stage, runtime image kept
# minimal so the deployed surface is small.

FROM python:3.11-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir uv==0.11.15

COPY pyproject.toml ./
COPY src ./src

RUN uv venv .venv && \
    uv pip install --python .venv/bin/python .

FROM python:3.11-slim AS runtime

# A non-root user, because a container compromise should not hand over root.
RUN useradd --create-home --shell /bin/bash bharatos

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src ./src
COPY alembic ./alembic
COPY alembic.ini ./

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    BHARAT_OS_ENVIRONMENT=production

USER bharatos

EXPOSE 8000

# Migrations run before the server starts, so a deploy never serves traffic
# against a schema it does not match.
CMD ["sh", "-c", "alembic upgrade head && uvicorn bharat_os.main:app --host 0.0.0.0 --port 8000"]
