# Wiki projektu: Wymiana Grup PW

## 1. Cel projektu

Wymiana Grup PW to backend aplikacji, w ktorej student moze opublikowac ogloszenie o zamianie grupy zajeciowej. Inny zweryfikowany student moze zlozyc aplikacje na wymiane. Wymiana wymaga potwierdzenia przez wlasciciela ogloszenia.

Frontend jest zaimplementowany jako React/Vite. W trybie developerskim korzysta z proxy `/api` do backendu FastAPI.

## 2. Stan obecny

Zaimplementowane:

- FastAPI z uruchamianiem przez Uvicorn.
- SQLModel i SQLite.
- Rejestracja z emailem PW, numerem indeksu i haslem.
- Hashowanie hasel przez `hashlib.scrypt`.
- Weryfikacja emaila przez Brevo Transactional API.
- Token aktywacyjny wazny 7 dni.
- Ponowienie maila weryfikacyjnego po wygasnieciu albo po bledzie wysylki.
- Logowanie przez siedmiodniowe cookie sesyjne `HttpOnly`, `SameSite=Lax` i `Secure` na produkcji.
- Reset hasla z jednorazowym tokenem waznym 1 godzine.
- Uniewaznianie aktywnych sesji po zmianie hasla i wylogowaniu.
- Publiczna lista aktywnych ogloszen.
- Wlasciciel ogloszenia i kontrola praw do edycji/usuwania.
- Zgloszenie do ogloszenia tylko przy statusie `active`.
- Atomowe przejscie ogloszenia z `active` do `pending`.
- Potwierdzenie wymiany i zamkniecie ogloszenia.
- Wygasanie zgloszenia po 48 godzinach i cooldown wlasciciela przez 4 dni.
- Maile o rejestracji, zgloszeniu i potwierdzeniu wymiany.
- Tabele `EmailDelivery` i `EmailDeliveryAttempt`.
- Rate limiting wraz z `slowapi`.
- Logowanie aplikacji przez standardowy logger na stdout.
- Endpoint `GET /health` sprawdzajacy dostep do bazy.
- Frontend React/Vite: logowanie, rejestracja, listingi, filtry, tworzenie ogloszen i panel wymian.
- Sesja przegladarki przez cookie `HttpOnly`; token nie jest dostepny dla JavaScript ani przechowywany w `localStorage`.
- Ochrona CSRF wszystkich metod `POST`, `PUT`, `PATCH` i `DELETE` przez token double-submit.
- Frontendowe formularze resetu hasla i ponowienia weryfikacji emaila.
- Wieloetapowy Dockerfile frontendu: Node buduje aplikacje, Nginx serwuje `dist`.
- Compose z backendem, frontendem, named volume SQLite, healthcheckami i zaleznoscia `service_healthy`.
- Nginx przekazuje `/api/...` do uslugi `backend`, a pozostale sciezki serwuje jako SPA.
- Automatyczne testy backendowe dla auth, cookie sesyjnego, wylogowania i CSRF.

Niezaimplementowane:

- Wspoldzielony storage rate limitingu, np. Redis.
- Migracje schematu bazy danych.
- Kolejka asynchronicznej wysylki maili.
- Administracja i moderacja.

Wdrozone produkcyjnie na VPS:

- Ubuntu na Hetzner Cloud z uzytkownikiem `spindel` i logowaniem root SSH wylaczonym.
- Domena `spindel.pl` wskazuje na VPS, a HTTPS obsluguje Nginx w kontenerze frontendowym.
- Docker Compose produkcyjny uruchamia backend, frontend i Certbota.
- SQLite jest w external volume `docker_wymiana_data`.
- Systemd timer monitoruje healthcheck backendu co minute i wysyla alerty przez Brevo przy zmianie stanu.
- Systemd timer wykonuje backup SQLite co 6 godzin do `/opt/wymiana-zajec/backups/`.

## 3. Struktura plikow

