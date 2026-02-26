#!/bin/bash
# ─────────────────────────────────────────────────────────────
#  SOOLEVO.COM — Skrypt wdrożenia aktualizacji
#  Użycie:
#    ./deploy.sh             → wdroż wszystko
#    ./deploy.sh frontend    → tylko frontend
#    ./deploy.sh backend     → tylko backend
# ─────────────────────────────────────────────────────────────

set -euo pipefail

INFRA_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ROOT_DIR="$(cd "$INFRA_DIR/.." && pwd)"
TARGET="${1:-all}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

cd "$INFRA_DIR"

echo "🚀 Soolevo Deploy [$TARGET] — $TIMESTAMP"

# ── Pobierz najnowszy kod ─────────────────────────────────────
echo "📥 git pull..."
cd "$ROOT_DIR"
git pull origin main

cd "$INFRA_DIR"

deploy_frontend() {
    echo "🎨 Deploy frontendu..."
    docker compose build frontend
    docker compose up -d --no-deps frontend
    echo "✅ Frontend wdrożony!"
}

deploy_backend() {
    echo "⚙️  Deploy backendu..."
    docker compose build backend
    docker compose up -d --no-deps backend
    echo "⏳ Czekam na start backendu..."
    sleep 5
    # Migracje (bezpieczne — tylko jeśli są zmiany)
    docker compose exec backend alembic upgrade head
    echo "✅ Backend wdrożony!"
}

case "$TARGET" in
    frontend) deploy_frontend ;;
    backend)  deploy_backend ;;
    all)
        deploy_backend
        deploy_frontend
        docker compose exec nginx nginx -s reload
        echo "✅ Wszystko wdrożone!"
        ;;
    *)
        echo "❌ Nieznany cel: $TARGET"
        echo "   Użycie: ./deploy.sh [frontend|backend|all]"
        exit 1
        ;;
esac

echo ""
echo "📊 Status:"
docker compose ps
echo ""
echo "📋 Logi (Ctrl+C żeby wyjść):"
docker compose logs --tail=20 "$TARGET" 2>/dev/null || docker compose logs --tail=20
