# syntax=docker/dockerfile:1.7
FROM python:3.14-alpine3.24@sha256:05b2b8b732ecd268fee8727a369f936f022d1321b59befd13c30ede22769dcdc AS build
RUN apk upgrade --no-cache && apk add --no-cache build-base
WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY pyproject.toml README.md ./
COPY GarimpoInvestimentos ./GarimpoInvestimentos
COPY charters ./charters
COPY observation_plans ./observation_plans
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        "predictor-core @ https://github.com/leonardosovienski/core-predictor/releases/download/v3.0.0/predictor_core-3.0.0-py3-none-any.whl" \
        "predictor-ops @ https://github.com/leonardosovienski/predictor-ops/releases/download/v4.0.0/predictor_ops-4.0.0-py3-none-any.whl" \
        ".[llm,excel,v3]" && \
    pip uninstall -y pip

FROM python:3.14-alpine3.24@sha256:05b2b8b732ecd268fee8727a369f936f022d1321b59befd13c30ede22769dcdc AS runtime
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
