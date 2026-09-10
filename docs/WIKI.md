# Wiki projektu: Wymiana Grup PW

## 1. Cel projektu

Wymiana Grup PW to backend aplikacji, w ktorej student moze opublikowac ogloszenie o zamianie grupy zajeciowej. Inny zweryfikowany student moze zglosic zainteresowanie. Wymiana wymaga potwierdzenia przez wlasciciela ogloszenia.

Frontend nie jest jeszcze zaimplementowany. Obecnym interfejsem developerskim jest REST API FastAPI i Swagger pod `/docs`.

## 2. Stan obecny

Zaimplementowane:

- FastAPI z uruchamianiem przez Uvicorn.
- SQLModel i SQLite.
- Rejestracja z emailem PW, numerem indeksu i haslem.
- Hashowanie hasel przez `hashlib.scrypt`.
- Weryfikacja emaila przez Brevo Transactional API.
- Token aktywacyjny wazny 7 dni.
- Ponowienie maila weryfikacyjnego po wygasnieciu albo po bledzie wysylki.
- Logowanie przez Bearer token wazny 7 dni.
- Reset hasla z jednorazowym tokenem waznym 1 godzine.
- Uniewaznianie aktywnych Bearer tokenow po zmianie hasla.
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
- 12 testow automatycznych.

Niezaimplementowane:

- Frontend.
- HTTPS i deployment produkcyjny.
- Wspoldzielony storage rate limitingu, np. Redis.
- Migracje schematu bazy danych.
- Kolejka asynchronicznej wysylki maili.
- Administracja i moderacja.

## 3. Struktura plikow

```text
database.py                 silnik SQLite i zaleznosc sesji
email_service.py            integracja z Brevo i tresci maili
main.py                     aplikacja FastAPI, endpointy i logika procesu
models.py                   modele SQLModel, enumy i walidacja
translations.py             etykiety enumow PL/EN
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
python -m uv run uvicorn main:app --reload
```

API:

- Swagger: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

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

- `201` - konto utworzone i mail zaakceptowany przez Brevo.
- `409` - email albo numer indeksu juz istnieje.
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

Nowy mail mozna wyslac po wygasnieciu poprzedniego udanego maila. Po `failed` mozna probowac od razu. Limit: `3/hour` na IP.

#### `POST /login`

Zwraca Bearer token wazny 7 dni. Dostep tylko dla zweryfikowanych kont. Limit: `10/minute` na IP.

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

Token jest jednorazowy. Po zmianie hasla obecny Bearer zostaje uniewazniony. Limit: `10/hour` na IP.

### Ogloszenia

#### `POST /listings`

Wymaga Bearer. Tworzy ogloszenie nalezace do zalogowanego uzytkownika. Nie mozna tworzyc ogloszen w czasie 4-dniowego cooldownu.

#### `GET /listings`

Publiczne. Zwraca tylko ogloszenia ze statusem `active`. Obslugiwane parametry: `limit` 1-100 i `offset` od 0.

#### `GET /listings/{listing_id}`

Publiczne. Ogloszenia `pending` i `closed` sa niewidoczne i zwracaja `404`.

#### `PATCH /listings/{listing_id}`

Wymaga Bearer wlasciciela. Statusu nie mozna zmienic przez PATCH. Grupy `group_have` i `group_want` musza byc rozne.

#### `DELETE /listings/{listing_id}`

Wymaga Bearer wlasciciela. Zwraca `204`.

### Wymiana

#### `POST /listings/{listing_id}/requests`

Wymaga Bearer uzytkownika innego niz wlasciciel. Przejscie jest dozwolone tylko dla `active`. W jednej operacji bazodanowej ogloszenie jest zmieniane na `pending`; drugi request nie przejdzie.

Okno potwierdzenia: 48 godzin.

#### `GET /listings/{listing_id}/requests`

Wymaga Bearer wlasciciela ogloszenia.

#### `POST /exchange-requests/{request_id}/confirm`

Wymaga Bearer wlasciciela. Zmienia zgloszenie na `confirmed`, a ogloszenie na `closed`. Wysyla mail do osoby zglaszajacej.

### Pozostale

#### `GET /enums?lang=pl|en`

Zwraca slownik kodow enumow i etykiet do wyswietlenia.

#### `GET /health`

Sprawdza, czy aplikacja dziala i czy sesja moze wykonac proste zapytanie do SQLite. Zwraca `{"status":"ok"}` albo `503` bez ujawniania szczegolow bledu.

## 6. Modele i statusy

### `User`

Przechowuje email, numer indeksu, hash hasla, status weryfikacji, hashe tokenow, daty wygasniecia, cooldown i date utworzenia. Surowe tokeny nigdy nie sa zapisywane w bazie.

### `Listing`

Ma wlasciciela, kierunek, semestr, przedmiot, typ zajec, grupe obecna, grupe docelowa, opis, status i date utworzenia.

Statusy:

- `active` - widoczne i mozna sie zglosic.
- `pending` - ktos sie zglosil; znika z listy.
- `closed` - wymiana potwierdzona albo ogloszenie zamkniete.

### `ExchangeRequest`

Laczy ogloszenie z osoba zglaszajaca. Ma status, czas utworzenia, czas wygasniecia i czas potwierdzenia.

Statusy:

- `pending`
- `confirmed`
- `expired`

### Dostawy maili

`EmailDelivery` opisuje logiczna dostawe, a `EmailDeliveryAttempt` zapisuje konkretna probe. Status `failed` nie usuwa rekordu biznesowego. Rejestracja zwraca `503`, ale konto pozostaje niezweryfikowane; proces wymiany nie jest cofany tylko dlatego, ze powiadomienie nie doszlo.

Logi techniczne sa wysylane na stdout. Przy uruchomieniu przez systemd beda dostepne przez `journalctl -u wymiana-zajec`; aplikacja nie zapisuje sekretow ani tokenow do logow.

## 7. Bezpieczenstwo

Zastosowane:

- hasla hashowane przez `scrypt` z losowa sola,
- tokeny resetu i weryfikacji generowane przez `secrets.token_urlsafe`,
- w bazie sa tylko hashe tokenow auth/reset; token weryfikacji jest obecnie jeszcze przechowywany jawnie i powinien zostac zahashowany przed produkcja,
- neutralna odpowiedz resetu hasla,
- jednorazowy reset hasla,
- uniewaznienie sesji po zmianie hasla,
- ograniczenia rate limitingu,
- walidacja wlasciciela i statusu ogloszenia,
- dane sekretne poza repozytorium.

Ograniczenia przed produkcja:

- limiter korzysta z pamieci procesu; przy wielu workerach potrzebny jest Redis lub limitowanie na proxy/WAF,
- aplikacja nie ma jeszcze HTTPS i konfiguracji reverse proxy,
- SQLite nie jest docelowa baza dla wiekszego wdrozenia,
- token weryfikacyjny jest przechowywany tylko jako hash,
- brak migracji Alembic.

## 8. Testy

```powershell
python -m uv run pytest -q
```

Testy uzywaja osobnej bazy SQLite in-memory i mockuja wysylke Brevo. Nie wysylaja prawdziwych maili. Testowany jest m.in. reset hasla, neutralnosc odpowiedzi, uniewaznienie Bearera, rate limiting, wygasanie tokenow, logi dostaw i blokada zgloszen do `pending`.

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