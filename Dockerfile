# syntax=docker/dockerfile:1.7
FROM python:3.13.14-alpine3.24@sha256:399babc8b49529dabfd9c922f2b5eea81d611e4512e3ed250d75bd2e7683f4b0 AS build
RUN apk add --no-cache build-base
WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY pyproject.toml README.md ./
COPY GarimpoInvestimentos ./GarimpoInvestimentos
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        "predictor-core @ https://github.com/leonardosovienski/core-predictor/releases/download/v2.2.0/predictor_core-2.2.0-py3-none-any.whl" \
        "predictor-ops @ https://github.com/leonardosovienski/tools-predictor/releases/download/v3.0.0/predictor_ops-3.0.0-py3-none-any.whl" \
        . && \
    pip uninstall -y pip

FROM python:3.13.14-alpine3.24@sha256:399babc8b49529dabfd9c922f2b5eea81d611e4512e3ed250d75bd2e7683f4b0 AS runtime
RUN addgroup -S -g 10001 predictor && adduser -S -D -u 10001 -h /nonexistent -G predictor predictor && \
    python -m pip uninstall -y pip setuptools
COPY --from=build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 OUTPUT_DIR=/var/lib/cripto-predictor/output DATA_DIR=/var/lib/cripto-predictor/data CACHE_DIR=/var/lib/cripto-predictor/cache
RUN mkdir -p /var/lib/cripto-predictor/output /var/lib/cripto-predictor/data /var/lib/cripto-predictor/cache && chown -R predictor:predictor /var/lib/cripto-predictor
USER 10001:10001
WORKDIR /var/lib/cripto-predictor
ENTRYPOINT ["cripto-predictor"]
CMD ["--help"]
