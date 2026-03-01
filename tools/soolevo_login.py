#!/usr/bin/env python3
"""
════════════════════════════════════════════════════════════════
  soolevo_login.py — Klient CLI konta Soolevo
  Użycie:
    python soolevo_login.py                        # tryb interaktywny
    python soolevo_login.py -e email -p hasło      # argumenty
    python soolevo_login.py --api https://api.soolevo.com  # prod
════════════════════════════════════════════════════════════════
  Wymaga: pip install requests
════════════════════════════════════════════════════════════════
"""

import argparse
import getpass
import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("❌ Brakuje biblioteki 'requests'. Zainstaluj: pip install requests")
    sys.exit(1)

# ── Kolory terminala ──────────────────────────────────────────
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    CYAN   = "\033[96m"
    BLUE   = "\033[94m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    WHITE  = "\033[97m"
    GRAY   = "\033[90m"

def c(color, text): return f"{color}{text}{C.RESET}"
def bold(text):     return c(C.BOLD, text)
def dim(text):      return c(C.DIM + C.GRAY, text)

# ── Stałe ────────────────────────────────────────────────────
DEFAULT_API = "https://api.soolevo.com"
TOKEN_FILE  = Path.home() / ".soolevo_tokens.json"

STATUS_LABELS = {
    "pending":   f"{c(C.YELLOW, '⏳ Oczekuje na płatność')}",
    "paid":      f"{c(C.BLUE,   '💳 Opłacony')}",
    "generated": f"{c(C.GREEN,  '✅ Gotowy do pobrania')}",
    "failed":    f"{c(C.RED,    '❌ Błąd generowania')}",
}


# ════════════════════════════════════════════════════════════
#  KLIENT API
# ════════════════════════════════════════════════════════════
class SoolevoClient:
    def __init__(self, api_base: str):
        self.api      = api_base.rstrip("/")
        self.session  = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.access_token  = None
        self.refresh_token = None

    # ── Auth ─────────────────────────────────────────────────
    def login(self, email: str, password: str) -> dict:
        r = self.session.post(f"{self.api}/api/auth/login",
                              json={"email": email, "password": password},
                              timeout=15)
        r.raise_for_status()
        data = r.json()
        self._store_tokens(data["access_token"], data["refresh_token"])
        return data

    def register(self, email: str, password: str) -> dict:
        r = self.session.post(f"{self.api}/api/auth/register",
                              json={"email": email, "password": password},
                              timeout=15)
        r.raise_for_status()
        data = r.json()
        self._store_tokens(data["access_token"], data["refresh_token"])
        return data

    def me(self) -> dict:
        r = self._get("/api/auth/me")
        return r.json()

    def refresh(self) -> bool:
        if not self.refresh_token:
            return False
        try:
            r = self.session.post(f"{self.api}/api/auth/refresh",
                                  json={"refresh_token": self.refresh_token},
                                  timeout=10)
            r.raise_for_status()
            data = r.json()
            self._store_tokens(data["access_token"], data["refresh_token"])
            return True
        except Exception:
            return False

    # ── Raporty ──────────────────────────────────────────────
    def my_reports(self) -> list:
        r = self._get("/api/reports/my")
        return r.json()

    def download_pdf(self, token: str, out_path: str) -> int:
        url = f"{self.api}/api/reports/download/{token}"
        r   = self.session.get(url, headers=self._auth_headers(), timeout=60, stream=True)
        r.raise_for_status()
        size = 0
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
                size += len(chunk)
        return size

    # ── Internals ────────────────────────────────────────────
    def _store_tokens(self, access: str, refresh: str):
        self.access_token  = access
        self.refresh_token = refresh
        self.session.headers.update({"Authorization": f"Bearer {access}"})
        try:
            TOKEN_FILE.write_text(json.dumps({
                "access_token":  access,
                "refresh_token": refresh,
                "api":           self.api,
            }))
            TOKEN_FILE.chmod(0o600)
        except Exception:
            pass

    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}"} if self.access_token else {}

    def _get(self, path: str) -> requests.Response:
        r = self.session.get(f"{self.api}{path}", timeout=20)
        if r.status_code == 401:
            if self.refresh():
                r = self.session.get(f"{self.api}{path}", timeout=20)
        r.raise_for_status()
        return r

    def load_saved_tokens(self) -> bool:
        """Wczytaj tokeny z pliku (~/.soolevo_tokens.json)."""
        if not TOKEN_FILE.exists():
            return False
        try:
            data = json.loads(TOKEN_FILE.read_text())
            if data.get("api") != self.api:
                return False
            self._store_tokens(data["access_token"], data["refresh_token"])
            return True
        except Exception:
            return False