```text
src/wymiana_zajec/database.py       silnik SQLite i zaleznosc sesji
src/wymiana_zajec/email_service.py  integracja z Brevo i tresci maili
src/wymiana_zajec/main.py           aplikacja FastAPI, endpointy i logika procesu
src/wymiana_zajec/models.py         modele SQLModel, enumy i walidacja
src/wymiana_zajec/translations.py   etykiety enumow PL/EN
pyproject.toml              zaleznosci i konfiguracja uv
uv.lock                    zablokowane wersje zaleznosci
src/wymiana_zajec/          entrypoint pakietu CLI
tests/conftest.py           import root modules podczas testow
tests/test_api.py            testy API i przeplywow biznesowych
tests/test_email_service.py  testy tresci i konfiguracji maili
docs/WIKI.md                dokumentacja projektu
docs/LLM_CONTEXT.md         kontekst do pracy z LLM
database.db                 lokalna baza developerska, ignorowana przez git
```

## 4. Uruchomienie

Zaleznosci sa zarzadzane przez uv. Nie uzywaj `pip install` do dodawania zaleznosci projektu.

```powershell
python -m uv sync
python -m uv run pytest -q
python -m uv run uvicorn wymiana_zajec.main:app --reload
```

API:

- Swagger: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

Frontend developerski uruchamiaj osobno:

```powershell
cd frontend
npm install
npm run dev
```

Frontend jest wtedy dostepny pod `http://localhost:5173`, a Vite przekazuje `/api` do backendu na porcie 8000.

Backend przez Docker:

```powershell
docker compose -f docker/compose.yaml up --build
```

Compose developerski uruchamia backend na `http://localhost:8000`, frontend przez Nginx na `http://localhost:5175` i przechowuje SQLite w external volume `docker_wymiana_data`. Produkcyjny `compose.prod.yaml` wystawia frontend na 80/443, nie publikuje backendu i uzywa Certbota. Healthcheck backendu sprawdza `/health`, a healthcheck frontendu sprawdza endpoint Nginxa.

Nie uzywaj `docker compose down -v`, jezeli chcesz zachowac baze w wolumenie.

### Przerwa techniczna

Frontend ma prosty tryb maintenance sterowany podczas budowania obrazu. Na VPS ustaw `VITE_MAINTENANCE=true` w lokalnym `.env`, przebuduj tylko frontend i uruchom go ponownie:

```bash
docker compose -f docker/compose.prod.yaml up -d --build frontend
```

Aby wrocic do normalnej strony, ustaw `VITE_MAINTENANCE=false` albo usun te zmienna i wykonaj te sama komende. Nie zatrzymuj backendu bez potrzeby; podczas planowanej przerwy mozesz zatrzymac timer healthchecka, aby nie wysylal alertow o celowej niedostepnosci.

Konfiguracja maili korzysta ze zmiennych srodowiskowych `BREVO_API_KEY`, `BREVO_SENDER_EMAIL`, `BREVO_SENDER_NAME` i `APP_BASE_URL`. Nie umieszczaj ich wartosci w dokumentacji, issue ani commitach.

## 5. Kontrakt API

### Uzytkownicy i uwierzytelnianie

#### `POST /register`

Tworzy uzytkownika i wysyla mail aktywacyjny.

Body:

```json
{
  "email": "12345678@pw.edu.pl",
  "index_number": "123456",
  "password": "minimum 8 znakow"
}
```

Odpowiedzi:

- `201` - neutralna odpowiedz po przetworzeniu danych; nie ujawnia, czy konto juz istnialo.
- `503` - konto zapisane, ale wysylka maila sie nie udala; dostawa ma status `failed` i mozna uzyc resend.

#### `GET /verify?token=...`

Jednorazowo aktywuje konto. Token wygasa po 7 dniach.

- `200` - konto zweryfikowane.
- `404` - token nie istnieje albo zostal juz zuzyty.
- `410` - token wygasl.

#### `POST /resend-verification`

Body:

```json
{"email": "12345678@pw.edu.pl"}
```

Zwraca neutralny komunikat i `200`, takze dla nieznanego, juz zweryfikowanego albo chwilowo zablokowanego konta. Nowy mail mozna wyslac po wygasnieciu poprzedniego udanego maila. Po `failed` mozna probowac od razu. Limit: `3/hour` na IP.

#### `GET /csrf`

