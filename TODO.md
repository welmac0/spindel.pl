# TODO

## Najblizszy etap

- [x] Uruchomic pelny Compose lokalnie i potwierdzic status `healthy` backendu i frontendu.
- [x] Wykonac smoke test przez frontend: logowanie, listing, wymiana i panel.
- [X] Wykonac commit etapu frontend + Nginx + Compose.
- [X] Przygotowac VPS Linux i wdrozenie stagingowe.

## Backup SQLite na serwerze Unix

- [ ] Skonfigurować cron na serwerze, aby uruchamiał `scripts/backup_sqlite.sh` co 6 godzin.
- [ ] Uruchamiać skrypt z katalogu projektu lub używać ścieżek absolutnych.
- [ ] Zapisywać stdout i stderr do pliku logu poza repozytorium.
- [ ] Sprawdzać kod wyjścia skryptu: `0` oznacza udany backup, `1` oznacza błąd.
- [ ] Skonfigurować alert lub ręczny przegląd logów po nieudanym backupie.
- [ ] Potwierdzić, że retencja 14 ostatnich kopii działa.
- [ ] Okresowo wykonać test odtworzenia backupu przez `PRAGMA integrity_check`.

Przykładowy wpis cron do skonfigurowania na serwerze:

```cron
0 */6 * * * cd /opt/wymiana-zajec && ./scripts/backup_sqlite.sh >> /var/log/wymiana-zajec-backup.log 2>&1
```

## Backend jako usluga systemd

- [x] Utworzyc uzytkownika systemowego `wymiana`.
- [ ] Umiescic projekt w `/opt/wymiana-zajec`.
- [ ] Utworzyc srodowisko uv w projekcie.
- [ ] Umiescic sekrety w `/etc/wymiana-zajec/wymiana-zajec.env` z prawami tylko dla wlasciciela.
- [ ] Skopiowac `deployment/systemd/wymiana-zajec.service` do `/etc/systemd/system/`.
- [ ] Wykonac `systemctl daemon-reload`.
- [ ] Wlaczyc start przy uruchomieniu systemu przez `systemctl enable wymiana-zajec`.
- [ ] Uruchomic usluge przez `systemctl start wymiana-zajec`.
- [ ] Sprawdzic status przez `systemctl status wymiana-zajec`.
- [ ] Sprawdzic logi przez `journalctl -u wymiana-zajec`.

## Alerty niedostepnosci

- [ ] Dodac `ALERT_EMAIL` do pliku sekretow na serwerze.
- [ ] Skopiowac `deployment/systemd/wymiana-zajec-healthcheck.service` i `.timer` do `/etc/systemd/system/`.
- [ ] Nadać skryptowi health check prawa wykonywania.
- [ ] Wlaczyc timer przez `systemctl enable --now wymiana-zajec-healthcheck.timer`.
- [ ] Sprawdzic logi monitora przez `journalctl -u wymiana-zajec-healthcheck`.
- [ ] Wykonac kontrolowany test niedostepnosci backendu.
- [ ] Rozwazyc zewnetrzny monitoring, ktory zadziala takze po awarii calego serwera.

### Docker monitor on the host

- [ ] Skopiowac `scripts/check_health_inner.sh` do `/opt/wymiana-zajec/scripts/`.
- [x] Upewnic sie, ze Compose ma healthcheck `/health` dla uslugi `backend`.
- [ ] Utworzyc `/etc/wymiana-zajec/wymiana-zajec-health.env` z `BREVO_API_KEY`, `BREVO_SENDER_EMAIL`, `BREVO_SENDER_NAME` i `ALERT_EMAIL`; ustawic `chmod 600`.
- [ ] Utworzyc osobna usluge `wymiana-zajec-healthcheck-inner.service` z `ExecStart=/opt/wymiana-zajec/scripts/check_health_inner.sh` i `EnvironmentFile=/etc/wymiana-zajec/wymiana-zajec-health.env`.
- [ ] Utworzyc timer `wymiana-zajec-healthcheck-inner.timer` uruchamiany co minute (`OnUnitActiveSec=1min`).
- [ ] Wykonac `systemctl daemon-reload` oraz `systemctl enable --now wymiana-zajec-healthcheck-inner.timer`.
- [ ] Sprawdzic wynik przez `systemctl status wymiana-zajec-healthcheck-inner.timer` i `journalctl -u wymiana-zajec-healthcheck-inner.service`.
- [ ] Przetestowac awarie: zatrzymac backend, potwierdzic alert `down`, uruchomic backend i potwierdzic alert recovery.

