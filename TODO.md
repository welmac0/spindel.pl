# TODO

## Najblizszy etap

- [x] Uruchomic pelny Compose lokalnie i potwierdzic status `healthy` backendu i frontendu.
- [x] Wykonac smoke test przez frontend: logowanie, listing, wymiana i panel.
- [X] Wykonac commit etapu frontend + Nginx + Compose.
- [X] Przygotowac VPS Linux i wdrozenie stagingowe.

## Backup SQLite na serwerze Unix

- [ ] Zainstalowac `wymiana-zajec-backup.service` i `wymiana-zajec-backup.timer` na VPS.
- [ ] Wykonac pierwszy backup external volume `docker_wymiana_data`.
- [ ] Zapisywac backupy w `/opt/wymiana-zajec/backups/` poza wolumenem aplikacji.
- [ ] Sprawdzac kod wyjscia skryptu: `0` oznacza udany backup, `1` oznacza blad.
- [ ] Sprawdzic logi backupu przez `journalctl -u wymiana-zajec-backup.service`.
- [ ] Potwierdzic, ze retencja 14 ostatnich kopii dziala.
- [ ] Okresowo wykonac test odtworzenia backupu przez `PRAGMA integrity_check`.

Backup produkcyjny uzywa systemd timera co 6 godzin i kopiuje baze z external volume przez tymczasowy kontener Pythona.

## Docker monitor on the host

- [x] Skopiowac `scripts/check_health_inner.sh` do `/opt/wymiana-zajec/scripts/`.
- [x] Upewnic sie, ze Compose ma healthcheck `/health` dla uslugi `backend`.
- [x] Umiescic produkcyjny `.env` w `/opt/wymiana-zajec/.env` z prawami `chmod 600`.
- [x] Zainstalowac `wymiana-zajec-healthcheck-inner.service` z `ExecStart=/opt/wymiana-zajec/scripts/check_health_inner.sh` i `EnvironmentFile=/opt/wymiana-zajec/.env`.
- [x] Utworzyc timer `wymiana-zajec-healthcheck-inner.timer` uruchamiany co minute (`OnUnitActiveSec=1min`).
- [x] Wykonac `systemctl daemon-reload` oraz `systemctl enable --now wymiana-zajec-healthcheck-inner.timer`.
- [x] Sprawdzic wynik przez `systemctl status wymiana-zajec-healthcheck-inner.timer` i `journalctl -u wymiana-zajec-healthcheck-inner.service`.
- [x] Potwierdzic przejscie monitora `down -> up` po przywroceniu zdrowego backendu.

## Docker storage

- [x] SQLite trzymac na trwalym external named volume `docker_wymiana_data`, nie w warstwie kontenera.
- [ ] Backupy trzymac osobno na hoście (`backups/`); backend nie powinien miec do nich dostepu.
- [ ] Backup wykonywac z hosta przez `sqlite3 .backup` i okresowo testowac odtworzenie.
- [ ] Docelowo kopiowac backupy poza serwer (inny dysk, NAS albo object storage).

## Docker Compose frontend + backend

- [x] Zbudowac frontend wieloetapowo przez Node i Nginx.
- [x] Skonfigurowac Nginx jako serwer SPA i proxy `/api` do uslugi `backend`.
- [x] Dodac frontend do `docker/compose.yaml`.
- [x] Dodac healthcheck frontendu sprawdzajacy Nginx przez HTTP.
- [x] Dodac `depends_on` z warunkiem `service_healthy` dla backendu.
- [x] Ograniczyc publiczne wystawienie portu backendu na produkcji.

## Limity biznesowe

- [ ] Ograniczyc liczbe aktywnych i oczekujacych ogloszen jednego uzytkownika do 8.
- [ ] Dodac test backendowy limitu 8 ogloszen i czytelny komunikat w frontendzie.

## Frontend: mobile i lokalizacja

- [ ] Poprawic mobilne filtry kierunkow: nazwy kierunkow nie moga byc zaslaniane przez checkboxy.
- [ ] Przetlumaczyc wszystkie komunikaty pustych stanow, bledow i informacji z bazy na PL/EN.
- [ ] Sprawdzic tlumaczenia na desktopie i telefonie dla obu wersji jezykowych.

