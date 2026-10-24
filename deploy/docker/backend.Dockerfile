FROM python:3.13-slim-trixie AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /build
COPY backend/pyproject.toml ./
COPY backend/app ./app
RUN python -m pip wheel --wheel-dir /wheels .

FROM python:3.13-slim-trixie AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/digitalfootprint/venv/bin:$PATH
RUN groupadd --system --gid 10001 digitalfootprint \
    && useradd --system --uid 10001 --gid digitalfootprint --home /nonexistent --shell /usr/sbin/nologin digitalfootprint \
    && python -m venv /opt/digitalfootprint/venv \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install --yes --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* \
    && rm -rf /wheels
WORKDIR /app
COPY backend/alembic.ini ./alembic.ini
COPY backend/alembic ./alembic
COPY deploy/docker/backend-entrypoint.sh /usr/local/bin/digitalfootprint-entrypoint
RUN chmod 0555 /usr/local/bin/digitalfootprint-entrypoint \
    && mkdir -p /data \
    && chown digitalfootprint:digitalfootprint /data
USER 10001:10001
EXPOSE 8000
ENTRYPOINT ["digitalfootprint-entrypoint"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
