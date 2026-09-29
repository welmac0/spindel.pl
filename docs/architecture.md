# Architektura

## Cel produktu

Spindel sluzy studentom PW do publikowania ogloszen o zamianie grup zajeciowych. Inny zweryfikowany student moze wyslac zgloszenie; wymiana konczy sie dopiero po potwierdzeniu przez wlasciciela ogloszenia.

## Komponenty

- **Frontend:** React + TypeScript + Vite; w produkcji statyczny `dist` serwuje Nginx.
- **Backend:** FastAPI + SQLModel, uruchamiany przez Uvicorn.
- **Baza danych:** SQLite na trwalym wolumenie Dockera `docker_wymiana_data`.
- **Reverse proxy / TLS:** Nginx w kontenerze frontendu przekazuje `/api` do backendu; Certbot odnawia certyfikat TLS.
- **E-mail:** Brevo Transactional API.
- **Host:** pojedynczy VPS Hetzner, Docker Compose na Ubuntu.

## Glowny przeplyw wymiany

1. Uzytkownik rejestruje konto przez adres PW i weryfikuje go linkiem e-mail.
2. Zalogowany uzytkownik publikuje ogloszenie.
3. Inny uzytkownik wysyla zgloszenie. Ogloszenie przechodzi atomowo z `active` do `pending` i znika z publicznej listy.
4. Wlasciciel potwierdza albo odrzuca zgloszenie.
5. Potwierdzenie ustawia `fulfilled` i dopiero wtedy ujawnia obu stronom e-mail kontaktowy. Odrzucenie anuluje ogloszenie.
6. Niepotwierdzone zgloszenie wygasa po 48 godzinach; ogloszenie wraca do `active`, a wlasciciel otrzymuje cooldown 4 dni.

Szczegoly statusow i zasad dostepu: [Model danych i API](api.md).

## Struktura kodu

- `src/wymiana_zajec/main.py` — routing API, auth, logika ogloszen i wymian, rate limiting.
- `src/wymiana_zajec/models.py` — modele SQLModel, DTO, enumy i walidacja.
- `src/wymiana_zajec/database.py` — silnik SQLite i sesje bazy.
- `src/wymiana_zajec/email_service.py` — Brevo i tresci e-maili.
- `src/wymiana_zajec/translations.py` — etykiety enumow PL/EN.
- `frontend/src/main.tsx` — glowna aplikacja React.
- `docker/` — obrazy, konfiguracja Compose i Nginx.
- `tests/` — testy API i e-maili.

## Uruchomienie lokalne

Wymagany Python 3.13+ i `uv`:

```powershell
python -m uv sync
python -m uv run uvicorn wymiana_zajec.main:app --reload
```

Testy backendu:

```powershell
python -m uv run pytest -q
```

Frontend uruchom w drugim terminalu:

```powershell
cd frontend
npm ci
npm run dev
```

Frontend developerski jest pod `http://localhost:5173`; Vite proxy'uje `/api` do backendu na porcie 8000. Swagger: `http://127.0.0.1:8000/docs`.

Alternatywnie pelny lokalny Compose:

```powershell
docker compose -f docker/compose.yaml up --build
```

Compose developerski wystawia frontend na porcie 5175, backend na 8000 i zapisuje SQLite w zewnetrznym wolumenie `docker_wymiana_data`. Nie wykonuj `docker compose down -v`, jezeli chcesz zachowac baze.

## Ograniczenia architektury

- Jedna instancja VPS; brak wysokiej dostepnosci na poziomie hosta.
- Rate limiting `slowapi` jest in-memory; wspoldzielony storage bedzie potrzebny dopiero przy wielu workerach/instancjach.
- SQLite i `create_all()` bez migracji Alembic sa wystarczajace dla obecnego etapu, ale zmiany schematu wymagaja ostroznosci.
- Wysylka e-mail jest synchroniczna; brak kolejki asynchronicznej.

Szczegoly sesji i ryzyk: [Bezpieczenstwo](security.md). Operacje VPS: [Operacje i wdrazanie](operations.md).
