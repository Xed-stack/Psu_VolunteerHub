FROM node:22-bookworm-slim AS ui-build
WORKDIR /ui
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund
COPY ui ./ui
COPY templates ./templates
COPY static/scripts ./static/scripts
RUN npm run build

FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 APP_ENV=production \
    PRIVATE_UPLOAD_FOLDER=/data/private
WORKDIR /app

# mysqlclient is already part of the project's pinned dependencies.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential pkg-config default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Explicit allowlist: no dumps, local uploads, .env, Git history or QA artifacts.
COPY app ./app
COPY templates ./templates
COPY static ./static
COPY --from=ui-build /ui/static/styles/app.css ./static/styles/app.css
COPY migrations ./migrations
COPY data/historical_activities_2020_2025.csv ./data/historical_activities_2020_2025.csv
COPY config.py wsgi.py ./
RUN ln -s /data/public /app/static/uploads

# Railway mounts /data at runtime. No schema setup or seeding in startup/build.
CMD ["sh", "-c", "mkdir -p /data/public /data/private && exec gunicorn --bind 0.0.0.0:${PORT:-8000} --workers 1 --worker-class gthread --threads 4 --timeout 120 wsgi:app"]