## Docker storage

- [x] SQLite trzymac na trwalym named volume `wymiana_data`, nie w warstwie kontenera.
- [ ] Backupy trzymac osobno na hoście (`backups/`); backend nie powinien miec do nich dostepu.
- [ ] Backup wykonywac z hosta przez `sqlite3 .backup` i okresowo testowac odtworzenie.
- [ ] Docelowo kopiowac backupy poza serwer (inny dysk, NAS albo object storage).

## Docker Compose frontend + backend

- [x] Zbudowac frontend wieloetapowo przez Node i Nginx.
- [x] Skonfigurowac Nginx jako serwer SPA i proxy `/api` do uslugi `backend`.
- [x] Dodac frontend do `docker/compose.yaml`.
- [x] Dodac healthcheck frontendu sprawdzajacy Nginx przez HTTP.
- [x] Dodac `depends_on` z warunkiem `service_healthy` dla backendu.
- [ ] Ograniczyc publiczne wystawienie portu backendu na produkcji.

## Bezpieczenstwo przed produkcja

- [X] Uniewaznic ujawniony klucz Brevo i wygenerowac nowy klucz produkcyjny.
- [X] Nie uruchamiac publicznie `docker compose config`, bo rozwija wartosci z `env_file`.
- [ ] Wdrozyc HTTPS i przekierowanie HTTP -> HTTPS.
- [ ] Dodac `Referrer-Policy: no-referrer` i usuwac tokeny verify/reset z adresu po ich odczytaniu.
- [ ] Rozwazyc przeniesienie sesji z `localStorage` do ciasteczka `HttpOnly`, `Secure`, `SameSite`.
- [ ] Dodac limity rate limitingu dla requestow wymian, anulowania i potwierdzania.
- [ ] Dodac limity dlugosci loginu oraz liczby i rozmiaru elementow `group_want`.
- [ ] Ujednolicic odpowiedzi rejestracji i resend, jezeli chcemy unikac enumeracji kont.
- [ ] Dodac naglowki CSP, HSTS, `X-Content-Type-Options` i ochrone przed framingiem w Nginx.
- [ ] Przypiac wersje zaleznosci frontendowych i obrazow Dockerowych zamiast `latest`.
- [ ] Rozwazyc hardening kontenerow: `read_only`, `cap_drop`, limity CPU/RAM i minimalne `tmpfs`.
- [ ] Poprawic JSON escaping w alertach Bash wysylanych przez Brevo.

## Infrastruktura: e-mail, hosting i domena

teraz              lokalny development + Docker lokalnie
przed beta testami domena + tani hosting/staging
przed publikacją   HTTPS + Nginx + Brevo + backupy + monitoring

### E-mail (wdrożone)
- Wysyłka transakcyjna przez Brevo (darmowy plan, 300 maili/dzień)
- Wysyłka z poddomeny `app.maciejwelpa.pl`, odseparowanej od domeny głównej (strona www)
- SPF + DKIM skonfigurowane w Cloudflare DNS, domena zweryfikowana w Brevo
- Uwierzytelnianie przez API key (nie SMTP) — mniejsze ryzyko blokady portów na hostingu, czytelniejsza obsługa błędów w kodzie

### Hosting (rekomendacja, do decyzji) 
- Hetzner Cloud, plan CX22/CX23 (~€5-8/mies., stała cena, 20 TB transferu wliczone)
- Wybrany zamiast Render/Railway/Fly.io — te mają albo cold-starty (Render free), albo rozliczenie per-użycie z ryzykiem nieprzewidywalnego rachunku (Railway, Fly.io)
- Docker Compose + własny Nginx na jednym VPS, SQLite na trwałym wolumenie, backupy wykonywane z poziomu hosta

### Domena projektu (rekomendacja, do decyzji) spindel.pl
- `.pl` jako rozszerzenie — grupa docelowa to studenci PW
- Rejestracja przez OVH (konto już istnieje) — uczciwsze ceny odnowienia (~85 zł/rok) niż CyberFolks/nazwa.pl/home.pl (179-200 zł/rok)
- Nameservery na Cloudflare, analogicznie do `maciejwelpa.pl`
- Nazwa: nieustalona — wstępna pula: swapgrupa, wymianka, grupomat, classswap (bez sprawdzenia dostępności)