# ════════════════════════════════════════════════════════════
#  UI HELPERS
# ════════════════════════════════════════════════════════════
def print_banner():
    print()
    print(c(C.CYAN, "  ╔══════════════════════════════════════════╗"))
    print(c(C.CYAN, "  ║") + c(C.BOLD + C.WHITE, "   ☀  Soolevo — Klient konta CLI          ") + c(C.CYAN, "║"))
    print(c(C.CYAN, "  ║") + dim("   soolevo.com · Kalkulator PV              ") + c(C.CYAN, "║"))
    print(c(C.CYAN, "  ╚══════════════════════════════════════════╝"))
    print()

def print_section(title: str):
    print()
    print(c(C.CYAN, "  ─── ") + bold(title))
    print()

def print_report_row(i: int, r: dict):
    """Wyświetl jeden wiersz raportu."""
    # Data
    try:
        dt  = datetime.fromisoformat(r["created_at"].replace("Z", ""))
        dts = dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        dts = r.get("created_at", "—")

    status_str = STATUS_LABELS.get(r["status"], r["status"])
    amount_str = f"  {dim(str(r['amount_pln']) + ' zł')}" if r.get("amount_pln") else ""
    pdf_ready  = "  " + c(C.GREEN, "📄 PDF gotowy") if r.get("pdf_ready") else ""

    print(f"  {dim(str(i).rjust(2) + '.')}  {c(C.GRAY, dts)}  {status_str}{amount_str}{pdf_ready}")
    print(f"       {dim('token: ' + r['token'][:24] + '…')}")
    print()


# ════════════════════════════════════════════════════════════
#  MENU INTERAKTYWNE (dashboard po zalogowaniu)
# ════════════════════════════════════════════════════════════
def dashboard(client: SoolevoClient):
    user = client.me()
    print_section(f"Panel konta: {c(C.WHITE, user['email'])}")

    while True:
        print(f"  {bold('1.')} Pokaż historię raportów")
        print(f"  {bold('2.')} Pobierz PDF raportu")
        print(f"  {bold('3.')} Odśwież listę raportów")
        print(f"  {bold('0.')} Wyloguj i wyjdź")
        print()

        choice = input(c(C.CYAN, "  Wybierz > ")).strip()

        if choice == "0":
            print(dim("\n  Wylogowano. Do zobaczenia! ☀\n"))
            try:
                TOKEN_FILE.unlink()
            except Exception:
                pass
            break

        elif choice in ("1", "3"):
            show_reports(client)

        elif choice == "2":
            download_report(client)

        else:
            print(c(C.YELLOW, "\n  Nieznana opcja. Wpisz 1, 2 lub 0.\n"))


def show_reports(client: SoolevoClient) -> list:
    print_section("Historia raportów")
    try:
        reports = client.my_reports()
    except Exception as e:
        print(c(C.RED, f"  ❌ Błąd pobierania raportów: {e}\n"))
        return []

    if not reports:
        print(c(C.YELLOW, "  Brak raportów. Przejdź na soolevo.com → Kalkulator.\n"))
        return []

    for i, r in enumerate(reports, 1):
        print_report_row(i, r)

    return reports


def download_report(client: SoolevoClient):
    reports = show_reports(client)
    if not reports:
        return

    ready = [r for r in reports if r.get("pdf_ready")]
    if not ready:
        print(c(C.YELLOW, "  Brak raportów gotowych do pobrania.\n"))
        return

    print("  Raporty gotowe do pobrania:")
    for i, r in enumerate(ready, 1):
        print(f"  {bold(str(i) + '.')} {dim(r['token'][:32] + '…')}")
    print()

    choice = input(c(C.CYAN, "  Numer raportu (Enter = anuluj) > ")).strip()
    if not choice:
        return

    try:
        idx = int(choice) - 1
        report = ready[idx]
    except (ValueError, IndexError):
        print(c(C.RED, "  ❌ Nieprawidłowy numer.\n"))
        return

    out = f"raport_soolevo_{report['token'][:8]}.pdf"
    print(f"\n  Pobieranie do: {c(C.WHITE, out)} …")
    try:
        size = client.download_pdf(report["token"], out)
        print(c(C.GREEN, f"  ✅ Pobrano {size // 1024} KB → {out}\n"))
    except Exception as e:
        print(c(C.RED, f"  ❌ Błąd: {e}\n"))


