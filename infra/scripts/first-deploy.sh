#!/bin/bash
# ─────────────────────────────────────────────────────────────
#  SOOLEVO.COM — Pierwsze wdrożenie (po setup-server.sh)
#  Uruchom z katalogu infra/:
#    sudo ./scripts/first-deploy.sh
# ─────────────────────────────────────────────────────────────

set -euo pipefail

DOMAIN="soolevo.com"
EMAIL="admin@soolevo.com"   # ← ZMIEŃ
INFRA_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "🚀 Pierwsze wdrożenie soolevo.com..."
cd "$INFRA_DIR"

# Sprawdź .env
if [ ! -f ".env" ]; then
    echo "❌ Brak pliku .env! Skopiuj .env.example i uzupełnij zmienne."
    exit 1
fi

# Sprawdź czy zmienne są uzupełnione
if grep -q "ZMIEN_TO" .env; then
    echo "❌ W .env są jeszcze wartości do zmiany (ZMIEN_TO_...)!"
    echo "   Uzupełnij: nano .env"
    exit 1
fi

# ── 1. Uruchom nginx bez SSL (dla certbot challenge) ──────────
echo "📡 Uruchamianie Nginx (HTTP) dla certbot..."
# Tymczasowa konfiguracja nginx bez SSL
cat > nginx/soolevo-init.conf << 'EOF'
server {
    listen 80;
    server_name soolevo.com www.soolevo.com api.soolevo.com;
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    location / { return 200 "OK"; }
}
EOF

cp nginx/soolevo-init.conf nginx/soolevo.conf
docker compose up -d nginx

# ── 2. Uzyskaj certyfikaty SSL ────────────────────────────────
echo "🔐 Pobieranie certyfikatów SSL..."
certbot certonly \
    --webroot \
    -w /var/lib/docker/volumes/"$(basename $INFRA_DIR)"_certbot_www/_data \
    -d "$DOMAIN" \
    -d "www.$DOMAIN" \
    --email "$EMAIL" \
    --agree-tos \
    --non-interactive

certbot certonly \
    --webroot \
    -w /var/lib/docker/volumes/"$(basename $INFRA_DIR)"_certbot_www/_data \
    -d "api.$DOMAIN" \
    --email "$EMAIL" \
    --agree-tos \
    --non-interactive

# ── 3. Przywróć właściwą konfigurację nginx ───────────────────
echo "⚙️  Przywracanie konfiguracji Nginx z SSL..."
cp nginx/soolevo-full.conf nginx/soolevo.conf 2>/dev/null || \
    git checkout nginx/soolevo.conf 2>/dev/null || \
    echo "  → Skopiuj ręcznie nginx/soolevo.conf z repozytorium!"

# ── 4. Build i uruchomienie wszystkich serwisów ───────────────
echo "🏗️  Budowanie obrazów Docker..."
docker compose build --no-cache

echo "🚀 Uruchamianie wszystkich serwisów..."
docker compose up -d

# ── 5. Migracje bazy danych ───────────────────────────────────
echo "🗄️  Uruchamianie migracji bazy danych..."
sleep 5  # poczekaj na start bazy
docker compose exec backend alembic upgrade head

# ── 6. Konfiguracja auto-renewal SSL ─────────────────────────
echo "⏰ Konfiguracja automatycznego odnowienia SSL..."
(crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet && docker compose -f $INFRA_DIR/docker-compose.yml exec nginx nginx -s reload") | crontab -

echo ""
echo "✅ Pierwsze wdrożenie zakończone!"
echo ""
echo "🌐 Aplikacja dostępna pod adresem: https://$DOMAIN"
echo "📊 Status serwisów: docker compose ps"
echo "📋 Logi: docker compose logs -f"