Ustawia cookie `spindel_csrf` (`SameSite=Lax`, `Secure` na produkcji) i zwraca token w JSON. Frontend przekazuje jego wartosc w naglowku `X-CSRF-Token` przy kazdym `POST`, `PUT`, `PATCH` i `DELETE`. Backend sprawdza zgodnosc cookie i naglowka, a jesli request ma naglowek `Origin`, porownuje z originem hosta/serwera proxy lub lista `ALLOWED_ORIGINS`. Brak tokenu, niezgodnosc lub nieautoryzowany origin zwraca `403`.

#### `POST /login`

Dostep tylko dla zweryfikowanych kont. Ustawia cookie `spindel_session` wazne 7 dni z flagami `HttpOnly`, `SameSite=Lax` i `Secure` na produkcji. Surowy token nie jest zwracany w JSON. Limit: `10/minute` na IP.

#### `POST /logout`

Wymaga aktywnej sesji i tokenu CSRF. Uniewaznia sesje po stronie serwera i wygasza cookie sesyjne. Zwraca `204`.

#### `POST /password-reset/request`

Body:

```json
{"email": "12345678@pw.edu.pl"}
```

Zawsze zwraca ten sam komunikat i `202`, aby nie ujawniac, czy konto istnieje. Dla zweryfikowanego konta wysyla token resetu wazny 1 godzine. Limit: `3/hour` na IP.

#### `POST /password-reset/confirm`

Body:

```json
{
  "token": "token_z_maila",
  "password": "nowe_haslo"
}
```

Token jest jednorazowy. Po zmianie hasla biezaca sesja cookie zostaje uniewazniona. Limit: `10/hour` na IP.

### Ogloszenia

#### `POST /listings`

Wymaga sesji cookie i prawidlowego tokenu CSRF. Tworzy ogloszenie nalezace do zalogowanego uzytkownika. Nie mozna tworzyc ogloszen w czasie 4-dniowego cooldownu.

Jeden uzytkownik moze miec maksymalnie 8 ogloszen w statusie `active` albo `pending`. Po osiagnieciu limitu endpoint zwraca `409`.

Lista `group_want` moze zawierac maksymalnie 5 grup, a numer grupy maksymalnie 2 cyfry. Login i haslo maja limity dlugosci wejscia.

`group_have` jest pojedyncza grupa, a `group_want` lista grup, np. `["14", "15"]`. Backend usuwa duplikaty i sortuje liste. W SQLite lista jest przechowywana jako tekst `"14,15"`. Jesli istnieje aktywne ogloszenie dla odwrotnej zamiany, odpowiedz to `409` z `conflicting_listing_id`.

#### `GET /listings`

Publiczne. Zwraca tylko ogloszenia ze statusem `active`. Obslugiwane parametry: `limit` 1-100 i `offset` od 0.

#### `GET /listings/{listing_id}`

Publiczne. Ogloszenia `pending`, `fulfilled`, `stale` i `cancelled` sa niewidoczne i zwracaja `404`.

#### `PATCH /listings/{listing_id}`

Wymaga sesji cookie, tokenu CSRF i bycia wlascicielem. Statusu nie mozna zmienic przez PATCH. Grupy `group_have` i `group_want` musza byc rozne.

#### `DELETE /listings/{listing_id}`

Wymaga sesji cookie, tokenu CSRF i bycia wlascicielem. Zwraca `204`.

### Wymiana

#### Ustalony UX panelu wymian

Po zalogowaniu w naglowku pojawia sie przycisk `Moje wymiany`. Widok ma trzy logiczne sekcje: `Wyslane`, `Otrzymane` i `Zakonczone`.

Wlasciciel ogloszenia widzi osobe zainteresowana oraz akcje `Potwierdz` i `Odrzuc`. Potwierdzenie wymaga dialogu z informacja, ze ogloszenie zostanie zamkniete. Po potwierdzeniu ogloszenie ma status `fulfilled`, obie osoby widza email drugiej osoby i obie dostaja email z krotkim opisem dopasowania.

Odrzucenie nie tworzy statusu `rejected` dla ogloszenia. Pokazuje monit o anulowaniu, a po potwierdzeniu ogloszenie przechodzi na `cancelled`; nie wraca do `active`, bo oznacza to, ze szukana zamiana przestala byc aktualna. Wyslane zgloszenie nie ujawnia emaila wlasciciela przed potwierdzeniem.

#### `POST /listings/{listing_id}/requests`

