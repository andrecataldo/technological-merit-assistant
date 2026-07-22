FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY ui ./ui
COPY config ./config

RUN pip install --upgrade pip && pip install -e .

EXPOSE 8000 8501
