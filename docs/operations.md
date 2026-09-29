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

Systemd timer na VPS monitoruje healthcheck backendu co minute i wysyla alert przez Brevo przy zmianie stanu kontenera. Ten monitor dziala na tym samym VPS-ie, wiec nie wykryje niezawodnie awarii hosta lub utraty lacznosci z niego.

### Niezalezny monitoring z Raspberry Pi

Repozytorium zawiera monitor dla Ubuntu na Raspberry Pi (lub innym stale wlaczonym hoście poza VPS-em): `scripts/check_external_health.sh`, jednostke `deployment/systemd/spindel-external-monitor.service` i timer `deployment/systemd/spindel-external-monitor.timer`. Co minute sprawdza HTTPS dla `/api/health` i `/nginx-health`; po dwoch kolejnych nieudanych sprawdzeniach wysyla alert przez Brevo. Po odzyskaniu obu endpointow wysyla wiadomosc o powrocie. Nie laczy sie z VPS-em przez SSH i nie potrzebuje otwierania portow w domowej sieci.

#### Instalacja na Ubuntu

Uruchom polecenia ponizsze na Raspberry Pi, z katalogu glownego sklonowanego repozytorium (tego, w ktorym widac `scripts/` i `deployment/`). Uzytkownik systemowy ma wlasny katalog stanu; klucz Brevo trzymany jest osobno w pliku root-owned.

```bash
sudo apt update
sudo apt install --yes curl python3
id spindel-monitor >/dev/null 2>&1 || sudo useradd --system --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin spindel-monitor
sudo install -d -o root -g spindel-monitor -m 0750 /etc/spindel-monitor
sudo install -o root -g root -m 0755 /tmp/check_external_health.sh /usr/local/sbin/spindel-external-monitor.sh
sudo install -o root -g root -m 0644 /tmp/spindel-external-monitor.service /etc/systemd/system/
sudo install -o root -g root -m 0644 /tmp/spindel-external-monitor.timer /etc/systemd/system/
sudo nano /etc/spindel-monitor/monitor.env
```

W `monitor.env` wpisz **lokalnie na Raspberry Pi** (nie wklejaj sekretow do repozytorium ani rozmowy):

```dotenv
BREVO_API_KEY=YOUR_BREVO_API_KEY
BREVO_SENDER_EMAIL=verified-sender@example.com
BREVO_SENDER_NAME="Spindel Monitor"
ALERT_EMAIL=your-alert-address@example.com
FAILURE_THRESHOLD=2
```

Systemd `EnvironmentFile` obsluguje proste wartosci bez spacji i cudzyslowow; dla nazwy nadawcy zawierajacej spacje ujmij wartosc w cudzyslowy. Ustaw wlasnosc i prawa dostepu, potem uruchom monitor:

```bash
sudo chown root:spindel-monitor /etc/spindel-monitor/monitor.env
sudo chmod 0640 /etc/spindel-monitor/monitor.env
sudo systemctl daemon-reload
sudo systemctl enable --now spindel-external-monitor.timer
sudo systemctl start spindel-external-monitor.service
systemctl status spindel-external-monitor.timer
sudo journalctl -u spindel-external-monitor.service -n 30 --no-pager
```

Timer wykonuje probe po starcie i co minute. Dwie kolejne nieudane kontrole zmieniaja stan na `down` i wysylaja jeden alert; kolejny alert przyjdzie po powrocie obu endpointow. Stan jest w `/var/lib/spindel-external-monitor/`.

Przy aktualizacji skryptu lub jednostek powtorz `scp` tych samych trzech plikow, wykonaj ponownie odpowiednie komendy `sudo install`, a potem `sudo systemctl daemon-reload`; sprawdz log przez `journalctl`. Pliku `monitor.env` nie pobieraj z repo i nie nadpisuj przy aktualizacji.

Testuj bez wylaczania produkcji: na chwile zmien lokalnie w `monitor.env` jeden URL na nieistniejaca sciezke w `https://spindel.pl`, wykonaj dwukrotnie `sudo systemctl start spindel-external-monitor.service`, sprawdz mail i przywroc URL. Po przywroceniu prawidlowych adresow uruchom usluge ponownie i sprawdz alert o powrocie. Nie testuj, zatrzymujac VPS w godzinach uzytkowania.

Ograniczenie: Raspberry Pi, domowe zasilanie/Internet oraz lacze do Brevo staja sie elementami monitora. Gdy Pi jest wylaczone albo domowe lacze padnie, nie bedzie moglo wyslac alertu; dla monitoringu krytycznego dodaj pozniej usluge zewnetrzna hostowana niezaleznie.

#### Czy monitorowac nieudany backup?

Tak, to oddzielny sygnal wartosciowy: witryna moze odpowiadac, mimo ze kolejne kopie bazy sie nie tworza. Obecny monitor na Raspberry sprawdza dostepnosc HTTP i nie ma bezpiecznego dostepu do prywatnego katalogu backupow na VPS-ie. Timer backupu i testy odtworzenia nadal trzeba sprawdzac. Alert o bledzie backupu warto dodac osobno, np. jako `OnFailure` do uslugi backupu lub jako zewnetrzne sprawdzanie wieku kopii; nie nalezy publicznie wystawiac katalogu ani endpointu udostepniajacego backupy.

## Maintenance mode

Frontend ma flage build-time `VITE_MAINTENANCE`. Instrukcja wlaczenia/wylaczenia jest w [maintenance mode](notes-how2/maintenance_mode.md). Maintenance nie wymaga zatrzymania backendu ani usuwania wolumenu.

## Rollback

Przed zmiana na produkcji zachowaj informacje o wdrozonym commicie i sprawdz backup. Obecny workflow nie ma automatycznego rollbacku ani wdrazania wskazanego taga. W razie awarii zatrzymaj dalsze proby wdrozen, wlacz maintenance w razie potrzeby, przywroc znany dobry kod/obrazy bez usuwania wolumenu, uruchom healthchecki i smoke test. Odtwarzanie bazy jest osobna procedura — nie cofaj obrazu i bazy automatycznie razem bez oceny zgodnosci schematu.
