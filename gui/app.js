document.addEventListener('DOMContentLoaded', () => {
    // Dom Elements
    const settingsForm = document.getElementById('settings-form');
    const cifInput = document.getElementById('cif');
    const clientIdInput = document.getElementById('client_id');
    const clientSecretInput = document.getElementById('client_secret');
    const testModeCheckbox = document.getElementById('test_mode');
    const testDirInput = document.getElementById('test_dir');
    const targetDirInput = document.getElementById('target_dir');
    const invertInOutCheckbox = document.getElementById('invert_in_out');
    const redirectUriInput = document.getElementById('redirect_uri');
    const folderStructureInput = document.getElementById('folder_structure');
    const daysInput = document.getElementById('days');
    const modeStatusText = document.getElementById('mode-status-text');
    
    const connectionBadge = document.getElementById('connection-badge');
    const badgeText = document.getElementById('badge-text');
    
    const connectBtn = document.getElementById('connect-btn');
    const statusCircle = document.getElementById('status-circle');
    const authTitle = document.getElementById('auth-title');
    const authDesc = document.getElementById('auth-desc');
    
    const syncYearSelect = document.getElementById('sync-year');
    const syncMonthSelect = document.getElementById('sync-month');
    const syncBtn = document.getElementById('sync-btn');
    
    const logsBox = document.getElementById('logs-box');
    const clearLogsBtn = document.getElementById('clear-logs-btn');
    
    const resultsBody = document.getElementById('results-body');

    // API URL prefix
    const apiBase = window.location.origin;
    let isSyncing = false;
    let lastLogIndex = 0;

    // Initialize Page
    init();

    function init() {
        loadConfig();
        checkStatus();
        
        // Start background polling for status and logs
        setInterval(checkStatus, 3000);
        setInterval(pollLogs, 1000);
        setInterval(checkSyncStatusState, 2000);
        
        // Event Listeners
        settingsForm.addEventListener('submit', saveConfig);
        connectBtn.addEventListener('click', connectANAF);
        syncBtn.addEventListener('click', triggerSync);
        clearLogsBtn.addEventListener('click', clearLogs);
        testModeCheckbox.addEventListener('change', updateModeUI);
        
        // Automatically set current month and year in select elements
        const now = new Date();
        const currentYear = now.getFullYear().toString();
        const currentMonth = String(now.getMonth() + 1).padStart(2, '0');
        
        // Find option elements and select them
        if ([...syncYearSelect.options].some(o => o.value === currentYear)) {
            syncYearSelect.value = currentYear;
        }
        syncMonthSelect.value = currentMonth;
    }

    // Toggle styling between TEST and LIVE
    function updateModeUI() {
        if (testModeCheckbox.checked) {
            modeStatusText.innerText = 'TEST (Sigur)';
            modeStatusText.className = 'mode-test';
        } else {
            modeStatusText.innerText = 'LIVE (Drive)';
            modeStatusText.className = 'mode-live';
        }
    }

    // Fetch config values from API
    async function loadConfig() {
        try {
            const res = await fetch(`${apiBase}/api/config`);
            if (res.ok) {
                const config = await res.json();
                cifInput.value = config.cif || '';
                clientIdInput.value = config.client_id || '';
                clientSecretInput.value = config.client_secret || '';
                testDirInput.value = config.test_dir || 'd:\\ANAFBOT\\test_sync';
                targetDirInput.value = config.target_dir || 'D:\\PALY S.R.L';
                testModeCheckbox.checked = config.test_mode !== false;
                invertInOutCheckbox.checked = config.invert_in_out !== false;
                redirectUriInput.value = config.redirect_uri || 'http://localhost:8000/callback';
                folderStructureInput.value = config.folder_structure || '{year}/{month}/{direction}';
                daysInput.value = config.days || 30;
                
                updateModeUI();
                enableConnectButtonState(config);
            }
        } catch (err) {
            addLocalLog('Sistem', `Eroare la încărcarea setărilor: ${err.message}`, 'error-line');
        }
    }

    function enableConnectButtonState(config) {
        if (config.client_id && config.client_secret && config.cif) {
            connectBtn.removeAttribute('disabled');
        } else {
            connectBtn.setAttribute('disabled', 'true');
        }
    }

    // Save configurations via API
    async function saveConfig(e) {
        e.preventDefault();
        
        const payload = {
            cif: cifInput.value.trim(),
            client_id: clientIdInput.value.trim(),
            client_secret: clientSecretInput.value.trim(),
            test_mode: testModeCheckbox.checked,
            test_dir: testDirInput.value.trim(),
            target_dir: targetDirInput.value.trim(),
            invert_in_out: invertInOutCheckbox.checked,
            redirect_uri: redirectUriInput.value.trim(),
            folder_structure: folderStructureInput.value.trim(),
            days: parseInt(daysInput.value, 10)
        };

        try {
            const res = await fetch(`${apiBase}/api/config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                addLocalLog('Sistem', 'Setările au fost salvate cu succes.', 'system-line');
                enableConnectButtonState(payload);
                checkStatus();
            } else {
                const err = await res.json();
                addLocalLog('Sistem', `Eroare la salvare: ${err.detail || 'Eroare server'}`, 'error-line');
            }
        } catch (err) {
            addLocalLog('Sistem', `Eroare conexiune server: ${err.message}`, 'error-line');
        }
    }

    // Check auth status from API
    async function checkStatus() {
        try {
            const res = await fetch(`${apiBase}/api/status`);
            if (res.ok) {
                const data = await res.json();
                updateAuthStatusUI(data);
            }
        } catch (err) {
            // Keep silent or show disconnected if API goes down
            connectionBadge.className = 'badge badge-disconnected';
            badgeText.innerText = 'Deconectat';
            statusCircle.className = 'status-circle disconnected';
            authTitle.innerText = 'Stare Conexiune: Server oprit';
            authDesc.innerText = 'Verificați dacă rulează scriptul Python principal.';
            syncBtn.setAttribute('disabled', 'true');
        }
    }

    function updateAuthStatusUI(data) {
        const hasCredentials = data.client_id && data.cif;
        
        if (!hasCredentials) {
            connectionBadge.className = 'badge badge-disconnected';
            badgeText.innerText = 'Fără Setări';
            statusCircle.className = 'status-circle disconnected';
            authTitle.innerText = 'Stare Conexiune: Neconfigurat';
            authDesc.innerText = 'Vă rugăm să introduceți CUI-ul și datele OAuth în setări.';
            syncBtn.setAttribute('disabled', 'true');
            return;
        }

        if (data.status === 'connected') {
            connectionBadge.className = 'badge badge-connected';
            badgeText.innerText = 'Conectat ANAF';
            statusCircle.className = 'status-circle connected';
            authTitle.innerText = 'Stare Conexiune: AUTORIZAT';
            authDesc.innerText = `Tokenul este valid. Expiră în aprox. ${data.access_days_remaining} zile (Refresh valid ${data.refresh_days_remaining} zile).`;
            if (!isSyncing) syncBtn.removeAttribute('disabled');
        } else if (data.status === 'needs_refresh') {
            connectionBadge.className = 'badge badge-warning';
            badgeText.innerText = 'Necesită Re-conectare';
            statusCircle.className = 'status-circle warning';
            authTitle.innerText = 'Stare Conexiune: Expirat';
            authDesc.innerText = `Conexiunea a expirat. Apăsați butonul 'Conectează ANAF' cu stick-ul introdus.`;
            syncBtn.setAttribute('disabled', 'true');
        } else {
            connectionBadge.className = 'badge badge-disconnected';
            badgeText.innerText = 'Neautorizat';
            statusCircle.className = 'status-circle disconnected';
            authTitle.innerText = 'Stare Conexiune: NEAUTORIZAT';
            authDesc.innerText = "Apăsați 'Conectează ANAF' pentru a vă autentifica cu tokenul digital.";
            syncBtn.setAttribute('disabled', 'true');
        }
    }

    // Trigger OAuth redirect
    async function connectANAF() {
        try {
            const res = await fetch(`${apiBase}/api/connect`);
            if (res.ok) {
                const data = await res.json();
                addLocalLog('Sistem', 'Se deschide pagina de autentificare ANAF. Vă rugăm să introduceți PIN-ul în fereastra pop-up.', 'system-line');
                window.open(data.auth_url, '_blank');
            } else {
                const err = await res.json();
                alert(`Eroare: ${err.detail}`);
            }
        } catch (err) {
            addLocalLog('Sistem', `Eroare pornire autentificare: ${err.message}`, 'error-line');
        }
    }

    // Trigger synchronization
    async function triggerSync() {
        if (isSyncing) return;
        
        const payload = {
            year: syncYearSelect.value,
            month: syncMonthSelect.value
        };

        try {
            isSyncing = true;
            syncBtn.setAttribute('disabled', 'true');
            syncBtn.innerText = 'Sincronizare în curs... ⏳';
            
            const res = await fetch(`${apiBase}/api/sync`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                addLocalLog('Sistem', 'Sincronizarea a fost adăugată în coadă. Se procesează...', 'system-line');
                checkSyncStatusState(true);
            } else {
                const err = await res.json();
                addLocalLog('Sistem', `Eroare pornire sync: ${err.detail || 'Eroare server'}`, 'error-line');
                isSyncing = false;
                syncBtn.removeAttribute('disabled');
                syncBtn.innerText = '🚀 Lansează Sincronizare Facturi PDF';
            }
        } catch (err) {
            addLocalLog('Sistem', `Eroare conexiune sync: ${err.message}`, 'error-line');
            isSyncing = false;
            syncBtn.removeAttribute('disabled');
            syncBtn.innerText = '🚀 Lansează Sincronizare Facturi PDF';
        }
    }

    // Check execution state of sync background task
    async function checkSyncStatusState(force = false) {
        if (!isSyncing && !force) return;

        try {
            const res = await fetch(`${apiBase}/api/sync/status`);
            if (res.ok) {
                const data = await res.json();
                isSyncing = data.active;
                
                if (data.results && data.results.length > 0) {
                    renderResultsTable(data.results);
                }
                
                if (!isSyncing) {
                    syncBtn.removeAttribute('disabled');
                    syncBtn.innerText = '🚀 Lansează Sincronizare Facturi PDF';
                    checkStatus(); // Refresh auth expiration
                }
            }
        } catch (err) {
            console.error('Failed to check sync status', err);
        }
    }

    function renderResultsTable(results) {
        resultsBody.innerHTML = '';
        results.forEach(res => {
            const row = document.createElement('tr');
            
            let statusClass = 'status-success';
            if (res.status.includes('Skipped')) {
                statusClass = 'status-skipped';
            } else if (res.status.includes('Failed') || res.status.includes('Error')) {
                statusClass = 'status-failed';
            }

            row.innerHTML = `
                <td><b>${res.id}</b></td>
                <td>${res.date}</td>
                <td>${res.type}</td>
                <td><code style="font-size: 11px;">[${res.direction}] / ${res.filename}</code></td>
                <td><span class="${statusClass}">${res.status}</span></td>
            `;
            resultsBody.appendChild(row);
        });
    }

    // Pull logs in real-time
    async function pollLogs() {
        try {
            const res = await fetch(`${apiBase}/api/logs`);
            if (res.ok) {
                const logs = await res.json();
                if (logs.length > lastLogIndex) {
                    const newLogs = logs.slice(lastLogIndex);
                    newLogs.forEach(entry => {
                        let lineClass = 'info-line';
                        if (entry.level === 'ERROR') lineClass = 'error-line';
                        if (entry.level === 'WARNING') lineClass = 'warning-line';
                        if (entry.message.startsWith('[Sistem]')) lineClass = 'system-line';
                        
                        const logDiv = document.createElement('div');
                        logDiv.className = `log-line ${lineClass}`;
                        logDiv.innerText = `[${entry.time}] ${entry.message}`;
                        logsBox.appendChild(logDiv);
                    });
                    
                    logsBox.scrollTop = logsBox.scrollHeight;
                    lastLogIndex = logs.length;
                }
            }
        } catch (err) {
            console.error('Error polling logs', err);
        }
    }

    async function clearLogs() {
        try {
            const res = await fetch(`${apiBase}/api/clear-logs`, { method: 'GET' });
            if (res.ok) {
                logsBox.innerHTML = '<div class="log-line system-line">[Sistem] Jurnalul a fost curățat.</div>';
                lastLogIndex = 0;
            }
        } catch (err) {
            console.error('Error clearing logs', err);
        }
    }

    function addLocalLog(source, msg, classType = 'info-line') {
        const time = new Date().toTimeString().split(' ')[0];
        const logDiv = document.createElement('div');
        logDiv.className = `log-line ${classType}`;
        logDiv.innerText = `[${time}] [${source}] ${msg}`;
        logsBox.appendChild(logDiv);
        logsBox.scrollTop = logsBox.scrollHeight;
    }
});
