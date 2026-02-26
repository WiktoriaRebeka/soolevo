# ─────────────────────────────────────────────────────────────
#  Backend FastAPI — Dockerfile
#  WeasyPrint wymaga systemowych zależności GTK/Pango
# ─────────────────────────────────────────────────────────────

FROM python:3.11-slim

# Zależności systemowe dla WeasyPrint
RUN apt-get update && apt-get install -y --no-install-recommends \
    # WeasyPrint deps
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libffi-dev \
    libjpeg-dev \
    libopenjp2-7 \
    libgdk-pixbuf2.0-0 \
    libcairo2 \
    # Inne
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Zależności Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kod aplikacji
COPY . .

# Katalog na raporty PDF
RUN mkdir -p /app/reports

EXPOSE 8000

# Uruchomienie z Gunicorn (produkcja) lub Uvicorn (dev)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
