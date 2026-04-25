FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

ADD https://astral.sh/uv/install.sh /install.sh
RUN sh /install.sh && rm /install.sh
ENV PATH="/root/.local/bin:${PATH}"

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .
RUN uv run python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["uv", "run", "opentelemetry-instrument", \
     "--traces_exporter", "otlp", \
     "--metrics_exporter", "otlp", \
     "--logs_exporter", "otlp", \
     "--", "gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120"]