Wymaga sesji cookie i tokenu CSRF, a uzytkownik nie moze byc wlascicielem ogloszenia. Przejscie jest dozwolone tylko dla `active`. W jednej operacji bazodanowej ogloszenie jest zmieniane na `pending`; drugi request nie przejdzie.

Okno potwierdzenia: 48 godzin.

#### `GET /listings/{listing_id}/requests`

Wymaga sesji cookie i bycia wlascicielem ogloszenia.

#### `POST /exchange-requests/{request_id}/confirm`

Wymaga sesji cookie i tokenu CSRF wlasciciela. Zmienia zgloszenie na `confirmed`, a ogloszenie na `fulfilled`. Obie osoby dostaja mail z krotkim opisem dopasowania i emailem drugiej osoby; kontakty sa ujawniane dopiero po potwierdzeniu.

#### `POST /exchange-requests/{request_id}/reject`

Wymaga sesji cookie i tokenu CSRF wlasciciela. Zgloszenie dostaje `cancelled`, a ogloszenie `cancelled`. Nie ma statusu ogloszenia `rejected`: odrzucenie oznacza, ze ogloszenie przestalo byc aktualne.

#### `POST /listings/{listing_id}/cancel`

Wymaga sesji cookie i tokenu CSRF wlasciciela. Anuluje ogloszenie ze statusu `active` albo `pending`, zachowujac historie.

#### `GET /me/exchange-requests`

Wymaga sesji cookie. Zwraca wyslane przez uzytkownika zgloszenia oraz zgloszenia do jego ogloszen. Frontend pokazuje je jako `Wyslane`, `Otrzymane` i `Zakonczone`.

### Pozostale

#### `GET /enums?lang=pl|en`

Zwraca slownik kodow enumow i etykiet do wyswietlenia.

#### `GET /health`

Sprawdza, czy aplikacja dziala i czy sesja moze wykonac proste zapytanie do SQLite. Zwraca `{"status":"ok"}` albo `503` bez ujawniania szczegolow bledu.

### Endpointy chronione

Kazdy z ponizszych endpointow wymaga cookie sesyjnego ustawionego przez `POST /login`:

- `POST /listings`
- `PATCH /listings/{listing_id}`
- `DELETE /listings/{listing_id}`
- `POST /listings/{listing_id}/requests`
- `GET /listings/{listing_id}/requests`
- `POST /exchange-requests/{request_id}/confirm`
- `POST /exchange-requests/{request_id}/reject`
- `POST /listings/{listing_id}/cancel`
- `GET /me/exchange-requests`
- `GET /me/listings`

Przegladarka wysyla cookie automatycznie; przed wywolaniem metod modyfikujacych dane klient musi pobrac `GET /csrf` i dolaczyc wartosc tokenu jako `X-CSRF-Token`. Publiczne sa odczyty listingow, `GET /enums`, `GET /health`, `GET /stats` oraz linkowe `GET /verify` i `GET /reset-password`.

## 6. Modele i statusy

### `User`

Przechowuje email, numer indeksu, hash hasla, status weryfikacji, hashe tokenow, daty wygasniecia, cooldown i date utworzenia. Surowe tokeny nigdy nie sa zapisywane w bazie.

### `Listing`

Ma wlasciciela, kierunek, semestr, przedmiot, typ zajec, grupe obecna, grupy docelowe, opis, status i date utworzenia. `group_want` jest lista w API, ale tekstem comma-separated w SQLite.

Statusy:

- `active` - widoczne i mozna sie zglosic.
- `pending` - ktos sie zglosil; znika z listy.
- `fulfilled` - wymiana potwierdzona i zakonczona sukcesem.
- `stale` - aktywne ogloszenie starsze niz 90 dni.
- `cancelled` - ogloszenie anulowane przez wlasciciela albo przez odrzucenie propozycji.

### `ExchangeRequest`

Laczy ogloszenie z osoba zglaszajaca. Ma status, czas utworzenia, czas wygasniecia i czas potwierdzenia.

Statusy:

- `pending`
- `confirmed`
- `expired`
- `cancelled`

### Dostawy maili

