# ANAF e-Factura PDF Downloader Bot 🇷🇴 🇬🇧

*   [🇷🇴 Română](#-română)
*   [🇬🇧 English](#-english)

---

## 🇷🇴 Română

Aplicație desktop locală în Python pentru automatizarea descărcării și sortării facturilor din sistemul oficial ANAF e-Factura în format PDF direct în foldere locale sau sincronizate în Cloud.

Scapă de conversiile manuale de XML în PDF factură cu factură. Conectezi stick-ul cu semnătura digitală, pornești aplicația și sincronizezi totul cu un singur click.

### ✨ Facilități
*   **Logare cu 1 Click**: Autentificare simplă prin portalul oficial ANAF OAuth direct cu stick-ul (token-ul digital).
*   **Conversie Automată în PDF**: Descarcă automat fișierele XML originale din API-ul ANAF și le convertește în formatul PDF oficial ANAF.
*   **Sortare Inteligentă**: Clasifică facturile automat în structura de foldere dorită:
    *   `FACTURA TRIMISĂ` (Vânzări / Venituri) ➔ folderul `IN/`
    *   `FACTURA PRIMITĂ` (Achiziții / Cheltuieli) ➔ folderul `OUT/`
*   **Structură Foldere Personalizabilă**: Poți alege formatul folderelor create din setări (Ex: `{year}/{month}/{direction}` sau `{direction}/{year}/{month}`).
*   **Protecție Duplicate**: Detectează dacă o factură a fost descărcată deja (în formatul botului, formatul vechi sau cel manual `[ID].pdf`), o omite pentru a economisi apeluri API și o redenumește pentru uniformitate.
*   **Deduplicare automată**: Dacă există ambele formate pe disk, botul șterge automat dublura simplă (`[ID].pdf`) și păstrează varianta standardizată.
*   **Panou Control Local**: Dashboard modern în browser cu jurnalizare în timp real (logs).

---

### 🚀 Ghid Rapid de Pornire

#### 1. Instalare
1.  Descarcă sau clonează acest folder pe calculatorul tău (Ex: în `C:\ANAFBOT` sau `D:\ANAFBOT`).
2.  Redenumește fișierul **`config.example.json`** în **`config.json`**.

#### 2. Pornire
1.  Conectează stick-ul cu semnătura digitală la calculator.
2.  Pornește launcher-ul corespunzător sistemului tău de operare:
    *   **Windows**: Dublu-click pe **`run.bat`**
    *   **macOS / Linux**: Deschide Terminalul în acest folder, fă scriptul executabil și rulează-l:
        ```bash
        chmod +x run.sh
        ./run.sh
        ```
    *   *Notă: La prima pornire, aplicația va instala automat toate librăriile Python necesare (FastAPI, Requests, cryptography etc.).*
3.  Serverul local va porni și browserul tău se va deschide automat la adresa:
    `http://127.0.0.1:8000` (sau `https://127.0.0.1:8000` dacă activezi HTTPS).

---

### 🔑 Configurare profil dezvoltator ANAF
Pentru a conecta botul la serverul ANAF, trebuie să creezi o aplicație gratuită pe portalul lor:

1.  Accesează portalul [ANAF OAuth Inregistrare](https://www.anaf.ro/InregOauth/Adaugare.xhtml) (cu stick-ul conectat).
2.  Mergi pe tab-ul **"Editare profil Oauth"** din header-ul paginii.
3.  Completează formularul:
    *   **Denumire aplicație**: `ANAFBot`
    *   **Callback URL 1**: `http://127.0.0.1:8000/callback` (sau `https://127.0.0.1:8000/callback` dacă vrei conexiune securizată).
    *   **Serviciu**: Bifează **DOAR "E-Factura"** (Debifează "E-Transport"). Dacă bifezi și E-Transport, portalul poate returna o eroare internă HTTP 400 Bad Request.
4.  Apasă pe **"Generare Client ID"**. Datele aplicației tale vor apărea în tabelul de mai jos.
5.  Copiază **Client ID** și **Client Secret** în setările Dashboard-ului botului, adaugă **CIF-ul** tău (fără "RO" și fără spații) și apasă pe **Salvează Setările**.

---

### 🛠️ Depanare: Conexiune Securizată (HTTPS local)
Dacă ai înregistrat pe portalul ANAF un URL cu `https://` și browserul se redirecționează cu eroarea "This site can't provide a secure connection" sau `ERR_SSL_PROTOCOL_ERROR`:

1.  În setările din stânga Dashboard-ului botului, asigură-te că **OAuth Redirect URL înregistrat** începe cu `https://127.0.0.1:8000/callback`.
2.  Salvează setările și restart-ează aplicația (`run.bat` / `run.sh`).
3.  Botul va genera automat un certificat SSL local (`cert.pem` / `key.pem`) și va porni pe HTTPS.
4.  Când browserul se deschide la `https://127.0.0.1:8000`, vei vedea un ecran de avertizare ("Your connection is not private"). 
5.  Apasă pe **"Advanced"** (Avansat) și alege **"Proceed to 127.0.0.1 (unsafe) / Continuați spre 127.0.0.1 (nesigur)"**. Autentificarea va fi acum 100% automată!

---

### 📁 Structuri Personalizate de Foldere
Poți schimba formatul folderelor create din setările aplicației folosind variabile dinamice:

*   `{year}`: Anul facturii (Ex: `2026`).
*   `{month}`: Numele lunii formatat cu index (Ex: `07_Iulie`).
*   `{raw_month}`: Indexul numeric al lunii format din 2 cifre (Ex: `07`).
*   `{direction}`: Direcția facturii (`IN` sau `OUT`).
*   `{cui}`: CIF-ul companiei tale (Ex: `49430531`).

#### Exemple:
*   `{year}/{month}/{direction}` (Implicit) ➔ `An/Lună/IN-OUT` (Ex: `2026/07_Iulie/IN/16-06-2026_ID.pdf`)
*   `{direction}/{year}/{month}` ➔ `IN-OUT/An/Lună`
*   `{cui}/{year}-{raw_month}/{direction}` ➔ Sortează după CUI și dată numerică

---
---

## 🇬🇧 English

A local desktop Python application to automate the downloading and sorting of your official ANAF e-Factura invoices as PDFs directly into your local folders or cloud-synced drives.

No manual PDF conversions, no complicated scripts. Just plugin your USB token, start the app, and sync with one click.

### ✨ Features
*   **One-Click Login**: Simple OAuth authorization through ANAF's official digital certificate portal.
*   **Automatic PDF Generation**: Seamlessly downloads invoice ZIP files from the ANAF API and converts the internal XML files to official ANAF-styled PDFs.
*   **Smart Folder Sorting**: Categorizes invoices automatically into your folder structure:
    *   `FACTURA TRIMISĂ` (Sent / Income) ➔ `IN/` folder
    *   `FACTURA PRIMITĂ` (Received / Expense) ➔ `OUT/` folder
*   **Customizable Folder Structures**: Set your preferred layout dynamically, e.g. `{year}/{month}/{direction}` or `{direction}/{year}/{month}`.
*   **Safety Deduplication**: Automatically detects existing files on disk (supporting multiple naming formats), skips downloading them again to save API calls, and standardizes file names.
*   **Auto-Cleanup**: If duplicate manual and bot formats co-exist, it will safely delete the plain manual duplicate (`[ID].pdf`) and keep the standardized date formatted file.
*   **Local Web Dashboard**: Modern, glassmorphism-designed local dashboard with live logging.

---

### 🚀 Quick Start Guide

#### 1. Installation
1.  Download or clone this repository to your computer (e.g., in `C:\ANAFBOT` or `D:\ANAFBOT`).
2.  Duplicate the template configuration file `config.example.json` and rename the copy to **`config.json`**.

#### 2. Startup
1.  Plug in your physical digital signature USB token (token digital).
2.  Start the application launcher matching your Operating System:
    *   **Windows**: Double-click **`run.bat`**
    *   **macOS / Union**: Open your Terminal, navigate to the folder, make the script executable (`chmod +x run.sh`), and run it:
        ```bash
        chmod +x run.sh
        ./run.sh
        ```
    *   *Note: On your first launch, the script will automatically check and install all required python dependencies (FastAPI, Requests, cryptography, etc.).*
3.  The bot server will boot, and your default web browser will automatically open:
    `http://127.0.0.1:8000` (or `https://127.0.0.1:8000` depending on your config.json redirect settings).

---

### 🔑 Initial Setup: ANAF Developer Profile
To connect the bot to the live ANAF API, you need to register a free developer app profile:

1.  Access the portal [ANAF OAuth registration portal](https://www.anaf.ro/InregOauth/Adaugare.xhtml) (ensure your token is plugged in).
2.  Select the **"Editare profil Oauth"** tab in the top header (if not already selected).
3.  Fill out the application form:
    *   **Denumire aplicație**: `ANAFBot`
    *   **Callback URL 1**: `http://127.0.0.1:8000/callback` (or `https://127.0.0.1:8000/callback` if you want a secure connection).
    *   **Serviciu**: Select **ONLY "E-Factura"** (uncheck E-Transport). If you check E-Transport, the portal might return an internal HTTP 400 error.
4.  Click **"Generare Client ID"**. Your application credentials will appear in the table below.
5.  Open your bot dashboard (`http://127.0.0.1:8000`) and paste the **Client ID**, **Client Secret**, and your **CIF/CUI** (only digits, no "RO"). Click **Save Settings**.

---

### 🛠️ Troubleshooting: ERR_SSL_PROTOCOL_ERROR
If you registered an HTTPS callback URL and the browser redirects you with a secure connection error (`ERR_SSL_PROTOCOL_ERROR`):

1.  In the settings on the left, ensure your **OAuth Redirect URL înregistrat** starts with `https://127.0.0.1:8000/callback`.
2.  Save settings and restart the launcher (`run.bat` / `run.sh`).
3.  The bot will automatically generate local SSL certificates (`cert.pem` / `key.pem`) and start on HTTPS.
4.  When your browser opens at `https://127.0.0.1:8000`, click **"Advanced"** and select **"Proceed to 127.0.0.1 (unsafe)"**.
5.  Click **Conectează ANAF** and authorization will now complete 100% automatically!

---

### 📁 Custom Folder Structures
You can customize exactly how directories are created and structured on your drive via the **Structură Foldere** settings field.

#### Available variables:
*   `{year}`: Year of the invoice (e.g. `2026`).
*   `{month}`: Month formatted with index and Romanian name (e.g. `07_Iulie`).
*   `{raw_month}`: Two-digit index of the month (e.g. `07`).
*   `{direction}`: Direction folder (`IN` or `OUT`).
*   `{cui}`: Your company's VAT number (e.g. `49430531`).

#### Examples:
*   `{year}/{month}/{direction}` (Default) ➔ `D:\PALY S.R.L\2026\07_Iulie\IN\16-06-2026_ID.pdf`
*   `{direction}/{year}/{month}` ➔ `D:\PALY S.R.L\IN\2026\07_Iulie\16-06-2026_ID.pdf`
*   `{cui}/{year}-{raw_month}/{direction}` ➔ `D:\PALY S.R.L\49430531\2026-07\IN\16-06-2026_ID.pdf`
