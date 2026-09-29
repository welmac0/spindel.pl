# Kontekst pracy dla agenta

Instrukcja startowa dla agenta kodujacego w repozytorium `wymiana-zajec`.

## Projekt

Spindel to aplikacja React/Vite + FastAPI do wymiany grup zajeciowych studentow PW. Stack: Python 3.13+, FastAPI, SQLModel, SQLite, Brevo, slowapi, uv, React, TypeScript i Vite.

## Zasady bezwzgledne

1. Nigdy nie czytaj, nie wyswietlaj ani nie cytuj `.env`, pliku `keys`, prywatnych kluczy SSH ani danych produkcyjnych. Odwoluj sie tylko do nazw zmiennych.
2. Nie dodawaj zaleznosci Python przez pip. Uzywaj `python -m uv add <pakiet>`; testuj przez `python -m uv run pytest -q`.
3. Nie usuwaj zmian uzytkownika ani nie wykonuj destrukcyjnych operacji na bazie bez wyraznej zgody.
4. Przed zmiana ustal lokalna hipoteze i najtanszy test, ktory ja obali. Zmieniaj najmniejszy modul bedacy wlascicielem zachowania.
5. Po zmianie uruchom najpierw testy dotykajace zmienionego przeplywu, potem pelne `pytest`; przy zmianie frontendu uruchom tez `npm run build` w `frontend`.
6. Zmiany API, zasad biznesowych, auth/mail lub konfiguracji wdrozeniowej wymagaja testu i aktualizacji odpowiedniej strony dokumentacji.
7. Projekt jest obecnie rozwijany samodzielnie. Nie wymagaj Pull Requesta: uzytkownik moze commitowac bezposrednio na `main`. Przed deployem sprawdz zielone CI dla wdrazanego commita.
8. Nie zmieniaj unikalnosci emaila/numeru indeksu ani neutralnych odpowiedzi rejestracji i resetu hasla; chroni to przed enumeracja kont.

## Mapa kodu

- `src/wymiana_zajec/main.py` — routing, uwierzytelnianie, rate limiting, logika wymian i zapis dostaw e-mail.
- `src/wymiana_zajec/models.py` — tabele, DTO, enumy, walidacja.
- `src/wymiana_zajec/email_service.py` — Brevo i tresci e-maili.
- `src/wymiana_zajec/database.py` — SQLite, `create_all()`, sesje bazy.
- `src/wymiana_zajec/translations.py` — etykiety enumow PL/EN.
- `frontend/src/main.tsx` — glowna aplikacja React.
- `tests/test_api.py`, `tests/test_email_service.py` — testy API i e-maili.

## Gdzie szukac dokumentacji

- [Indeks dokumentacji](WIKI.md)
- [Architektura i uruchomienie](architecture.md)
- [Model danych i API](api.md)
- [Bezpieczenstwo](security.md)
- [Testowanie](testing.md)
- [Operacje i wdrazanie](operations.md)

## Istotne, nieoczywiste decyzje

- Frontend nie przechowuje tokenu sesji w `localStorage`; sesja jest cookie `HttpOnly`.
- Wszystkie metody `POST`, `PUT`, `PATCH`, `DELETE` maja ochrone CSRF.
- SQLite dziala na pojedynczym VPS; nie dodawaj Redisa ani architektury wielu instancji bez decyzji o skalowaniu.
- `create_all()` nie migruje istniejacych tabel. Nie usuwaj bazy, by obejsc zmiane schematu.
- Dane kontaktowe ujawniaja sie dopiero po potwierdzeniu wymiany.
