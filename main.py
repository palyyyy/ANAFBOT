import os
import json
import time
import zipfile
import io
import datetime
import logging
import threading
import webbrowser
from typing import Dict, Any, List, Optional
import requests
import re
from fastapi import FastAPI, Request, HTTPException, Query, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ANAFBot")

app = FastAPI(title="ANAF e-Factura Downloader")

@app.on_event("startup")
def open_browser():
    def open_url():
        time.sleep(1.5)
        try:
            config = load_config()
            redirect_uri = config.get("redirect_uri", "")
            scheme = "https" if redirect_uri.lower().startswith("https://") else "http"
            logger.info(f"Opening dashboard in your web browser ({scheme})...")
            webbrowser.open(f"{scheme}://127.0.0.1:8000/")
        except Exception as e:
            logger.error(f"Failed to open browser automatically: {str(e)}")
    threading.Thread(target=open_url, daemon=True).start()

# CORS middleware for local web UI

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
GUI_DIR = os.path.join(os.path.dirname(__file__), "gui")

# Global in-memory log buffer to stream logs to UI
log_stream = []

class UIHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        log_stream.append({
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
            "level": record.levelname,
            "message": record.getMessage()
        })
        if len(log_stream) > 500:
            log_stream.pop(0)

ui_handler = UIHandler()
ui_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(ui_handler)

MONTHS_MAP = {
    "01": "01_Ianuarie",
    "02": "02_Februarie",
    "03": "03_Martie",
    "04": "04_Aprilie",
    "05": "05_Mai",
    "06": "06_Iunie",
    "07": "07_Iulie",
    "08": "08_August",
    "09": "09_Septembrie",
    "10": "10_Octombrie",
    "11": "11_Noiembrie",
    "12": "12_Decembrie"
}

def parse_message_date(date_str: str) -> Optional[tuple[str, str, str]]:
    if not date_str:
        return None
    # Try ISO format "YYYY-MM-DD..." (e.g. 2026-07-20T10:00:00)
    if len(date_str) >= 10 and date_str[4] == '-' and date_str[7] == '-':
        return date_str[0:4], date_str[5:7], date_str[8:10]
    # Try Romanian format "DD/MM/YYYY..." or "DD-MM-YYYY..." or "DD.MM.YYYY..."
    if len(date_str) >= 10 and (date_str[2] in ('/', '-', '.') and date_str[5] in ('/', '-', '.')):
        return date_str[6:10], date_str[3:5], date_str[0:2]
    # Try continuous digits "YYYYMMDD..."
    digits = "".join(c for c in date_str if c.isdigit())
    if len(digits) >= 8:
        if 2020 <= int(digits[0:4]) <= 2099:
            return digits[0:4], digits[4:6], digits[6:8]
        elif 2020 <= int(digits[4:8]) <= 2099:
            return digits[4:8], digits[2:4], digits[0:2]
    return None


