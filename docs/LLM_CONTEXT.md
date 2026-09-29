# Kontekst projektu dla LLM

Ten dokument jest instrukcja startowa dla agenta pracujacego nad repozytorium `wymiana-zajec`.

## Tozsamosc systemu

To aplikacja FastAPI + React/Vite do wymiany grup zajeciowych studentow PW. Stack: Python 3.13+, FastAPI, SQLModel, SQLite, Brevo Transactional Email API, slowapi, uv, React, Vite i lucide-react.

## Zasady bezwzgledne

1. Nigdy nie czytaj, nie wyswietlaj i nie cytuj `.env`. Korzystaj tylko z nazw zmiennych konfiguracyjnych albo `.env.example`.
2. Nie dodawaj zaleznosci przez pip. Uzywaj `python -m uv add <pakiet>`; testy uruchamiaj przez `python -m uv run pytest -q`.
3. Nie usuwaj zmian uzytkownika i nie wykonuj destrukcyjnych operacji na bazie bez wyraznej zgody.
4. Po zmianie kodu uruchom najpierw testy dotykajace zmienionego przeplywu, potem caly `pytest`.
5. Nie cofaj unikalnosci emaila ani numeru indeksu. Endpoint rejestracji odpowiada neutralnie przy duplikacie, aby nie ujawniac istnienia konta.
6. Nie ujawniaj, czy konto istnieje w reset-password request.

## Pliki wlascicielskie

- `main.py`: routing, uwierzytelnianie, rate limiting, proces wymiany, logowanie dostaw.
- `models.py`: tabele SQLModel, DTO, enumy, walidatory.
- `email_service.py`: Brevo API, tresci maili, konfiguracja przez env.
- `database.py`: SQLite engine, `create_all`, dependency sesji.
- `GET /health` w `main.py`: kontrola procesu i prostego zapytania do SQLite.
- `translations.py`: etykiety enumow.
- `tests/test_api.py`: testy kontraktow i przeplywow API.
- `tests/test_email_service.py`: testy budowy maili i konfiguracji.
- `docs/WIKI.md`: pelna dokumentacja dla zespolu.

## Obecny kontrakt biznesowy

### Konto

Rejestracja wymaga emaila w formacie `8-cyfr@pw.edu.pl`, szesciocyfrowego numeru indeksu i hasla minimum 8 znakow. Email musi zostac zweryfikowany. Link aktywacyjny wazny jest 7 dni. Resend zwraca neutralne `200` niezaleznie od istnienia i stanu konta; nowa wiadomosc jest wysylana po wygasnieciu poprzedniego linku albo po bledzie wysylki. Sesja jest wazna 7 dni i przechowywana w ciasteczku `spindel_session` z `HttpOnly`, `SameSite=Lax` oraz `Secure` na produkcji.

Reset hasla:

- request ma odpowiedz neutralna `202`,
- token resetu jest przechowywany w bazie jako SHA-256 hash,
- token wazny 1 godzine i jednorazowy,
- zmiana hasla uniewaznia auth token.

Frontend nie przechowuje tokenu sesji w JavaScript ani `localStorage`: przegladarka wysyla ciasteczko sesyjne automatycznie. `GET /csrf` wydaje token CSRF w czytelnym dla frontendu ciasteczku `spindel_csrf` i odpowiedzi JSON; frontend dodaje go jako `X-CSRF-Token` do kazdej metody modyfikujacej dane. Backend sprawdza zgodnosc tokenu cookie/header i odrzuca nieautoryzowany `Origin`. `POST /logout` uniewaznia sesje po stronie serwera i usuwa cookie sesyjne. Formularze obsluguja reset hasla, ustawienie hasla z tokenu URL `/reset-password?token=...` oraz resend weryfikacji.

Po odczytaniu tokenu verify/reset frontend usuwa go z paska adresu przez `history.replaceState`. Login ma ograniczona dlugosc, a `group_want` ma limit 5 elementow i 2 cyfry na numer grupy.

### Panel wymian: decyzje UX

Po zalogowaniu frontend ma pokazac przycisk `Moje wymiany` w naglowku. Panel dzieli dane na `Wyslane`, `Otrzymane` i `Zakonczone`. Wlasciciel moze `Potwierdz` albo `Odrzuc` otrzymane zgloszenie; potwierdzenie wymaga potwierdzajacego dialogu. Po potwierdzeniu listing przechodzi na `fulfilled`, oba emaile dostaja wiadomosc o dopasowaniu oraz email drugiej osoby. Kontakty nie sa ujawniane przed potwierdzeniem.

