# Kontekst projektu dla LLM

Ten dokument jest instrukcja startowa dla agenta pracujacego nad repozytorium `wymiana-zajec`.

## Tozsamosc systemu

To backend FastAPI dla wymiany grup zajeciowych studentow PW. Stack: Python 3.13+, FastAPI, SQLModel, SQLite, Brevo Transactional Email API, slowapi, uv. Frontend nie istnieje.

## Zasady bezwzgledne

1. Nigdy nie czytaj, nie wyswietlaj i nie cytuj `.env`. Korzystaj tylko z nazw zmiennych konfiguracyjnych albo `.env.example`.
2. Nie dodawaj zaleznosci przez pip. Uzywaj `python -m uv add <pakiet>`; testy uruchamiaj przez `python -m uv run pytest -q`.
3. Nie usuwaj zmian uzytkownika i nie wykonuj destrukcyjnych operacji na bazie bez wyraznej zgody.
4. Po zmianie kodu uruchom najpierw testy dotykajace zmienionego przeplywu, potem caly `pytest`.
5. Nie cofaj unikalnosci emaila ani numeru indeksu. `409` przy duplikacie jest zamierzony.
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

Rejestracja wymaga emaila w formacie `8-cyfr@pw.edu.pl`, szesciocyfrowego numeru indeksu i hasla minimum 8 znakow. Email musi zostac zweryfikowany. Link aktywacyjny wazny jest 7 dni. Resend jest zablokowany przez 7 dni po udanej wysylce, ale mozliwy od razu po `failed`. Bearer jest wazny 7 dni.

Reset hasla:

- request ma odpowiedz neutralna `202`,
- token resetu jest przechowywany w bazie jako SHA-256 hash,
- token wazny 1 godzine i jednorazowy,
- zmiana hasla uniewaznia auth token.

### Ogloszenie i wymiana

Ogloszenia sa publiczne, ale tworzenie/edycja/usuwanie wymaga Bearera i wlasciciela. Tylko `active` jest widoczne. Zgloszenie wymaga zalogowania, nie moze byc do wlasnego ogloszenia i warunkowo przelacza `active -> pending`. Po 48 godzinach bez potwierdzenia zgloszenie wygasa, ogloszenie wraca do `active`, a wlasciciel dostaje cooldown 4 dni. Potwierdzenie zmienia zgloszenie na `confirmed` i ogloszenie na `closed`.

### Mail i awaria

Kazda logiczna wysylka ma `EmailDelivery`, a kazda proba `EmailDeliveryAttempt`. Nieudana wysylka jest zapisana jako `failed`. Rejestracja zwraca `503`, ale konto zostaje w bazie niezweryfikowane. Awaria powiadomienia wymiany nie cofa zapisanej wymiany.

## Endpointy

- `POST /register` - konto, limit `5/minute`.
- `GET /verify?token=...` - aktywacja.
- `POST /resend-verification` - resend, limit `3/hour`.
- `POST /login` - Bearer, limit `10/minute`.
- `POST /password-reset/request` - neutralny request, limit `3/hour`.
- `POST /password-reset/confirm` - jednorazowa zmiana, limit `10/hour`.
- `POST /listings` - chronione tworzenie.
- `GET /listings` i `GET /listings/{id}` - publiczne aktywne ogloszenia.
- `PATCH/DELETE /listings/{id}` - tylko wlasciciel.
- `POST /listings/{id}/requests` - tylko zalogowany, tylko active.
- `GET /listings/{id}/requests` - tylko wlasciciel.
- `POST /exchange-requests/{id}/confirm` - tylko wlasciciel.
- `GET /enums` - etykiety PL/EN.
- `GET /health` - status aplikacji i bazy.

## Bezpieczenstwo i ryzyka

Hashowanie hasel uzywa `scrypt`. Tokeny generuje `secrets`, a tokeny resetu i weryfikacji sa przechowywane jako hashe. Rate limiting uzywa slowapi z pamiecia procesu, wiec nie jest jeszcze wystarczajacy dla wielu workerow. Przed produkcja trzeba dodac Redis/WAF, HTTPS, trusted hosts i CORS. Logi aplikacji ida na stdout i nie moga zawierac sekretow ani tokenow; systemd przechwyci je przez journald.

`create_all()` nie wykonuje migracji istniejacych tabel. Zmiana modeli moze wymagac usuniecia lokalnego `database.db`; migracje sa celowo odlozone.

## Walidacja po zmianach

```powershell
python -m uv run pytest -q
```

Testy nie lacza sie z Brevo: wysylka jest mockowana. Przy recznym tescie uzywaj Swaggera na `http://127.0.0.1:8000/docs`.

## Decyzje wdrozeniowe

Na obecnym etapie aplikacja dziala jako jedna instancja. Nie dodawaj Redisa ani architektury klastrowej bez decyzji o skalowaniu. Docelowo frontend i backend beda osobnymi procesami za Nginxem, ale frontend jest odlozony do czasu domkniecia backendu.

## Preferowany sposob zmian

Przed edycja sformuluj lokalna hipoteze i najtanszy test, ktory ja obali. Zmieniaj najmniejszy wlascicielski modul. Dla zmian auth/mail zawsze dodaj test braku wycieku danych, jednorazowosci tokenu lub poprawnego statusu bledu. Nie czytaj sekretow, aby diagnozowac konfiguracje; sprawdzaj obecnosc nazw zmiennych albo wynik endpointu.