def load_config() -> Dict[str, Any]:
    if not os.path.exists(CONFIG_PATH):
        default = {
            "cif": "",
            "client_id": "",
            "client_secret": "",
            "target_dir": "",
            "test_dir": "test_sync",
            "test_mode": True,
            "invert_in_out": True,
            "redirect_uri": "http://localhost:8000/callback",
            "folder_structure": "{year}/{month}/{direction}",
            "days": 30,
            "tokens": {
                "access_token": "",
                "refresh_token": "",
                "access_expires_at": 0,
                "refresh_expires_at": 0
            }
        }
        save_config(default)
        return default
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(config: Dict[str, Any]):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def get_valid_token(config: Dict[str, Any]) -> Optional[str]:
    tokens = config.get("tokens", {})
    access_token = tokens.get("access_token")
    access_expires_at = tokens.get("access_expires_at", 0)
    refresh_token = tokens.get("refresh_token")
    refresh_expires_at = tokens.get("refresh_expires_at", 0)
    
    current_time = int(time.time())
    
    if access_token and current_time < access_expires_at - 300: # 5 min buffer
        return access_token
        
    # If access token is expired but refresh token is valid, refresh it
    if refresh_token and current_time < refresh_expires_at - 300:
        logger.info("Access token expired or expiring soon. Attempting to refresh using refresh token...")
        url = "https://logincert.anaf.ro/anaf-oauth2/v1/token"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": config.get("client_id"),
            "client_secret": config.get("client_secret")
        }
        try:
            res = requests.post(url, data=payload, timeout=15)
            if res.status_code == 200:
                data = res.json()
                new_access = data.get("access_token")
                new_refresh = data.get("refresh_token", refresh_token) # sometimes it doesn't return a new refresh token
                expires_in = int(data.get("expires_in", 7776000)) # default 90 days in seconds
                
                # refresh token usually stays valid for 365 days
                tokens["access_token"] = new_access
                tokens["refresh_token"] = new_refresh
                tokens["access_expires_at"] = current_time + expires_in
                # Keep original refresh expiration or update if server provided new one
                if "refresh_token" in data:
                    tokens["refresh_expires_at"] = current_time + 31536000 # 365 days
                
                config["tokens"] = tokens
                save_config(config)
                logger.info("Tokens successfully refreshed!")
                return new_access
            else:
                logger.error(f"Failed to refresh token: {res.status_code} - {res.text}")
        except Exception as e:
            logger.error(f"Error during token refresh: {str(e)}")
            
    return None

# Endpoints
@app.get("/api/config")
def get_config_endpoint():
    return load_config()

@app.post("/api/config")
def save_config_endpoint(new_config: Dict[str, Any]):
    current = load_config()
    # Preserving token cache when saving settings
    tokens = current.get("tokens", {})
    current.update(new_config)
    current["tokens"] = tokens
    save_config(current)
    logger.info("Configuration updated successfully.")
    return {"status": "ok"}

@app.get("/api/status")
def get_status_endpoint():
    config = load_config()
    tokens = config.get("tokens", {})
    access_token = tokens.get("access_token")
    access_expires_at = tokens.get("access_expires_at", 0)
    refresh_token = tokens.get("refresh_token")
    refresh_expires_at = tokens.get("refresh_expires_at", 0)
    
    current_time = int(time.time())
    
    status = "disconnected"
    access_days = 0
    refresh_days = 0
    
    if access_token and current_time < access_expires_at:
        status = "connected"
        access_days = max(0, int((access_expires_at - current_time) / 86400))
        refresh_days = max(0, int((refresh_expires_at - current_time) / 86400))
    elif refresh_token and current_time < refresh_expires_at:
        status = "needs_refresh"
        refresh_days = max(0, int((refresh_expires_at - current_time) / 86400))
        
    return {
        "status": status,
        "access_days_remaining": access_days,
        "refresh_days_remaining": refresh_days,
        "cif": config.get("cif"),
        "client_id": config.get("client_id")
    }

@app.get("/api/connect")
def connect_endpoint(request: Request):
    config = load_config()
    client_id = config.get("client_id")
    if not client_id:
        raise HTTPException(status_code=400, detail="Client ID is required in configurations before connecting.")
    
    # Retrieve Redirect URL directly from user configurations to ensure absolute match
    redirect_uri = config.get("redirect_uri", "http://localhost:8000/callback")
    
    auth_url = f"https://logincert.anaf.ro/anaf-oauth2/v1/authorize?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}"
    return {"auth_url": auth_url}