# ════════════════════════════════════════════════════════════
#  LOGOWANIE / REJESTRACJA
# ════════════════════════════════════════════════════════════
def do_login(client: SoolevoClient, email: str = None, password: str = None):
    print_section("Logowanie")

    if not email:
        email    = input(c(C.CYAN, "  Email    > ")).strip()
    else:
        print(f"  Email    : {c(C.WHITE, email)}")

    if not password:
        password = getpass.getpass(c(C.CYAN, "  Hasło    > "))

    try:
        client.login(email, password)
        user = client.me()
        print(c(C.GREEN, f"\n  ✅ Zalogowano jako {user['email']}\n"))
        return True
    except requests.HTTPError as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        print(c(C.RED, f"\n  ❌ Błąd logowania: {detail}\n"))
        return False
    except requests.ConnectionError:
        print(c(C.RED, f"\n  ❌ Nie można połączyć z {client.api}\n"))
        return False


def do_register(client: SoolevoClient):
    print_section("Rejestracja nowego konta")
    email    = input(c(C.CYAN, "  Email          > ")).strip()
    password = getpass.getpass(c(C.CYAN, "  Hasło (min 8)  > "))
    confirm  = getpass.getpass(c(C.CYAN, "  Potwierdź hasło > "))

    if password != confirm:
        print(c(C.RED, "\n  ❌ Hasła nie są identyczne.\n"))
        return False

    try:
        client.register(email, password)
        print(c(C.GREEN, f"\n  ✅ Konto utworzone i zalogowano jako {email}\n"))
        return True
    except requests.HTTPError as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        print(c(C.RED, f"\n  ❌ Błąd: {detail}\n"))
        return False


# ════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(
        description="Soolevo CLI — zarządzaj kontem i raportami PV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Przykłady:\n"
               "  python soolevo_login.py\n"
               "  python soolevo_login.py -e moj@email.pl -p mojehaslo\n"
               "  python soolevo_login.py --api https://api.soolevo.com\n"
    )
    parser.add_argument("-e", "--email",    help="Adres email")
    parser.add_argument("-p", "--password", help="Hasło (bezpieczniej: zostaw puste)")
    parser.add_argument("--api",            default=DEFAULT_API, help=f"URL API (domyślnie: {DEFAULT_API})")
    parser.add_argument("--register",       action="store_true", help="Tryb rejestracji")
    parser.add_argument("--reports",        action="store_true", help="Tylko pokaż raporty i wyjdź")
    args = parser.parse_args()

    print_banner()
    print(dim(f"  API: {args.api}"))
    print()

    client = SoolevoClient(args.api)

    # Próba wczytania zapisanych tokenów
    if not args.register and client.load_saved_tokens():
        try:
            user = client.me()
            print(c(C.GREEN, f"  ✅ Automatyczne logowanie jako {user['email']}"))
            print(dim("     (tokeny zapisane w ~/.soolevo_tokens.json)\n"))
            if args.reports:
                show_reports(client)
            else:
                dashboard(client)
            return
        except Exception:
            pass  # Token wygasł → pełne logowanie

    # Rejestracja lub logowanie
    if args.register:
        ok = do_register(client)
    else:
        # Menu startowe
        if not args.email:
            print(f"  {bold('1.')} Zaloguj się")
            print(f"  {bold('2.')} Zarejestruj nowe konto")
            print(f"  {bold('0.')} Wyjdź")
            print()
            choice = input(c(C.CYAN, "  Wybierz > ")).strip()
            if choice == "0":
                print(dim("\n  Do zobaczenia! ☀\n"))
                return
            elif choice == "2":
                ok = do_register(client)
            else:
                ok = do_login(client, args.email, args.password)
        else:
            ok = do_login(client, args.email, args.password)

    if not ok:
        sys.exit(1)

    if args.reports:
        show_reports(client)
    else:
        dashboard(client)


if __name__ == "__main__":
    main()