`EmailDelivery` opisuje logiczna dostawe, a `EmailDeliveryAttempt` zapisuje konkretna probe. Status `failed` nie usuwa rekordu biznesowego. Rejestracja zwykle zwraca neutralne `201`, a przy bledzie wysylki `503`; konto pozostaje niezweryfikowane. Proces wymiany nie jest cofany tylko dlatego, ze powiadomienie nie doszlo.

Logi techniczne sa wysylane na stdout. Przy uruchomieniu przez systemd beda dostepne przez `journalctl -u wymiana-zajec`; aplikacja nie zapisuje sekretow ani tokenow do logow.

## 7. Bezpieczenstwo

Zastosowane:

- hasla hashowane przez `scrypt` z losowa sola,
- tokeny resetu, weryfikacji, sesji i CSRF generowane przez `secrets.token_urlsafe`,
- tokeny resetu, weryfikacji i sesji sa przechowywane w bazie wylacznie jako hashe,
- cookie sesyjne `HttpOnly`, `SameSite=Lax`, siedmiodniowe oraz `Secure` na produkcji,
- ochrona CSRF przez double-submit cookie, naglowek `X-CSRF-Token` i walidacje `Origin` dla metod zmieniajacych stan,
- neutralna odpowiedz resetu hasla,
- jednorazowy reset hasla,
- uniewaznienie sesji po zmianie hasla,
- ograniczenia rate limitingu,
- walidacja wlasciciela i statusu ogloszenia,
- dane sekretne poza repozytorium.

Ograniczenia i ryzyka produkcyjne:

- limiter korzysta z pamieci procesu; przy wielu workerach potrzebny jest Redis lub limitowanie na proxy/WAF,
- SQLite nie jest docelowa baza dla wiekszego wdrozenia,
- brak migracji Alembic.

## 8. Testy

```powershell
python -m uv run pytest -q
```

## 9. Test manualny end-to-end

### Przygotowanie

Uruchom backend i frontend. Najwygodniej uzyj dwoch profili przegladarki albo okna zwyklego i incognito, aby utrzymac osobne sesje kont A i B.

```powershell
# terminal 1, backend lokalnie
python -m uv run uvicorn wymiana_zajec.main:app --reload

# terminal 2, frontend
cd frontend
npm run dev
```

Otworz `http://localhost:5173`. Swagger API jest pod `http://127.0.0.1:8000/docs`.

W lokalnej bazie developerskiej moze istniec konto testowe B utworzone poza kodem. Nie wpisuj hasla testowego do repozytorium ani dokumentacji produkcyjnej.

### A. Rejestracja i weryfikacja

1. Frontend pobiera token przez `GET /csrf`; metody modyfikujace dane wysylaja go w naglowku `X-CSRF-Token`.
2. W profilu A wybierz `Zaloz konto`.
3. Uzyj formatu emaila `12345678@pw.edu.pl`, szesciocyfrowego numeru indeksu i hasla o dlugosci co najmniej 8 znakow.
4. Sprawdz, ze konto zostalo utworzone i pojawil sie komunikat o weryfikacji emaila.
5. Przed weryfikacja sprobuj sie zalogowac. Oczekiwany rezultat: `403`, konto nie moze wejsc do aplikacji.
6. Otworz link `/verify?token=...` z maila. Oczekiwany rezultat: `200`.
7. Otworz ten sam link drugi raz. Oczekiwany rezultat: blad, bo token jest jednorazowy.
8. Sprawdz link wygasly po 7 dniach w testach API albo przez przygotowanie rekordu w bazie. Oczekiwany rezultat: `410`.

### B. Logowanie i sesja cookie

1. Zaloguj konto A poprawnym haslem. Oczekiwany rezultat: pojawia sie przycisk `Moje wymiany` i `Dodaj ogloszenie`.
2. Odswiez strone. Uzytkownik powinien nadal byc zalogowany dzieki cookie sesyjnemu.
3. Wyloguj sie. Oczekiwany rezultat: frontend wywoluje `POST /logout`, cookie jest wygaszone, a przyciski konta wracaja do `Zaloguj` i `Zaloz konto`.
4. Sprobuj zalogowac sie zlym haslem. Oczekiwany rezultat: `401`, bez utworzenia sesji.
5. Sprobuj dostepu do chronionego endpointu bez sesji. Oczekiwany rezultat: `401`.
6. Sprobuj wyslac operacje zmieniajaca dane z brakujacym lub blednym `X-CSRF-Token`. Oczekiwany rezultat: `403`.

