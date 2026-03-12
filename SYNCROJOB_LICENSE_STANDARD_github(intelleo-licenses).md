# ♾️ SYNCROJOB LICENSE PROTECTION STANDARD (2026)

Questo documento definisce lo standard di protezione e validazione delle licenze per la suite di software **SyncroJob** (es. MagoRPA, ISAB_TimeSheet). Utilizza questo file come contesto primario per allineare la validazione delle licenze su nuovi progetti.

## 🎯 LOGICA DI PROTEZIONE
Il sistema si basa su una **validazione cloud-based** integrata con un identificativo hardware univoco (HWID). La licenza locale è un payload cifrato che può essere aperto solo se la chiave derivata dall'HWID della macchina corrente è identica a quella usata durante la generazione.

---

## 🔑 PARAMETRI CRITTOGRAFICI (CRITICO)
Per garantire la compatibilità con il repository cloud `intelleo-licenses` e i tool di generazione, utilizza **SEMPRE** questi parametri:

- **Algoritmo KDF:** PBKDF2HMAC con SHA256.
- **Salt:** `b"SyncroJob_Grace_Salt_2026"` (NON utilizzare salt generici o "BotTS").
- **Iterazioni:** `480000` (Standard OWASP 2023+, allineato a ISAB_TimeSheet).
- **Libreria:** `cryptography.fernet`.

### Derivazione della Chiave (Esempio Python):
```python
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

def get_license_key(hwid: str) -> bytes:
    salt = b"SyncroJob_Grace_Salt_2026"
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    return base64.urlsafe_b64encode(kdf.derive(hwid.encode()))
```

---

## 🖥️ HARDWARE ID (HWID) & NORMALIZZAZIONE
L'HWID deve essere estratto dal **Seriale del Disco Primario** (Windows: WMIC o PowerShell `Win32_DiskDrive`).

### Regole di Normalizzazione:
La causa principale di errori "Invalid Token" è la sporcizia nei dati restituiti dal sistema (null bytes, spazi extra).
1. **Normalizzazione Aggressiva:** Rimuovi spazi, null bytes e caratteri non stampabili.
2. **Caratteri Permessi:** Alfanumerici, trattini `-` e underscore `_`.
3. **Case:** Sempre in **MAIUSCOLO**.
4. **Underscore:** Non rimuovere gli underscore (es. `0025_384C...`) perché sono usati come separatori nei nomi delle cartelle su GitHub.

```python
clean_id = re.sub(r"[^a-zA-Z0-9-_]", "", raw_id).strip().upper()
```

---

## 📁 PERCORSI E SINCRONIZZAZIONE (TOTALE)
La licenza deve essere persistente e ridondante. Il software deve cercare e sincronizzare la licenza in due percorsi:

1. **Locale (Progetto):** `data/Licenza/`
2. **Sistema (AppData):** `%APPDATA%/<NomeApp>/Licenza/` (es. `AppData/Roaming/MagoRPA/Licenza/`)

Se il file esiste in AppData ma non nella cartella locale (o viceversa), l'app deve **auto-sincronizzarli** all'avvio.

---

## ☁️ CLOUD INTEGRATION (GITHUB)
Le licenze sono ospitate su: `github.com/gianky00/intelleo-licenses`.
- **URL Base API:** `https://api.github.com/repos/gianky00/intelleo-licenses/contents/licenses/{hwid}`
- **File richiesti:** `config.dat` (cifrato) e `manifest.json` (contiene l'hash SHA256).
- **Revoca:** Se l'API restituisce **404 Not Found** per un HWID specifico, il client **DEVE cancellare** i file locali e bloccare l'accesso.

---

## ⏳ TRUSTED TIME & GRACE PERIOD
1. **Network Time:** Verifica sempre la scadenza tramite NTP (`pool.ntp.org`). Non fidarti solo dell'orologio locale.
2. **Offline Token:** Crea un file `validity.token` cifrato con l'ultimo timestamp online riuscito.
3. **Grace Period:** Consenti il funzionamento offline per un massimo di **3 giorni** dall'ultimo controllo riuscito.

---

## 🚫 ERRORI COMUNI DA EVITARE
- **Mismatch Salt:** Non usare `BotTS_Fixed_Salt_For_License` (vecchio standard).
- **Iterazioni insufficienti:** Non usare 100.000 (fallisce su licenze nuove).
- **Normalizzazione errata:** Non rimuovere l'underscore, altrimenti GitHub darà 404.
- **Percorso unico:** Se salvi solo in locale, l'utente perde la licenza se sposta la cartella. Usa sempre la sincronizzazione AppData.
