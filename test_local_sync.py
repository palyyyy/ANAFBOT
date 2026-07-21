import os
import shutil
import json
import time
import zipfile
import io
from unittest.mock import patch, MagicMock

# Import the methods we want to test from main.py
import main

# Test directory setup
TEST_SYNC_DIR = "d:\\ANAFBOT\\test_sync"

# Clear test directory if it exists to start fresh
if os.path.exists(TEST_SYNC_DIR):
    shutil.rmtree(TEST_SYNC_DIR)
os.makedirs(TEST_SYNC_DIR, exist_ok=True)

# Update config.json settings temporarily for the test
config = main.load_config()
config["cif"] = "12345678"
config["test_mode"] = True
config["test_dir"] = TEST_SYNC_DIR
config["invert_in_out"] = True  # TRIMISA -> IN, PRIMITA -> OUT
config["tokens"] = {
    "access_token": "mock_access_token",
    "refresh_token": "mock_refresh_token",
    "access_expires_at": int(time.time()) + 3600,
    "refresh_expires_at": int(time.time()) + 86400
}
main.save_config(config)

# Prepare Mock Responses
mock_messages_response = {
    "cif": "12345678",
    "mesaje": [
        {
            "id": "1111111",
            "cif_emitent": "87654321",
            "cif_beneficiar": "12345678",
            "tip": "FACTURA TRIMISA",
            "data_creare": "2026-07-20T10:00:00"
        },
        {
            "id": "2222222",
            "cif_emitent": "12345678",
            "cif_beneficiar": "44443333",
            "tip": "FACTURA PRIMITA",
            "data_creare": "2026-07-21T15:30:00"
        },
        {
            "id": "3333333",
            "cif_emitent": "12345678",
            "cif_beneficiar": "55556666",
            "tip": "FACTURA TRIMISA",
            "data_creare": "2026-06-15T09:00:00"  # June invoice (should be skipped when syncing July)
        }
    ]
}

# Create a mock zip file content
zip_buffer = io.BytesIO()
with zipfile.ZipFile(zip_buffer, "w") as zf:
    zf.writestr("invoice_111.xml", "<Invoice>Mock UBL XML content</Invoice>")
    zf.writestr("signature.xml", "<Signature>Mock Signature</Signature>")
mock_zip_content = zip_buffer.getvalue()

mock_pdf_content = b"%PDF-1.4 Mock PDF binary data"

# Mock the requests calls
@patch("requests.get")
@patch("requests.post")
def run_simulation(mock_post, mock_get):
    # 1. Mock listing endpoint
    mock_list_res = MagicMock()
    mock_list_res.status_code = 200
    mock_list_res.json.return_value = mock_messages_response
    
    # 2. Mock download zip endpoint
    mock_dl_res = MagicMock()
    mock_dl_res.status_code = 200
    mock_dl_res.content = mock_zip_content
    
    # 3. Mock transformare endpoint
    mock_tf_res = MagicMock()
    mock_tf_res.status_code = 200
    mock_tf_res.content = mock_pdf_content
    
    # Setup mock returns
    mock_get.side_effect = lambda url, **kwargs: mock_list_res if "listaMesajeFactura" in url else mock_dl_res
    mock_post.return_value = mock_tf_res
    
    print("\n--- Starting Sync Simulation for July 2026 ---")
    main.run_sync_task("2026", "07")
    print("--- Simulation Finished ---\n")

if __name__ == "__main__":
    run_simulation()
    
    # Verify folder structure and files created
    print("Verifying created directory structure:")
    for root, dirs, files in os.walk(TEST_SYNC_DIR):
        level = root.replace(TEST_SYNC_DIR, '').count(os.sep)
        indent = ' ' * 4 * (level)
        print(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            print(f"{subindent}{f}")
            
    # Check assertions
    path_trimisa = os.path.join(TEST_SYNC_DIR, "2026", "07_Iulie", "IN", "20260720_1111111.pdf")
    path_primita = os.path.join(TEST_SYNC_DIR, "2026", "07_Iulie", "OUT", "20260721_2222222.pdf")
    path_june = os.path.join(TEST_SYNC_DIR, "2026", "06_Iunie")
    
    print("\nAssertion Checklist:")
    print(f" - Factura Trimisa PDF created in IN folder: {'PASS' if os.path.exists(path_trimisa) else 'FAIL'}")
    print(f" - Factura Primita PDF created in OUT folder: {'PASS' if os.path.exists(path_primita) else 'FAIL'}")
    print(f" - June invoice correctly skipped: {'PASS' if not os.path.exists(path_june) else 'FAIL'}")
