========================================================================
                 ANAF e-Factura PDF Downloader Bot
========================================================================

Acest ghid conține toate instrucțiunile de configurare și depanare pentru
utilizarea botului local de descărcare și organizare a facturilor ANAF.

------------------------------------------------------------------------
🚀 CUM SĂ PORNEȘTI BOTUL
------------------------------------------------------------------------
1. Conectează stick-ul cu semnătura digitală la calculator.
2. Dublu-click pe fișierul "run.bat" din acest folder.
3. Dashboard-ul se va deschide automat în browser la adresa:
   http://127.0.0.1:8000

------------------------------------------------------------------------
🔑 CONFIGURARE INIȚIALĂ / RE-AUTORIZARE (O dată pe an)
------------------------------------------------------------------------
Dacă token-ul expiră după 365 de zile sau trebuie să refaci configurarea:

1. Accesează portalul ANAF OAuth cu stick-ul introdus:
   https://www.anaf.ro/InregOauth/Adaugare.xhtml

2. Mergi la secțiunea "Editare profil Oauth" din meniul de sus (dacă nu e selectat implicit).

3. Completează formularul de înregistrare aplicație:
   * Denumire aplicație: ANAFBot
   * Callback URL 1: http://localhost:8000/callback (sau http://127.0.0.1:8000/callback)
   * Serviciu: Selectează DOAR "E-Factura" (Debifează "E-Transport")
     --> IMPORTANT: Dacă bifezi și E-Transport, serverul ANAF va da eroare 400!

4. Apasă pe "Generare Client ID". Datele aplicației vor apărea în tabelul de mai jos.

5. Copiază Client ID și Client Secret în câmpurile din setările Dashboard-ului botului.

------------------------------------------------------------------------
❌ DEPANARE: EROARE SSL / PAGINĂ NEAGRĂ LA AUTORIZARE
------------------------------------------------------------------------
Dacă după ce te loghezi cu certificatul digital pe ANAF, browserul se
redirecționează către "127.0.0.1:8000/callback..." și îți afișează eroarea:
"This site can't provide a secure connection" sau "ERR_SSL_PROTOCOL_ERROR":

1. Click pe bara de adrese a browserului (unde scrie link-ul paginii).
2. Șterge litera "s" din "https://", astfel încât link-ul să înceapă cu "http://":
   În loc de: https://127.0.0.1:8000/callback?code=...
   Să fie:    http://127.0.0.1:8000/callback?code=...
3. Apasă tasta ENTER pe tastatură.
4. Ecranul se va încărca imediat și va afișa mesajul de confirmare a succesului.

------------------------------------------------------------------------
📁 STRUCTURA DE SALVARE A FACTURILOR
------------------------------------------------------------------------
Facturile sunt sortate automat în foldere după data din factură:
D:\PALY S.R.L\[An]\[Lună]\[IN sau OUT]\[DD-MM-YYYY]_[ID_Mesaj].pdf (Ex: 16-06-2026_7732853451.pdf)

* FACTURA TRIMISĂ ➔ Folderul IN (Vânzări / Venituri)
* FACTURA PRIMITĂ ➔ Folderul OUT (Achiziții / Cheltuieli)

* Notă: Botul are o politică de siguranță strictă. Dacă fișierul PDF
  există deja pe disk, acesta este ignorat. Botul nu va șterge și nu
  va suprascrie NICIODATĂ fișiere din drive-ul tău.

------------------------------------------------------------------------
⚙️ STRUCTURĂ PERSONALIZATĂ FOLDERE
------------------------------------------------------------------------
În setările Dashboard-ului poți schimba formatul folderelor create prin
câmpul "Structură Foldere". Valoarea implicită este:
{year}/{month}/{direction}

Variabilele pe care le poți folosi sunt:
* {year}       ➔ Anul facturii (Ex: 2026)
* {month}      ➔ Folderul lunii cu nume (Ex: 07_Iulie)
* {raw_month}  ➔ Indexul lunii format din 2 cifre (Ex: 07)
* {direction}  ➔ Direcția facturii (IN sau OUT)
* {cui}        ➔ CIF-ul firmei tale (Ex: 49430531)

Exemple de structuri pe care le poți scrie:
* {year}/{month}/{direction} ➔ Format standard (An/Lună/IN-OUT)
* {direction}/{year}/{month} ➔ Sortează mai întâi după IN/OUT
* {cui}/{year}-{raw_month}/{direction} ➔ Sortează după CUI și lună numerică
