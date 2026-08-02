# syntax=docker/dockerfile:1.7
FROM python:3.13.11-slim-bookworm@sha256:20080e807bfc404f8450b185cf0fc95d553462673598549613735f70a5b4d5d0 AS build
WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY pyproject.toml README.md ./
COPY GarimpoInvestimentos ./GarimpoInvestimentos
COPY wheelhouse ./wheelhouse
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ./wheelhouse/predictor_core-2.1.0-py3-none-any.whl ./wheelhouse/predictor_ops-2.0.0-py3-none-any.whl .

FROM python:3.13.11-slim-bookworm@sha256:20080e807bfc404f8450b185cf0fc95d553462673598549613735f70a5b4d5d0 AS runtime
RUN groupadd --system --gid 10001 predictor && useradd --system --uid 10001 --gid predictor --home-dir /nonexistent predictor
COPY --from=build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 OUTPUT_DIR=/var/lib/cripto-predictor/output DATA_DIR=/var/lib/cripto-predictor/data CACHE_DIR=/var/lib/cripto-predictor/cache
RUN mkdir -p /var/lib/cripto-predictor/output /var/lib/cripto-predictor/data /var/lib/cripto-predictor/cache && chown -R predictor:predictor /var/lib/cripto-predictor
USER 10001:10001
WORKDIR /var/lib/cripto-predictor
ENTRYPOINT ["cripto-predictor"]
CMD ["--help"]