### C. Reset hasla i ponowienie weryfikacji

1. W oknie logowania kliknij `Nie pamietam hasla` i wpisz email konta A.
2. Oczekiwany rezultat: neutralny komunikat niezaleznie od tego, czy konto istnieje; API zwraca `202`.
3. Otworz link resetu z maila i ustaw nowe haslo.
4. Zaloguj sie nowym haslem. Stare haslo powinno odrzucic logowanie.
5. Jesli konto jest niezweryfikowane, uzyj `Wyslij ponownie link weryfikacyjny`.
6. Ponowienie przed wygasnieciem poprzedniego poprawnie wyslanego linku powinno zostac zablokowane przez `429`; po `failed` powinno byc mozliwe od razu.
7. Uzyj tokenu resetu drugi raz albo po wygasnieciu. Oczekiwany rezultat: `400`.

### D. Tworzenie i wyszukiwanie ogloszenia

1. Konto A utworz ogloszenie, np. `Algebra`, semestr 3, grupa `1` -> grupy `2, 3`.
2. Sprawdz, ze ogloszenie jest widoczne publicznie i ma poprawne grupy.
3. Otworz filtry i sprawdz filtrowanie po kierunku, przedmiocie, semestrze, typie zajec, grupie posiadanej i grupie szukanej.
4. Dodaj drugie ogloszenie z odwrotnym kierunkiem, np. `2` -> `1`. Oczekiwany rezultat: `409` z `conflicting_listing_id`.
5. Sprobuj utworzyc ogloszenie z taka sama grupa w `group_have` i `group_want`. Oczekiwany rezultat: walidacja `422`.
6. Sprobuj utworzyc ogloszenie bez sesji. Oczekiwany rezultat: `401` przy prawidlowym tokenie CSRF.
7. W panelu `Moje wymiany` sprawdz, ze ogloszenie jest widoczne w `Moje ogloszenia`.

### E. Zgloszenie wymiany

1. W profilu B znajdz aktywne ogloszenie konta A.
2. Przed zalogowaniem kliknij zainteresowanie. Oczekiwany rezultat: komunikat o koniecznosci logowania.
3. Po zalogowaniu kontem B kliknij `Aplikuj`.4. Oczekiwany rezultat: ogloszenie przechodzi na `pending` i znika z publicznej listy.
5. W profilu B otworz `Moje wymiany`: wpis jest w `Wyslane`.
6. W profilu A otworz `Moje wymiany`: wpis jest w `Otrzymane`, z akcjami `Potwierdz` i `Odrzuc`.
7. Przed potwierdzeniem sprawdz, ze email drugiej osoby nie jest widoczny.
8. Sprobuj wyslac drugie zgloszenie do tego samego ogloszenia. Oczekiwany rezultat: `409` albo blokada wynikajaca ze statusu `pending`.
9. Sprobuj zglosic sie do wlasnego ogloszenia. Oczekiwany rezultat: `400` albo `403` zgodnie z kontraktem endpointu.

### F. Potwierdzenie wymiany

1. W profilu A kliknij `Potwierdz`.
2. Anuluj dialog. Oczekiwany rezultat: nic sie nie zmienia.
3. Ponownie kliknij `Potwierdz` i zaakceptuj dialog.
4. Oczekiwany rezultat: request ma status `confirmed`, listing ma status `fulfilled` i znika z publicznej listy.
5. W obu profilach wpis pojawia sie w `Zakonczone`.
6. Dopiero teraz oba profile widza email drugiej osoby.
7. Sprawdz skrzynki: obie osoby powinny dostac krotki email o dopasowaniu z opisem przedmiotu i kontaktem.
8. Sprobuj potwierdzic ten sam request drugi raz. Oczekiwany rezultat: `409`.

### G. Odrzucenie i anulowanie

