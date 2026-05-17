# --- Stage 1: Base Setup (Alpine) ---
FROM python:3.11-alpine AS python_base

# Python optimizations
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# --- Stage 2: Builder ---
FROM python_base AS builder

# Instalar dependencias del sistema necesarias para compilar
RUN apk add --no-cache \
    gcc \
    musl-dev \
    linux-headers

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias de Python con cache mount para builds más rápidos
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --default-timeout=100 --retries 5 -r requirements.txt

# --- Stage 3: Dev Environment (opcional, para desarrollo local) ---
FROM python_base AS dev

# Instalar herramientas de desarrollo
RUN apk add --no-cache \
    curl \
    git \
    vim \
    netcat-openbsd \
    procps

# Copiar dependencias instaladas desde builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

WORKDIR /app

# Copiar código fuente
COPY . .

# Crear geso.conf por defecto si no existe
RUN if [ ! -f geso.conf ]; then \
      cp .conf.example geso.conf 2>/dev/null || true; \
    fi

# Crear directorio para datos y asegurar permisos
RUN mkdir -p /app/data && \
    chmod 777 /app/data

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# --- Stage 4: Production (The Tiny Image) ---
FROM python_base AS prod

# Copiar dependencias instaladas desde builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

WORKDIR /app

# Copiar código fuente
COPY . .

# Crear geso.conf por defecto si no existe
RUN if [ ! -f geso.conf ]; then \
      cp .conf.example geso.conf 2>/dev/null || true; \
    fi

# Crear directorio para datos y asegurar permisos
RUN mkdir -p /app/data && \
    chmod 777 /app/data

EXPOSE 8000

# Asegurar permisos del directorio de datos antes de iniciar
CMD ["sh", "-c", "chmod -R 777 /app/data 2>/dev/null || true && python init_db.py && exec uvicorn main:app --host 0.0.0.0 --port 8000"]