## Branding i tresci

- [ ] Zmienic teksty strony tak, aby byly ukierunkowane na wydzial i studentow PW.
- [ ] Zaprojektowac i dodac docelowe logo Spindel.
- [ ] Dodac stopke z podstawowymi informacjami, kontaktem i linkami formalnymi.

## Bezpieczenstwo przed produkcja

- [X] Uniewaznic ujawniony klucz Brevo i wygenerowac nowy klucz produkcyjny.
- [X] Nie uruchamiac publicznie `docker compose config`, bo rozwija wartosci z `env_file`.
- [x] Wdrozyc HTTPS i przekierowanie HTTP -> HTTPS.
- [ ] Dodac `Referrer-Policy: no-referrer` i usuwac tokeny verify/reset z adresu po ich odczytaniu.
- [ ] Rozwazyc przeniesienie sesji z `localStorage` do ciasteczka `HttpOnly`, `Secure`, `SameSite`.
- [ ] Dodac limity rate limitingu dla requestow wymian, anulowania i potwierdzania.
- [ ] Dodac limity dlugosci loginu oraz liczby i rozmiaru elementow `group_want`.
- [ ] Ujednolicic odpowiedzi rejestracji i resend, jezeli chcemy unikac enumeracji kont.
- [x] Dodac HSTS, `X-Content-Type-Options` i `Referrer-Policy` w produkcyjnym Nginx.
- [ ] Dodac CSP i ochrone przed framingiem w Nginx.
- [ ] Przypiac wersje zaleznosci frontendowych i obrazow Dockerowych zamiast `latest`.
- [ ] Rozwazyc hardening kontenerow: `read_only`, `cap_drop`, limity CPU/RAM i minimalne `tmpfs`.
- [ ] Poprawic JSON escaping w alertach Bash wysylanych przez Brevo.

## Przerwa techniczna

- [ ] Dodac kontrolowany tryb maintenance dla frontendu, z czytelnym komunikatem zamiast bledow API `502` przy zatrzymanym backendzie.
- [ ] Dodac bezpieczna procedure wlaczania i wylaczania przerwy technicznej wraz z czasowym wylaczeniem alertow healthchecka.

## Infrastruktura: e-mail, hosting i domena

teraz              Docker Compose na VPS + domena + HTTPS + monitoring
przed beta testami backupy SQLite i test odtworzenia
przed publikacją   pozostaly hardening i zewnetrzny monitoring

### E-mail (wdrożone)
- Wysyłka transakcyjna przez Brevo (darmowy plan, 300 maili/dzień)
- Wysyłka z poddomeny `app.maciejwelpa.pl`, odseparowanej od domeny głównej (strona www)
- SPF + DKIM skonfigurowane w Cloudflare DNS, domena zweryfikowana w Brevo
- Uwierzytelnianie przez API key (nie SMTP) — mniejsze ryzyko blokady portów na hostingu, czytelniejsza obsługa błędów w kodzie

### Hosting (wdrozony)
- Hetzner Cloud, plan CX22/CX23 (~€5-8/mies., stała cena, 20 TB transferu wliczone)
- Wybrany zamiast Render/Railway/Fly.io — te mają albo cold-starty (Render free), albo rozliczenie per-użycie z ryzykiem nieprzewidywalnego rachunku (Railway, Fly.io)
- Docker Compose + własny Nginx na jednym VPS, SQLite na trwałym wolumenie, backupy wykonywane z poziomu hosta

### Domena projektu (wdrozona) spindel.pl
- `.pl` jako rozszerzenie — grupa docelowa to studenci PW
- Rejestracja przez OVH (konto już istnieje) — uczciwsze ceny odnowienia (~85 zł/rok) niż CyberFolks/nazwa.pl/home.pl (179-200 zł/rok)
- Nameservery na Cloudflare, analogicznie do `maciejwelpa.pl`
- Nazwa: nieustalona — wstępna pula: swapgrupa, wymianka, grupomat, classswap (bez sprawdzenia dostępności)