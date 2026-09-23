# syntax=docker/dockerfile:1.7
FROM python:3.14-alpine3.24@sha256:016508ba505da24f7139765bc4bb669df4e88eb2f12eeadd571bf2f88d7533df AS build
RUN apk upgrade --no-cache && apk add --no-cache build-base
WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY --from=ghcr.io/astral-sh/uv:0.12.1 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock README.md ./
COPY GarimpoInvestimentos ./GarimpoInvestimentos
COPY charters ./charters
COPY observation_plans ./observation_plans
# Dependências só do uv.lock, com --require-hashes; o próprio pacote entra sem deps.
RUN uv export --locked --no-dev --no-emit-project --extra llm --extra excel --extra v3 \
        --format requirements-txt --output-file /tmp/lock-requirements.txt && \
    pip install --no-cache-dir --require-hashes -r /tmp/lock-requirements.txt && \
    pip install --no-cache-dir --no-deps . && \
    pip uninstall -y pip

FROM python:3.14-alpine3.24@sha256:016508ba505da24f7139765bc4bb669df4e88eb2f12eeadd571bf2f88d7533df AS runtime
RUN apk upgrade --no-cache && \
    addgroup -S -g 10001 predictor && adduser -S -D -u 10001 -h /nonexistent -G predictor predictor && \
    python -m pip uninstall -y pip setuptools
COPY --from=build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 OUTPUT_DIR=/var/lib/cripto-predictor/output DATA_DIR=/var/lib/cripto-predictor/data CACHE_DIR=/var/lib/cripto-predictor/cache LOGS_DIR=/var/lib/cripto-predictor/logs
RUN mkdir -p /var/lib/cripto-predictor/output /var/lib/cripto-predictor/data /var/lib/cripto-predictor/cache /var/lib/cripto-predictor/logs && chown -R predictor:predictor /var/lib/cripto-predictor
USER 10001:10001
WORKDIR /var/lib/cripto-predictor
ENTRYPOINT ["cripto-predictor"]
CMD ["--help"]
