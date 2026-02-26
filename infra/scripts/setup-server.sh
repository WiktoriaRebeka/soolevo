#!/bin/bash
# ─────────────────────────────────────────────────────────────
#  SOOLEVO.COM — Skrypt konfiguracji serwera (Ubuntu 22.04)
#  Uruchom JEDNORAZOWO jako root:
#    curl -sSL https://raw.githubusercontent.com/.../setup.sh | bash
#  LUB:
#    chmod +x setup.sh && sudo ./setup.sh
# ─────────────────────────────────────────────────────────────

set -euo pipefail

DOMAIN="soolevo.com"
APP_USER="soolevo"
APP_DIR="/opt/soolevo"
EMAIL="admin@soolevo.com"   # ← ZMIEŃ na swój email (dla Let's Encrypt)

echo "🚀 Konfiguracja serwera dla $DOMAIN..."

# ── 1. Aktualizacja systemu ───────────────────────────────────
echo "📦 Aktualizacja pakietów..."
apt-get update && apt-get upgrade -y
apt-get install -y curl git ufw htop unzip

# ── 2. Docker ─────────────────────────────────────────────────
echo "🐳 Instalacja Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | bash
    systemctl enable docker
    systemctl start docker
fi

# Docker Compose plugin
apt-get install -y docker-compose-plugin
docker compose version

# ── 3. Użytkownik aplikacji ────────────────────────────────────
echo "👤 Tworzenie użytkownika $APP_USER..."
if ! id "$APP_USER" &>/dev/null; then
    useradd -m -s /bin/bash "$APP_USER"
    usermod -aG docker "$APP_USER"
fi

# ── 4. Firewall UFW ───────────────────────────────────────────
echo "🔥 Konfiguracja firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh       # port 22
ufw allow http      # port 80
ufw allow https     # port 443
ufw --force enable
ufw status

# ── 5. Katalog aplikacji ──────────────────────────────────────
echo "📁 Przygotowanie katalogu $APP_DIR..."
mkdir -p "$APP_DIR"
chown "$APP_USER:$APP_USER" "$APP_DIR"

# ── 6. Klonowanie repo (zastąp URL swoim repo) ────────────────
echo "📥 Klonowanie repozytorium..."
if [ ! -d "$APP_DIR/.git" ]; then
    sudo -u "$APP_USER" git clone https://github.com/TWOJ_LOGIN/soolevo.git "$APP_DIR"
else
    echo "  → Repo już istnieje, pomijam klonowanie."
fi

# ── 7. Konfiguracja .env ──────────────────────────────────────
echo "⚙️  Kopiowanie .env..."
if [ ! -f "$APP_DIR/infra/.env" ]; then
    cp "$APP_DIR/infra/.env.example" "$APP_DIR/infra/.env"
    echo ""
    echo "⚠️  WAŻNE: Uzupełnij zmienne w $APP_DIR/infra/.env!"
    echo "   nano $APP_DIR/infra/.env"
fi

# ── 8. Certbot — SSL ──────────────────────────────────────────
echo "🔐 Instalacja Certbot..."
apt-get install -y certbot

echo ""
echo "✅ Konfiguracja serwera zakończona!"
echo ""
echo "📋 Następne kroki:"
echo "   1. Uzupełnij $APP_DIR/infra/.env"
echo "   2. Ustaw DNS: soolevo.com i api.soolevo.com → $(curl -s ifconfig.me)"
echo "   3. Poczekaj na propagację DNS (do 15 min)"
echo "   4. Uruchom: cd $APP_DIR/infra && sudo ./scripts/first-deploy.sh"
