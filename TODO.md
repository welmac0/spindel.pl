# TODO

## Najblizszy etap

- [x] Uruchomic pelny Compose lokalnie i potwierdzic status `healthy` backendu i frontendu.
- [x] Wykonac smoke test przez frontend: logowanie, listing, wymiana i panel.
- [X] Wykonac commit etapu frontend + Nginx + Compose.
- [X] Przygotowac VPS Linux i wdrozenie stagingowe.

## Backup SQLite na serwerze Unix

- [x] Zainstalowac `wymiana-zajec-backup.service` i `wymiana-zajec-backup.timer` na VPS.
- [x] Wykonac pierwszy backup external volume `docker_wymiana_data`.
- [x] Zapisywac backupy w `/opt/wymiana-zajec/backups/` poza wolumenem aplikacji.
- [x] Sprawdzac kod wyjscia skryptu: `0` oznacza udany backup, `1` oznacza blad.
- [x] Sprawdzic logi backupu przez `journalctl -u wymiana-zajec-backup.service`.
- [x] Potwierdzic, ze retencja 14 ostatnich kopii dziala.
- [x] Okresowo wykonac test odtworzenia backupu przez `PRAGMA integrity_check`.

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
- [x] Backupy trzymac osobno na hoście (`backups/`); backend nie powinien miec do nich dostepu.
- [x] Backup wykonywac z hosta przez `sqlite3 .backup` i okresowo testowac odtworzenie.
- [x] Kopiowac backupy poza serwer na Maca przez SSH/rsync i weryfikowac checksumy.

## Docker Compose frontend + backend

- [x] Zbudowac frontend wieloetapowo przez Node i Nginx.
- [x] Skonfigurowac Nginx jako serwer SPA i proxy `/api` do uslugi `backend`.
- [x] Dodac frontend do `docker/compose.yaml`.
- [x] Dodac healthcheck frontendu sprawdzajacy Nginx przez HTTP.
- [x] Dodac `depends_on` z warunkiem `service_healthy` dla backendu.
- [x] Ograniczyc publiczne wystawienie portu backendu na produkcji.

## Limity biznesowe

- [x] Ograniczyc liczbe aktywnych i oczekujacych ogloszen jednego uzytkownika do 8.
- [x] Dodac test backendowy limitu 8 ogloszen i czytelny komunikat bledu API.

## Frontend: mobile i lokalizacja

- [x] Poprawic mobilne filtry kierunkow: nazwy kierunkow nie moga byc zaslaniane przez checkboxy.
- [x] Przetlumaczyc komunikaty pustych stanow, bledow, auth, filtrow i panelu wymian na PL/EN.
- [x] Sprawdzic build frontendu dla obu wersji jezykowych.

## Branding i tresci

- [ ] Zmienic teksty strony tak, aby byly ukierunkowane na wydzial i studentow PW.
- [ ] Zaprojektowac i dodac docelowe logo Spindel.
- [x] Dodac stopke z podstawowymi informacjami, kontaktem i linkami formalnymi.
- [x] Dodac roboczy regulamin i polityke prywatnosci jako strony publiczne.

## Bezpieczenstwo przed produkcja

- [X] Uniewaznic ujawniony klucz Brevo i wygenerowac nowy klucz produkcyjny.
- [X] Nie uruchamiac publicznie `docker compose config`, bo rozwija wartosci z `env_file`.
- [x] Wdrozyc HTTPS i przekierowanie HTTP -> HTTPS.
- [ ] Dodac `Referrer-Policy: no-referrer` i usuwac tokeny verify/reset z adresu po ich odczytaniu.
- [ ] Rozwazyc przeniesienie sesji z `localStorage` do ciasteczka `HttpOnly`, `Secure`, `SameSite`.
- [x] Dodac limity rate limitingu dla tworzenia ogloszen, requestow wymian, anulowania i potwierdzania.
- [ ] Dodac limity dlugosci loginu oraz liczby i rozmiaru elementow `group_want`.
- [ ] Ujednolicic odpowiedzi rejestracji i resend, jezeli chcemy unikac enumeracji kont.
- [x] Dodac HSTS, `X-Content-Type-Options` i `Referrer-Policy` w produkcyjnym Nginx.
- [x] Dodac CSP i ochrone przed framingiem w Nginx.
- [x] Przypiac wersje zaleznosci frontendowych.
- [ ] Przypiac wersje i digesty obrazow Dockerowych zamiast nieokreslonych tagow.
- [ ] Rozwazyc hardening kontenerow: `read_only`, `cap_drop`, limity CPU/RAM i minimalne `tmpfs`.
- [ ] Poprawic JSON escaping w alertach Bash wysylanych przez Brevo.

## Przerwa techniczna

- [x] Dodac kontrolowany tryb maintenance dla frontendu, z czytelnym komunikatem zamiast bledow API `502` przy zatrzymanym backendzie.
- [x] Dodac prosta procedure wlaczania i wylaczania maintenance przez `VITE_MAINTENANCE` i rebuild frontendu.

## Backlog

| Temat | Opis | Krytycznosc |
|---|---|---|
| Sesja HttpOnly | Zastapic token w `localStorage` ciasteczkiem `HttpOnly`, `Secure`, `SameSite` i dodac ochrone CSRF. | Wysoka przed wieksza beta |
| Limity wejscia | Ograniczyc dlugosc loginu oraz liczbe i rozmiar elementow `group_want`. | Srednia |
| Enumeracja kont | Ujednolicic odpowiedzi rejestracji i resend, aby nie ujawniac istnienia kont. | Srednia |
| Przypiecie obrazow | Przypiac wersje i digesty obrazow Dockerowych zamiast nieokreslonych tagow. | Srednia |
| Hardening kontenerow | Rozwazyc `read_only`, `cap_drop`, limity CPU/RAM i minimalne `tmpfs`. | Niska |
| Alert JSON | Dodac bezpieczne JSON escaping w skryptach Bash wysylajacych alerty Brevo. | Niska |
| Zewnetrzny monitoring | Dodac monitoring niezalezny od VPS i jego systemd. | Niska |
| Migracje | Dodac migracje schematu, np. Alembic. | Srednia |
| Kolejka maili | Przeniesc wysylke maili do kolejki asynchronicznej. | Niska |
| Moderacja | Dodac panel administracyjny i proces zglaszania tresci. | Niska |

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