@app.get("/callback")
def oauth_callback(request: Request, code: str = Query(...)):
    config = load_config()
    client_id = config.get("client_id")
    client_secret = config.get("client_secret")
    
    redirect_uri = config.get("redirect_uri", "http://localhost:8000/callback")
    
    url = "https://logincert.anaf.ro/anaf-oauth2/v1/token"


    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri
    }
    
    logger.info("Exchanging authorization code for OAuth2 tokens...")
    try:

        res = requests.post(url, data=payload, timeout=15)
        if res.status_code == 200:
            data = res.json()
            access_token = data.get("access_token")
            refresh_token = data.get("refresh_token")
            expires_in = int(data.get("expires_in", 7776000)) # 90 days in seconds
            
            current_time = int(time.time())
            
            config["tokens"] = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "access_expires_at": current_time + expires_in,
                "refresh_expires_at": current_time + 31536000 # 365 days
            }
            save_config(config)
            logger.info("ANAF token successfully acquired and saved!")
            
            html_content = """
            <html>
                <head>
                    <title>Authentication Successful</title>
                    <style>
                        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #f8fafc; text-align: center; padding: 50px; }
                        .card { background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; display: inline-block; padding: 40px; box-shadow: 0 4px 30px rgba(0,0,0,0.5); }
                        h1 { color: #10b981; }
                        button { background: #10b981; border: none; color: white; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-size: 16px; margin-top: 20px; }
                    </style>
                </head>
                <body>
                    <div class="card">
                        <h1>✓ Conectare Reușită!</h1>
                        <p>Tokenul de autentificare a fost salvat cu succes.</p>
                        <p>Puteți închide această filă și să reveniți în tabloul de bord ANAF Bot.</p>
                        <button onclick="window.close()">Închide Pagina</button>
                    </div>
                </body>
            </html>
            """
            return HTMLResponse(content=html_content)
        else:
            logger.error(f"Error exchanging tokens: {res.status_code} - {res.text}")
            return HTMLResponse(content=f"<h1>Eroare Autentificare</h1><p>{res.text}</p>")
    except Exception as e:
        logger.error(f"Authentication exception: {str(e)}")
        return HTMLResponse(content=f"<h1>Eroare Conexiune</h1><p>{str(e)}</p>")

@app.get("/api/logs")
def get_logs():
    return log_stream

@app.get("/api/clear-logs")
def clear_logs():
    global log_stream
    log_stream.clear()
    return {"status": "ok"}

# Background sync execution state
sync_active = False
sync_results = []

