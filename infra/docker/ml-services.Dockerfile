FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*

COPY ml-services/requirements.txt ./ml-services/requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r ./ml-services/requirements.txt

COPY scripts ./scripts
COPY proto ./proto
COPY ml-services ./ml-services

RUN bash ./scripts/generate_proto.sh --python-only

WORKDIR /app/ml-services

CMD ["python", "grpc_server/server.py"]