1. Utworz nowe ogloszenie konta A i zglos sie na nie kontem B.
2. W profilu A kliknij `Odrzuc` i anuluj dialog. Oczekiwany rezultat: brak zmian.
3. Ponownie kliknij `Odrzuc` i zaakceptuj monit o anulowaniu.
4. Oczekiwany rezultat: request ma `cancelled`, listing ma `cancelled`, a listing nie wraca do `active`.
5. W profilu A anuluj osobne aktywne ogloszenie przez `Moje ogloszenia`.
6. Oczekiwany rezultat: listing ma `cancelled` i znika z publicznej listy.
7. Anuluj listing ze statusem `pending`. Powiazany oczekujacy request tez powinien miec `cancelled`.
8. Sprobuj anulowac cudze ogloszenie. Oczekiwany rezultat: `403`.
9. Sprobuj anulowac listing `fulfilled`, `stale` albo juz `cancelled`. Oczekiwany rezultat: `409`.

### H. Wygasanie i nieaktualne ogloszenia

1. W testach API ustaw `expires_at` requestu na czas przeszly.
2. Wykonaj odczyt listy lub wywolaj endpoint wymiany.
3. Oczekiwany rezultat: request ma `expired`, listing wraca do `active`, a wlasciciel dostaje cooldown 4 dni.
4. W czasie cooldownu sprobuj utworzyc nowe ogloszenie. Oczekiwany rezultat: blokada.
5. Ustaw `created_at` aktywnego ogloszenia starsze niz 90 dni i wywolaj odczyt listy.
6. Oczekiwany rezultat: listing przechodzi na `stale` i nie jest publicznie widoczny.

### I. Health, maile i dane

1. Otworz `/health`. Oczekiwany rezultat: `{"status":"ok"}`.
2. Sprawdz `GET /enums?lang=pl` i `GET /enums?lang=en`; etykiety powinny byc kompletne, w tym `cancelled`.
3. Przy mockowanej wysylce uruchom testy automatyczne; nie wymagaja one prawdziwego Brevo.
4. Przy realnej konfiguracji sprawdz, ze logi nie zawieraja hasel ani surowych tokenow.
5. Sprawdz, ze reset hasla uniewaznia poprzednia sesje cookie.

### J. Docker

1. Upewnij sie, ze Docker Engine dziala.
2. Uruchom `docker compose -f docker/compose.yaml up --build`.
3. Sprawdz `http://localhost:8000/health` i `http://localhost:8000/docs`.
4. Sprawdz `docker compose -f docker/compose.yaml ps`; backend powinien byc zdrowy.
5. Utworz konto i listing przez API, zatrzymaj kontener `docker compose -f docker/compose.yaml down`, a nastepnie uruchom go ponownie.
6. Sprawdz, ze dane przetrwaly, bo SQLite jest w wolumenie `wymiana_data`.
7. Nie uzywaj `docker compose down -v`, chyba ze celowo chcesz wyzerowac baze.

### Kryterium zaliczenia

Test jest zaliczony, gdy publiczna lista pokazuje tylko aktualne `active`, kontakty sa ukryte przed `confirmed`, potwierdzenie i anulowanie sa atomowe, wygasanie przywraca listing zgodnie z cooldownem, sesja dziala po odswiezeniu, reset hasla jest jednorazowy, a dane przezywaja restart Compose.

Testy uzywaja osobnej bazy SQLite in-memory i mockuja wysylke Brevo. Nie wysylaja prawdziwych maili. Testowane sa m.in. ciasteczka sesyjne, logout, ochrona CSRF, reset hasla, neutralnosc odpowiedzi, uniewaznienie sesji, rate limiting, wygasanie tokenow, logi dostaw i blokada zgloszen do `pending`.

## 9. Kolejnosc dalszych prac

1. HTTPS, reverse proxy, trusted hosts, CORS i konfiguracja produkcyjna.
2. Storage rate limitingu odporny na wiele instancji, dopiero przy skalowaniu.
3. Migracje schematu, gdy projekt zacznie przechowywac dane, ktorych nie mozna kasowac.
4. Frontend jako osobny proces za Nginxem.

## 10. Zasady pracy z repozytorium

- Nie czytaj ani nie wyswietlaj `.env`.
- Nie commituj sekretow, bazy lokalnej ani pliku `keys`.
- Dodawaj biblioteki przez `python -m uv add <pakiet>`.
- Po zmianach uruchamiaj `python -m uv run pytest -q`.
- Zachowuj testy dla kazdej zmiany kontraktu lub reguly biznesowej.
- Nie dodawaj migracji ani zmian produkcyjnych bez osobnej decyzji.