def run_sync_task(year: str, month: str):
    global sync_active, sync_results
    sync_active = True
    sync_results = []
    
    config = load_config()
    cif = config.get("cif")
    test_mode = config.get("test_mode", True)
    invert_in_out = config.get("invert_in_out", True)
    days_to_search = config.get("days", 30)
    
    base_dir = config.get("test_dir") if test_mode else config.get("target_dir")
    
    logger.info(f"Starting sync for Year: {year}, Month: {month}...")
    logger.info(f"Target Directory: {base_dir}")
    logger.info(f"Mode: {'TEST (Safe Mode)' if test_mode else 'LIVE (Active Drive)'}")
    
    if not cif:
        logger.error("CUI/CIF is not configured. Aborting sync.")
        sync_active = False
        return
        
    token = get_valid_token(config)
    if not token:
        logger.error("No valid authorization token found. Please click 'Connect ANAF' to authenticate first.")
        sync_active = False
        return
        
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Fetch invoice messages from ANAF (query parameter `zile` max value is 60)
    logger.info(f"Fetching messages list from ANAF for the last {days_to_search} days...")
    # Clean CIF: strip 'RO' and spaces
    clean_cif = cif.upper().replace("RO", "").strip()
    
    list_url = f"https://api.anaf.ro/prod/FCTEL/rest/listaMesajeFactura?zile={days_to_search}&cif={clean_cif}"
    
    try:
        res = requests.get(list_url, headers=headers, timeout=30)
        if res.status_code != 200:
            logger.error(f"Failed to fetch list from ANAF: HTTP {res.status_code} - {res.text}")
            sync_active = False
            return
            
        data = res.json()
        messages = data.get("mesaje", [])
        logger.info(f"Total messages received from ANAF: {len(messages)}")
        
        matching_messages = []
        for msg in messages:
            date_str = msg.get("data_creare") or msg.get("data_crearii", "")
            parsed_date = parse_message_date(date_str)
            if parsed_date:
                y, m, d = parsed_date
                # Support "ALL" wildcards for year and month
                match_year = (year == "ALL" or y == year)
                match_month = (month == "ALL" or m == month)
                if match_year and match_month:
                    matching_messages.append((msg, parsed_date))
                
        logger.info(f"Filtered messages matching Year: {year}, Month: {month}: {len(matching_messages)}")
        
        success_count = 0
        skipped_count = 0
        error_count = 0
        
        for index, (msg, parsed_date) in enumerate(matching_messages, 1):
            y_part, m_part, d_part = parsed_date
            msg_id = msg.get("id") or msg.get("id_solicitare")
            if not msg_id:
                logger.error(f"Message at index {index} has no valid ID. Skipping.")
                error_count += 1
                continue
                
            msg_type = msg.get("tip", "FACTURA TRIMISA")
            
            # Format Date for filename: DD-MM-YYYY and display: DD.MM.YYYY
            file_date = f"{d_part}-{m_part}-{y_part}"
            display_date = f"{d_part}.{m_part}.{y_part}"
            
            # Resolve month subfolder name
            month_folder_name = MONTHS_MAP.get(m_part, f"{m_part}_Luna")
            
            # Resolve IN/OUT directory
            # Rule:
            # If invert_in_out is True (User requested):
            #   FACTURA PRIMITA -> OUT
            #   FACTURA TRIMISA -> IN
            # If false (standard logic):
            #   FACTURA PRIMITA -> IN
            #   FACTURA TRIMISA -> OUT
            dir_type = "OUT"
            if msg_type == "FACTURA TRIMISA":
                dir_type = "IN" if invert_in_out else "OUT"
            elif msg_type == "FACTURA PRIMITA":
                dir_type = "OUT" if invert_in_out else "IN"
            else:
                # Erori, etc. go into their own folder or IN by default
                dir_type = "IN"
                
            # Create final target path based on user's customizable folder structure template
            structure_template = config.get("folder_structure", "{year}/{month}/{direction}")
            try:
                resolved_subpath = structure_template.format(
                    year=y_part,
                    month=month_folder_name,
                    direction=dir_type,
                    cui=clean_cif,
                    raw_month=m_part
                )
            except Exception as e:
                logger.error(f"Failed to parse folder structure template '{structure_template}': {str(e)}. Falling back to default.")
                resolved_subpath = os.path.join(y_part, month_folder_name, dir_type)
                
            path_parts = re.split(r'[\\/]', resolved_subpath)
            folder_path = os.path.join(base_dir, *[p for p in path_parts if p.strip()])
            os.makedirs(folder_path, exist_ok=True)
            
            pdf_filename = f"{file_date}_{msg_id}.pdf"
            pdf_path = os.path.join(folder_path, pdf_filename)
            
            old_formatted_filename = f"{y_part}{m_part}{d_part}_{msg_id}.pdf"
            old_formatted_path = os.path.join(folder_path, old_formatted_filename)
            
            plain_filename = f"{msg_id}.pdf"
            plain_path = os.path.join(folder_path, plain_filename)
            
            # Safety & Duplicate Check
            if os.path.exists(pdf_path):
                # If the new format exists, clean up any old/plain duplicate files
                for dup_path in (old_formatted_path, plain_path):
                    if os.path.exists(dup_path):
                        try:
                            os.remove(dup_path)
                            logger.info(f"[{index}/{len(matching_messages)}] Cleaned up duplicate file: {os.path.basename(dup_path)}")
                        except Exception as e:
                            logger.error(f"Failed to delete duplicate file: {str(e)}")
                            
                logger.info(f"[{index}/{len(matching_messages)}] Skipped: {pdf_filename} already exists.")
                sync_results.append({
                    "id": msg_id,
                    "date": display_date,
                    "type": msg_type,
                    "direction": dir_type,
                    "filename": pdf_filename,
                    "status": "Skipped (Exists)"
                })
                skipped_count += 1
                continue
                
            elif os.path.exists(old_formatted_path):
                # Standardize old formatted name to new format
                try:
                    os.rename(old_formatted_path, pdf_path)
                    logger.info(f"[{index}/{len(matching_messages)}] Upgraded old filename (renamed {old_formatted_filename} -> {pdf_filename})")
                    # If plain also exists, clean it up
                    if os.path.exists(plain_path):
                        try:
                            os.remove(plain_path)
                        except:
                            pass
                            
                    sync_results.append({
                        "id": msg_id,
                        "date": display_date,
                        "type": msg_type,
                        "direction": dir_type,
                        "filename": pdf_filename,
                        "status": "Upgraded Format (Renamed)"
                    })
                    skipped_count += 1
                    continue
                except Exception as e:
                    logger.error(f"Failed to upgrade old filename: {str(e)}")
                    
            elif os.path.exists(plain_path):
                # Standardize plain manual name to new format
                try:
                    os.rename(plain_path, pdf_path)
                    logger.info(f"[{index}/{len(matching_messages)}] Standardized manual download (renamed {plain_filename} -> {pdf_filename})")
                    sync_results.append({
                        "id": msg_id,
                        "date": display_date,
                        "type": msg_type,
                        "direction": dir_type,
                        "filename": pdf_filename,
                        "status": "Standardized (Renamed)"
                    })
                    skipped_count += 1
                    continue
                except Exception as e:
                    logger.error(f"Failed to rename manual download: {str(e)}")
                    # Proceed to download as a fallback if rename fails
                
            logger.info(f"[{index}/{len(matching_messages)}] Downloading invoice ID: {msg_id} ({msg_type})...")
            
            # 2. Download invoice ZIP
            dl_url = f"https://api.anaf.ro/prod/FCTEL/rest/descarcare?id={msg_id}"
            dl_res = requests.get(dl_url, headers=headers, timeout=30)
            
            if dl_res.status_code != 200:
                logger.error(f"Failed to download ZIP for message {msg_id}: HTTP {dl_res.status_code}")
                sync_results.append({
                    "id": msg_id,
                    "date": display_date,
                    "type": msg_type,
                    "direction": dir_type,
                    "filename": pdf_filename,
                    "status": f"Download Failed (HTTP {dl_res.status_code})"
                })
                error_count += 1
                continue
                
            # 3. Extract XML from ZIP in memory
            try:
                zip_data = io.BytesIO(dl_res.content)
                xml_content = None
                with zipfile.ZipFile(zip_data) as zf:
                    for name in zf.namelist():
                        if name.endswith(".xml") and not name.lower().startswith("signature"):
                            # This is the actual invoice XML (usually named [id_descarcare].xml)
                            xml_content = zf.read(name).decode("utf-8")
                            break
                            
                if not xml_content:
                    logger.error(f"No XML found in downloaded ZIP for message {msg_id}")
                    sync_results.append({
                        "id": msg_id,
                        "date": display_date,
                        "type": msg_type,
                        "direction": dir_type,
                        "filename": pdf_filename,
                        "status": "XML Not Found in ZIP"
                    })
                    error_count += 1
                    continue
                    
                # 4. Transform XML to PDF via ANAF transformare endpoint
                # Standard is FACT1 for invoices
                logger.info(f"Converting XML to PDF for ID {msg_id} via ANAF webservice...")
                transform_url = "https://api.anaf.ro/prod/FCTEL/rest/transformare/FACT1/DA"
                tf_headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "text/plain"
                }
                tf_res = requests.post(transform_url, data=xml_content.encode("utf-8"), headers=tf_headers, timeout=30)
                
                if tf_res.status_code == 200:
                    # Save PDF
                    with open(pdf_path, "wb") as f:
                        f.write(tf_res.content)
                    logger.info(f"Successfully saved PDF: {pdf_path}")
                    sync_results.append({
                        "id": msg_id,
                        "date": display_date,
                        "type": msg_type,
                        "direction": dir_type,
                        "filename": pdf_filename,
                        "status": "Success"
                    })
                    success_count += 1
                else:
                    logger.error(f"Failed to transform XML to PDF: HTTP {tf_res.status_code} - {tf_res.text}")
                    sync_results.append({
                        "id": msg_id,
                        "date": display_date,
                        "type": msg_type,
                        "direction": dir_type,
                        "filename": pdf_filename,
                        "status": f"PDF Conversion Failed (HTTP {tf_res.status_code})"
                    })
                    error_count += 1
            except Exception as e:
                logger.error(f"Exception while processing ID {msg_id}: {str(e)}")
                sync_results.append({
                    "id": msg_id,
                    "date": display_date,
                    "type": msg_type,
                    "direction": dir_type,
                    "filename": pdf_filename,
                    "status": f"Error ({str(e)})"
                })
                error_count += 1
                
        logger.info("========================================")
        logger.info("Sync Completed Report:")
        logger.info(f" - Successfully downloaded and converted: {success_count} PDFs")
        logger.info(f" - Skipped (already exist): {skipped_count}")
        logger.info(f" - Failed: {error_count}")
        logger.info("========================================")
        
    except Exception as e:
        logger.error(f"Sync failed with fatal error: {str(e)}")
    finally:
        sync_active = False


