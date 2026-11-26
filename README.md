# 🛑 RPZ Hazard Domain Sync (BIND / RPZ)

![Language](https://img.shields.io/badge/Language-Python3-blue)
![DNS](https://img.shields.io/badge/DNS-BIND%20RPZ-green)
![Source](https://img.shields.io/badge/Source-hazard.mf.gov.pl-red)
![Status](https://img.shields.io/badge/Status-Production-success)

Skrypt automatycznie synchronizujący **rejestr domen hazardowych Ministerstwa Finansów** z lokalną strefą **BIND RPZ** i przekierowujący je na stronę MF.

> Rejestr domen znajduje się na:  
> https://hazard.mf.gov.pl/api/Register

Skrypt realizuje obowiązek ISP polegający na **blokowaniu i przekierowaniu** domen wpisanych do rejestru MF w ciągu 48h od publikacji.

---

## ⚡ Features
- 🟢 Automatyczne pobieranie XML z MF  
- 🟢 Walidacja ilości domen (ochrona przed błędami API)  
- 🟢 Detekcja zmian przez **hash MD5**  
- 🟢 Generowanie strefy **RPZ** dla BIND  
- 🟢 Obsługa wildcard `*.domena`  
- 🟢 Bezpieczna podmiana plików + `rndc reload`  
- 🟢 Logowanie operacji

---

## 🔧 Jak to działa
1. Cron uruchamia skrypt co 2h  
2. Skrypt pobiera XML z MF  
3. Wyciąga listę domen  
4. Sprawdza czy lista się zmieniła  
5. Generuje plik `hazard.db`  
6. Reloaduje strefę `rpz.hazard` w BIND

---

## ⚠️ Ograniczenia
- 🔴 Brak podpisu kryptograficznego danych MF  
- 🔴 Brak DNSSEC po stronie RPZ  
- 🔴 Zależność od dostępności API MF

---

## 💻 Instalacja

### 📦 Wymagania
- BIND z obsługą RPZ  
- Python 3  
- curl, rndc, named-checkzone  

Instalacja (RHEL / Alma / Rocky):
```bash
dnf install -y bind bind-utils python3 curl
```

---

### 📁 Pliki

Zapisz i uruchom skrypt:
```bash
/etc/named-update_rpz_hazard.py
```

Skrypt stworzy Strefe RPZ:
```bash
/var/named/hazard.db
```

Log dzialania:
```bash
/var/named/data/update_rpz_hazard.log
```

Cache hash:
```bash
/var/named/hazard.list.cache
```

---

### ⚙️ Konfiguracja BIND (`/etc/named.conf`)
```conf
zone "rpz.hazard" {
    type master;
    file "hazard.db";
    check-names ignore;
};
```

---

### ⏱ Cron
```bash
0 */2 * * * /usr/bin/flock -n /tmp/hazard_update.lock /usr/bin/python3 /etc/named-update_rpz_hazard.py
```

---

## 🧪 Test

Sprawdź czy domena z listy MF jest przekierowana:
```bash
dig +short domena-z-rejestru.pl
```

Powinno zwrócić:
```text
145.237.235.240
```

---

## 📚 Źródła
- [Rejestr domen hazardowych MF](https://hazard.mf.gov.pl)  
- Ustawa o grach hazardowych – art. 15f  