Odrzucenie nie oznacza powrotu do `active`: uzytkownik, ktory odrzuca zainteresowanie, dostaje monit o anulowanie ogloszenia. Po akceptacji listing ma status `cancelled`. Nie dodajemy statusu `rejected` do statusow ogloszen, poniewaz stan biznesowy ma byc przechowywany na ogloszeniu i ma wspierac szybkie wyszukiwanie aktualnych ofert.

### Ogloszenie i wymiana

Ogloszenia sa publiczne, ale tworzenie/edycja/usuwanie wymaga aktywnej sesji cookie i uprawnien wlasciciela. Jeden uzytkownik moze miec maksymalnie 8 ogloszen w statusie `active` lub `pending`. `group_have` to pojedyncza grupa, a `group_want` to lista grup w API; SQLite przechowuje ja jako posortowany tekst comma-separated. Tylko `active` jest widoczne. Zgloszenie wymaga zalogowania, nie moze byc do wlasnego ogloszenia i warunkowo przelacza `active -> pending`. Po 48 godzinach bez potwierdzenia zgloszenie wygasa, ogloszenie wraca do `active`, a wlasciciel dostaje cooldown 4 dni. Potwierdzenie zmienia zgloszenie na `confirmed` i ogloszenie na `fulfilled`. Odrzucenie oznacza `cancelled` dla zgloszenia i ogloszenia; nie dodajemy `rejected` do statusow ogloszen.

### Mail i awaria

Kazda logiczna wysylka ma `EmailDelivery`, a kazda proba `EmailDeliveryAttempt`. Nieudana wysylka jest zapisana jako `failed`. Rejestracja zwraca neutralne `201`, ale przy awarii wysylki zwraca `503`; konto zostaje w bazie niezweryfikowane. Awaria powiadomienia wymiany nie cofa zapisanej wymiany.

## Endpointy

- `POST /register` - konto, neutralna odpowiedz `201`, limit `5/minute`.
- `GET /verify?token=...` - aktywacja.
- `POST /resend-verification` - resend, limit `3/hour`.
- `GET /csrf` - inicjalizuje token CSRF i cookie; wymagane przed metodami modyfikujacymi dane.
- `POST /login` - ustawia sesyjne cookie `HttpOnly`; nie zwraca surowego tokenu, limit `10/minute`.
- `POST /logout` - uniewaznia biezaca sesje i usuwa cookie.
- `POST /password-reset/request` - neutralny request, limit `3/hour`.
- `POST /password-reset/confirm` - jednorazowa zmiana, limit `10/hour`.
- `POST /listings` - chronione tworzenie.
- `GET /listings` i `GET /listings/{id}` - publiczne aktywne ogloszenia.
- `PATCH/DELETE /listings/{id}` - tylko wlasciciel.
- `POST /listings/{id}/requests` - tylko zalogowany, tylko active.
- `GET /listings/{id}/requests` - tylko wlasciciel.
- `POST /exchange-requests/{id}/confirm` - tylko wlasciciel.
- `POST /exchange-requests/{id}/reject` - wlasciciel anuluje ogloszenie po odrzuceniu.
- `POST /listings/{id}/cancel` - wlasciciel anuluje ogloszenie.
- `GET /me/exchange-requests` - panel wyslanych i otrzymanych zgloszen.
- `GET /me/listings` - wszystkie ogloszenia zalogowanego wlasciciela, takze `pending`, `fulfilled`, `stale` i `cancelled`.
- `GET /enums` - etykiety PL/EN.
- `GET /health` - status aplikacji i bazy.

Tworzenie ogloszenia zwraca `409` z `conflicting_listing_id`, jesli istnieje aktywne ogloszenie dla odwrotnej zamiany. Frontend pokazuje bledy operacji jako toast. Odpowiedz panelu wymian zawiera `listing` ze szczegolami oraz `is_owner`; kontakty sa niepuste dopiero dla `confirmed`.

## Bezpieczenstwo i ryzyka