@app.post("/api/sync")
def sync_endpoint(payload: Dict[str, str], background_tasks: BackgroundTasks):
    global sync_active
    if sync_active:
        raise HTTPException(status_code=400, detail="A synchronization task is already in progress.")
        
    year = payload.get("year")
    month = payload.get("month")
    
    if not year or not month:
        raise HTTPException(status_code=400, detail="Year and Month parameters are required.")
        
    # Queue task to run in the background
    background_tasks.add_task(run_sync_task, year, month)
    return {"status": "queued"}

@app.get("/api/sync/status")
def sync_status_endpoint():
    return {
        "active": sync_active,
        "results": sync_results
    }

# Serving Dashboard Frontend Static Files
if os.path.exists(GUI_DIR):
    app.mount("/", StaticFiles(directory=GUI_DIR, html=True), name="gui")
else:
    @app.get("/")
    def index():
        return HTMLResponse("<h1>ANAF Bot Dashboard</h1><p>GUI folder not found. Please create 'gui' folder and place assets.</p>")

def generate_self_signed_cert():
    cert_path = os.path.join(os.path.dirname(CONFIG_PATH), "cert.pem")
    key_path = os.path.join(os.path.dirname(CONFIG_PATH), "key.pem")
    if os.path.exists(cert_path) and os.path.exists(key_path):
        return cert_path, key_path
        
    logger.info("Generating self-signed SSL certificate for secure local OAuth connections...")
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        import ipaddress
        
        # Generate private key
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        # Generate certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, u"127.0.0.1"),
        ])
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow() - datetime.timedelta(days=1)
        ).not_valid_after(
            # 10 years validity
            datetime.datetime.utcnow() + datetime.timedelta(days=3650)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                x509.DNSName(u"localhost")
            ]),
            critical=False,
        ).sign(key, hashes.SHA256())
        
        # Write private key
        with open(key_path, "wb") as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            ))
        # Write certificate
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
            
        logger.info("SSL Certificate successfully generated.")
        return cert_path, key_path
    except Exception as e:
        logger.error(f"Failed to generate SSL certificate: {str(e)}")
        return None, None

if __name__ == "__main__":
    config = load_config()
    redirect_uri = config.get("redirect_uri", "http://localhost:8000/callback")
    
    # Auto-detect if redirect_uri uses HTTPS and run server on HTTPS if so
    if redirect_uri.lower().startswith("https://"):
        logger.info("HTTPS redirect detected. Setting up local secure server...")
        cert_path, key_path = generate_self_signed_cert()
        if cert_path and key_path and os.path.exists(cert_path) and os.path.exists(key_path):
            logger.info("Starting local secure web server (HTTPS)...")
            uvicorn.run(app, host="127.0.0.1", port=8000, ssl_keyfile=key_path, ssl_certfile=cert_path)
        else:
            logger.error("Could not load SSL credentials. Falling back to HTTP...")
            uvicorn.run(app, host="127.0.0.1", port=8000)
    else:
        logger.info("Starting local web server (HTTP)...")
        uvicorn.run(app, host="127.0.0.1", port=8000)
