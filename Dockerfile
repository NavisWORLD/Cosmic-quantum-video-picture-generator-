FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    COSMOS_API_HOST=0.0.0.0 \
    COSMOS_API_PORT=8788

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md LICENSE NOTICE.md ./
COPY src ./src
COPY apps ./apps
RUN pip install --no-cache-dir ".[server,media]"

RUN mkdir -p /app/out /app/.cosmos-media
VOLUME ["/app/out", "/app/.cosmos-media"]
EXPOSE 8788

CMD ["cosmos-media", "serve", "--host", "0.0.0.0", "--port", "8788"]
