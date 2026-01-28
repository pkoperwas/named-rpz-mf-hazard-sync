#!/usr/bin/python3
import subprocess
import re
import os
import hashlib
from datetime import datetime

# --- KONFIGURACJA ---
URL_XML = "https://hazard.mf.gov.pl/api/Register"
ZONE_FILE = "/var/named/hazard.db"
# Plik cache do przechowywania podpisu poprzedniej listy domen
CACHE_FILE = "/var/named/hazard.list.cache"
REDIRECT_IP = "145.237.235.240"
LOG_FILE = "/var/named/data/update_rpz_hazard.log"
SERIAL = datetime.now().strftime("%Y%m%d%H")

# --- PEŁNE ŚCIEŻKI DO BINARIÓW ---
CURL_BIN = "/usr/bin/curl"
CHOWN_BIN = "/usr/bin/chown"
NAMED_CHECKZONE_BIN = "/usr/sbin/named-checkzone"
RNDC_BIN = "/usr/sbin/rndc"

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] {message}"
    print(formatted_message)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(formatted_message + "\n")
    except Exception as e:
        print(f"BŁĄD LOGOWANIA: {e}")

def generate_rpz():
    log("=== Rozpoczynam cykl aktualizacji RPZ ===")
    
    try:
        # 1. Pobieranie danych
        log(f"Pobieranie XML z {URL_XML}...")
        cmd_curl = [CURL_BIN, "-k", "-s", "-L", "--compressed", "--connect-timeout", "60", URL_XML]
        result = subprocess.run(cmd_curl, capture_output=True)
        
        if result.returncode != 0 or not result.stdout:
            log("BŁĄD: Serwer MF nie odpowiada.")
            return

        content = result.stdout.decode('utf-8', errors='ignore')

        # 2. Wyciąganie domen
        raw_domains = re.findall(r'<(?:[^:>]*:)?(?:AdresDomeny|Address)[^>]*>([^<]+)</(?:[^:>]*:)?(?:AdresDomeny|Address)>', content, re.IGNORECASE)
        
        # Tworzymy posortowaną listę unikalnych domen
        domains = sorted(list(set(d.strip().lower() for d in raw_domains if "." in d and len(d) > 3)))

        count = len(domains)
        if count < 1000:
            log(f"BŁĄD: Wykryto tylko {count} domen. Przerywam.")
            return

        # 3. SPRAWDZANIE ZMIAN PRZEZ HASH CZYSZCZONEJ LISTY
        new_hash = hashlib.md5("\n".join(domains).encode()).hexdigest()
        
        old_hash = ""
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r") as f:
                old_hash = f.read().strip()

        if new_hash == old_hash:
            log(f"INFO: Lista {count} domen jest identyczna z poprzednią. Brak pracy do wykonania.")
            log("=== Koniec cyklu (brak zmian) ===\n")
            return

        log(f"Wykryto zmiany (nowe/usunięte domeny). Przetworzono {count} unikalnych domen.")

        # 4. Budowanie nowej strefy
        header = f"""$TTL 60
@             IN  SOA  localhost. root.localhost.  (
                          {SERIAL} ; serial
                          3H         ; refresh
                          1H         ; retry
                          1W         ; expire
                          1H )       ; minimum
             IN  NS   localhost.

; --- Reguły RPZ (Redirect to: {REDIRECT_IP}) ---
"""
        
        temp_file = ZONE_FILE + ".tmp"
        with open(temp_file, "w") as f:
            f.write(header)
            for d in domains:
                f.write(f"{d} IN A {REDIRECT_IP}\n")
                f.write(f"*.{d} IN A {REDIRECT_IP}\n")

        # 5. Podmiana plików i zapis nowego hasha do cache
        os.chmod(temp_file, 0o640)
        subprocess.run([CHOWN_BIN, "root:named", temp_file])
        os.replace(temp_file, ZONE_FILE)
        
        # Zapisujemy hash nowej listy, żeby przy kolejnym ruruchomieniu wiedzieć, że już to mamy
        with open(CACHE_FILE, "w") as f:
            f.write(new_hash)
            
        log("Plik strefy zaktualizowany i hash zapisany w cache.")

        # 6. RNDC RELOAD
        check = subprocess.run([NAMED_CHECKZONE_BIN, "-k", "ignore", "rpz.hazard", ZONE_FILE], capture_output=True, text=True)
        if check.returncode == 0:
            reload_res = subprocess.run([RNDC_BIN, "reload", "rpz.hazard"], capture_output=True, text=True)
            log(f"SUKCES RNDC: {reload_res.stdout.strip() or reload_res.stderr.strip()}")
        else:
            log(f"BŁĄD SKŁADNI: {check.stderr.strip()}")

    except Exception as e:
        log(f"KRYTYCZNY WYJĄTEK: {str(e)}")
    
    log("=== Koniec cyklu aktualizacji ===\n")

if __name__ == "__main__":
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f: pass
        os.chmod(LOG_FILE, 0o640)
    generate_rpz()
