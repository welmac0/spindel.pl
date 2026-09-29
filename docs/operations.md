# Operacje i wdrazanie

## Produkcja

Spindel dziala na pojedynczym VPS Hetzner (Ubuntu) przez Docker Compose. Produkcyjny Compose uruchamia backend, frontend/Nginx i Certbot. Nginx wystawia 80/443, backend nie ma publicznie wystawionego portu, a SQLite znajduje sie w zewnetrznym wolumenie `docker_wymiana_data`.

## Wdrozenie

W repozytorium istnieje reczny GitHub Actions workflow `Deploy production`: weryfikuje CI dla aktualnego `main`, laczy sie z VPS, wykonuje backup, buduje obrazy, uruchamia uslugi i czeka na healthchecki. Workflow wdraza `main`, nie konkretny tag.

Po wdrozeniu zweryfikuj:

- `https://spindel.pl/api/health`
- `https://spindel.pl/nginx-health`
- statusy `healthy` dla backendu i frontendu,
- logi aplikacji i Certbota,
- systemd timery healthchecka i backupu,
- kluczowy przeplyw aplikacji.

Nie uruchamiaj `docker compose down -v`, jesli baza ma zostac zachowana.

## Samodzielny przeplyw pracy

Repozytorium jest obecnie rozwijane przez jedna osobe. Bezposrednie commity na `main` sa akceptowanym sposobem pracy; Pull Request nie jest warunkiem. Przed wdrozeniem uruchom testy backendu i build frontendu, a nastepnie sprawdz zielone CI dla commita na `main`. Uzywaj osobnych branchy, jesli zmiana jest ryzykowna lub chcesz latwo ja odlozyc.

Release/tag opisuje commit; nie wykonuje deployu. Tag wersji przypinaj do commita, ktory rzeczywiscie zostal wdrozony i zweryfikowany.

## Backup i odtworzenie SQLite

- systemd timer wykonuje backup co 6 godzin do `/opt/wymiana-zajec/backups/`, poza wolumenem aplikacji.
- Backup ma checksum i jest sprawdzany przez `PRAGMA integrity_check`.
- Retencja po stronie VPS wynosi 14 kopii.
- Druga kopia jest pobierana poza VPS przez SSH/rsync; szczegoly sa w [instrukcji backupu na Macu](notes-how2/mac_backup.md).
- Okresowo testuj odtworzenie kopii poza produkcyjna baza. Nie przywracaj pliku testowego do wolumenu produkcyjnego.

## Monitoring

Systemd timer monitoruje healthcheck backendu co minute i wysyla alert przez Brevo przy zmianie stanu. Ten monitor dziala na tym samym VPS-ie, wiec nie wykryje niezawodnie awarii hosta lub utraty lacznosci z niego. Niezalezny monitoring zewnetrzny i alerty wymagaja osobnej konfiguracji.

## Maintenance mode

Frontend ma flage build-time `VITE_MAINTENANCE`. Instrukcja wlaczenia/wylaczenia jest w [maintenance mode](notes-how2/maintenance_mode.md). Maintenance nie wymaga zatrzymania backendu ani usuwania wolumenu.

## Rollback

Przed zmiana na produkcji zachowaj informacje o wdrozonym commicie i sprawdz backup. Obecny workflow nie ma automatycznego rollbacku ani wdrazania wskazanego taga. W razie awarii zatrzymaj dalsze proby wdrozen, wlacz maintenance w razie potrzeby, przywroc znany dobry kod/obrazy bez usuwania wolumenu, uruchom healthchecki i smoke test. Odtwarzanie bazy jest osobna procedura — nie cofaj obrazu i bazy automatycznie razem bez oceny zgodnosci schematu.
