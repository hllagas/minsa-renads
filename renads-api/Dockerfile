FROM python:3.14-slim-bookworm

# System dependencies:
#   libreoffice        — soffice --convert-to pdf (generación de proyectos de convenio)
#   libpq-dev          — psycopg2-binary
#   libjpeg-dev zlib1g-dev — Pillow (ImageField de logos)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libreoffice \
        libpq-dev \
        libjpeg-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
