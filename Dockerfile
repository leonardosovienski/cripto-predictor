# syntax=docker/dockerfile:1.7
FROM python:3.14-alpine3.24@sha256:9e9fde4d32eedce0b661d9ab91e826b62dddf28e928c230ec55f1866cac66b01 AS build
RUN apk upgrade --no-cache && apk add --no-cache build-base
WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY --from=ghcr.io/astral-sh/uv:0.12.1 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock README.md STACK_WHEELS.json ./
COPY scripts/stack_wheels.py ./scripts/stack_wheels.py
# Wheels publicadas do stack (core/ops), já baixadas e conferidas pelo sha256 por `scripts/stack_wheels.py fetch`
# no contexto de build; a imagem não consulta o GitHub (os produtores são privados).
COPY .stack-wheels ./.stack-wheels
COPY GarimpoInvestimentos ./GarimpoInvestimentos
COPY charters ./charters
COPY observation_plans ./observation_plans
# Dependências só do uv.lock, com --require-hashes; o próprio pacote entra sem deps.
RUN uv export --locked --no-dev --no-emit-project --extra llm --extra excel --extra v3 \
        --format requirements-txt --output-file /tmp/lock-requirements.txt && \
    python scripts/stack_wheels.py check && \
    python scripts/stack_wheels.py requirements --input /tmp/lock-requirements.txt --output /tmp/lock-requirements.hashed.txt && \
    pip install --no-cache-dir --require-hashes -r /tmp/lock-requirements.hashed.txt && \
    pip install --no-cache-dir --no-deps . && \
    pip uninstall -y pip

FROM python:3.14-alpine3.24@sha256:9e9fde4d32eedce0b661d9ab91e826b62dddf28e928c230ec55f1866cac66b01 AS runtime
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
