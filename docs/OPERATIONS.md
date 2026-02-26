# 📘 Soolevo.com — Dokumentacja Operacyjna

> Wersja: 1.0 | Data: Luty 2025

---

## 🔑 Szybki dostęp

| Zasób | Adres |
|-------|-------|
| Strona główna | https://soolevo.com |
| API | https://api.soolevo.com |
| API docs (Swagger) | https://api.soolevo.com/docs |
| Serwer | SSH: `ssh soolevo@<IP-SERWERA>` |
| Katalog aplikacji | `/opt/soolevo/` |
| Konfiguracja | `/opt/soolevo/infra/.env` |

---

## 🚀 Wdrożenie nowej wersji

### A) Wdrożenie FRONTENDU

```bash
# Na serwerze:
cd /opt/soolevo/infra
./scripts/deploy.sh frontend
```

**Co się dzieje:**
1. `git pull` — pobiera nowy kod
2. `docker compose build frontend` — buduje nowy obraz (npm build)
3. `docker compose up -d --no-deps frontend` — restartuje kontener
4. Zero downtime — stary kontener działa do uruchomienia nowego

---

### B) Wdrożenie BACKENDU

```bash
cd /opt/soolevo/infra
./scripts/deploy.sh backend
```

**Co się dzieje:**
1. `git pull` — pobiera nowy kod
2. `docker compose build backend` — instaluje nowe zależności Python
3. `docker compose up -d --no-deps backend` — restartuje kontener
4. `alembic upgrade head` — uruchamia migracje bazy danych

> ⚠️ **Uwaga:** Jeśli zmieniałeś schematy bazy, utwórz nową migrację Alembic PRZED wdrożeniem!

---

### C) Wdrożenie WSZYSTKIEGO

```bash
cd /opt/soolevo/infra
./scripts/deploy.sh all
```

---

## 📋 Logi

### Logi na żywo (streaming)

```bash
# Wszystkie serwisy
docker compose logs -f

# Tylko backend
docker compose logs -f backend

# Tylko nginx
docker compose logs -f nginx

# Tylko baza danych
docker compose logs -f db
```

### Ostatnie N linii logów

```bash
docker compose logs --tail=100 backend
```

### Logi z konkretnego zakresu czasu

```bash
docker compose logs --since="2025-02-26T10:00:00" backend
```

---

## 🔄 Restart serwisów

```bash
# Restart jednego serwisu
docker compose restart backend
docker compose restart frontend
docker compose restart nginx

# Restart wszystkiego
docker compose restart

# Zatrzymanie i restart z przebudowaniem
docker compose down && docker compose up -d
```

---

## 🔐 Odnowienie certyfikatu SSL

Certyfikaty odnawiają się **automatycznie** — skrypt cron sprawdza co 12h i odnawia jeśli zostało < 30 dni.

### Ręczne odnowienie (jeśli potrzebne)

```bash
# Na serwerze (jako root lub sudo):
certbot renew --quiet

# Przeładuj Nginx żeby załadował nowe certyfikaty
docker compose exec nginx nginx -s reload
```

### Sprawdzenie daty wygaśnięcia

```bash
certbot certificates
```

---

## 🔋 Zarządzanie magazynami energii

### Dodanie nowego produktu (Faza 1 — JSON)

Edytuj plik `/opt/soolevo/backend/app/data/batteries.json`:

```bash
nano /opt/soolevo/backend/app/data/batteries.json
```

Schemat produktu:
```json
{
  "id": 9,
  "name": "Nazwa modelu",
  "brand": "Marka",
  "capacity_kwh": 10.0,
  "price_pln": 15000,
  "warranty_years": 10,
  "chemistry": "LFP",
  "max_power_kw": 5.0,
  "cycles": 6000,
  "dod_percent": 90,
  "efficiency_percent": 96,
  "weight_kg": 100,
  "description": "Opis produktu.",
  "tags": ["lfp", "modularny"],
  "specs_json": {}
}
```

Po zapisaniu pliku — **nie ma potrzeby restartowania** — backend odczytuje plik przy każdym zapytaniu.

### Dodanie produktu przez API (Faza 2 — baza danych)

```bash
# Przez psql na serwerze
docker compose exec db psql -U soolevo -d soolevo
INSERT INTO batteries (name, brand, capacity_kwh, price_pln, ...) VALUES (...);
```

---

## 🗄️ Baza danych

### Połączenie z bazą

```bash
docker compose exec db psql -U soolevo -d soolevo
```

### Backup bazy

```bash
# Ręczny backup
docker compose exec db pg_dump -U soolevo soolevo > backup_$(date +%Y%m%d).sql

# Restore
cat backup_20250226.sql | docker compose exec -T db psql -U soolevo soolevo
```

### Status płatności — podgląd

```sql
-- Wszystkie płatności z ostatnich 7 dni
SELECT p.id, p.status, p.amount_groszy/100.0 as pln, p.confirmed_at, r.token
FROM payments p JOIN reports r ON p.report_id = r.id
WHERE p.created_at > NOW() - INTERVAL '7 days'
ORDER BY p.created_at DESC;
```

---

## 🔧 Zmienne środowiskowe

Plik: `/opt/soolevo/infra/.env`

```bash
nano /opt/soolevo/infra/.env
```

Po zmianie zmiennych środowiskowych — **restart backendu wymagany**:
```bash
docker compose restart backend
```

---

## 📊 Status serwisów

```bash
# Szybki przegląd
docker compose ps

# Zużycie zasobów
docker stats
```

Oczekiwany output `docker compose ps`:
```
NAME              STATUS         PORTS
soolevo-backend   running        0.0.0.0:8000
soolevo-db        running        5432/tcp
soolevo-frontend  running        80/tcp
soolevo-nginx     running        0.0.0.0:80->80, 0.0.0.0:443->443
soolevo-redis     running        6379/tcp
```

---

## 🆘 Troubleshooting

### Backend nie startuje

```bash
docker compose logs backend | tail -50
```
Najczęstsze przyczyny:
- Błąd połączenia z bazą → sprawdź `DATABASE_URL` w `.env`
- Błąd importu Python → sprawdź `requirements.txt`

### PDF nie generuje się po płatności

```bash
docker compose logs backend | grep "PDF\|paynow\|webhook"
```
Sprawdź:
- `PAYNOW_SIGNATURE_KEY` — musi być identyczny jak w panelu PayNow
- Webhook URL w panelu PayNow: `https://api.soolevo.com/webhooks/paynow`

### Nginx 502 Bad Gateway

```bash
docker compose ps backend  # czy backend działa?
docker compose restart backend
```

### Certyfikat SSL wygasł

```bash
certbot renew --force-renewal
docker compose exec nginx nginx -s reload
```

---

## 📞 Kontakty techniczne

- **PayNow support:** https://docs.paynow.pl/
- **Docker docs:** https://docs.docker.com/compose/
- **FastAPI docs:** https://fastapi.tiangolo.com/
- **Let's Encrypt status:** https://letsencrypt.status.io/