Hashowanie hasel uzywa `scrypt`. Tokeny generuje `secrets`; tokeny sesji, resetu hasla i weryfikacji sa przechowywane w bazie jako hashe. Cookie sesyjne ma `HttpOnly`, `SameSite=Lax`, siedmiodniowy czas zycia oraz `Secure` wlaczone przez `SESSION_COOKIE_SECURE=true` na produkcji. Wszystkie metody `POST`, `PUT`, `PATCH` i `DELETE` wymagaja zgodnego cookie CSRF i naglowka `X-CSRF-Token`. Rate limiting uzywa slowapi z pamiecia procesu, wiec nie jest jeszcze wystarczajacy dla wielu workerow. Produkcja dziala przez HTTPS/reverse proxy; pozostaje ryzyko pojedynczego VPS oraz in-memory rate limitingu. Logi aplikacji ida na stdout i nie moga zawierac sekretow ani tokenow; systemd przechwyci je przez journald.

`create_all()` nie wykonuje migracji istniejacych tabel. Zmiana modeli moze wymagac usuniecia lokalnego `database.db`; migracje sa celowo odlozone.

Docker: `docker/compose.yaml` uruchamia backend na porcie 8000 i frontend przez Nginx na porcie 5175. Frontend developerski Vite jest dostepny na porcie 5173. `docker/Dockerfile.frontend` jest wieloetapowy: Node buduje `dist`, a Nginx go serwuje. `docker/nginx.conf` przekazuje `/api/...` do uslugi `backend` i obsluguje fallback SPA. SQLite jest w external volume `docker_wymiana_data`; oba serwisy maja healthcheck, a frontend zalezy od `backend` przez `service_healthy`. Nie czytaj `.env`; Compose przekazuje je przez `env_file`.

Produkcja dziala na Hetzner VPS jako `docker compose -f docker/compose.prod.yaml`: frontendowy Nginx wystawia 80/443, Certbot odnawia certyfikat, backend nie ma publicznego portu, a SQLite jest w external volume `docker_wymiana_data`. Obrazy bazowe sa przypiete do wersji i digestow manifestow. Backend i frontend produkcyjny maja `read_only`, `cap_drop: ALL`, `no-new-privileges`, limity CPU/RAM oraz minimalne `tmpfs`; zapisy odbywaja sie tylko do wymaganych wolumenow. Systemd uruchamia `wymiana-zajec-healthcheck-inner.timer` co minute oraz `wymiana-zajec-backup.timer` co 6 godzin. Monitor korzysta z `/opt/wymiana-zajec/.env`, zapisuje stan w `/var/lib/wymiana-zajec-health/docker-status` i wysyla alerty Brevo. Payload alertu jest kodowany przez `python3`/`json.dumps`, wiec cudzyslowy i znaki nowej linii nie uszkadzaja JSON. Backup trafia do `/opt/wymiana-zajec/backups/`, ma checksum i `PRAGMA integrity_check`; wykonano test odtworzenia i potwierdzono retencje 14 kopii.

Maintenance: frontend obsluguje flage build-time `VITE_MAINTENANCE`. Na VPS ustawia sie ja w lokalnym `.env` i wykonuje `docker compose -f docker/compose.prod.yaml up -d --build frontend`; powrot do aplikacji wymaga ustawienia `false`/usuniecia zmiennej i ponownego buildu.

## Walidacja po zmianach

```powershell
python -m uv run pytest -q
```

Testy backendowe uzywaja osobnej bazy SQLite in-memory i mockuja wysylke Brevo. Przy recznym tescie uzywaj scenariusza end-to-end w `docs/WIKI.md`, sekcja 9, oraz Swaggera na `http://127.0.0.1:8000/docs`. Chronione sa endpointy wymagajace sesji cookie oraz wszystkie metody modyfikujace dane dodatkowo chronione CSRF; publiczne sa odczyty listingow, enumy, health i link verify/reset. Liczbe testow potwierdzaj wynikiem biezacego uruchomienia, nie utrzymuj jej recznie w tym dokumencie.

## Decyzje wdrozeniowe

Na obecnym etapie aplikacja dziala jako jedna instancja Docker Compose na VPS-ie. Nie dodawaj Redisa ani architektury klastrowej bez decyzji o skalowaniu. Frontend jest serwowany przez Nginx, a Nginx przekazuje API do backendu.

## Preferowany sposob zmian

Przed edycja sformuluj lokalna hipoteze i najtanszy test, ktory ja obali. Zmieniaj najmniejszy wlascicielski modul. Dla zmian auth/mail zawsze dodaj test braku wycieku danych, jednorazowosci tokenu lub poprawnego statusu bledu. Nie czytaj sekretow, aby diagnozowac konfiguracje; sprawdzaj obecnosc nazw zmiennych albo wynik endpointu.